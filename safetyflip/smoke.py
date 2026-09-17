"""Tiny CPU optimizer exercise, not Qwen fine-tuning or a benchmark reproduction.

Uses a byte-token GRU, masked mean pooling, supplied toy labels and two authored
pairs. Every objective term, the learned direction, both critics and optimizers
participate in backward/step. No released weights or downloaded resources are used.
The architecture, serialization, pooling and hyperparameters are explicit choices.
"""

import copy
import json
from pathlib import Path

import torch
from torch import Tensor, nn

from .losses import BCFTObjective
from .schema import load_pairs, serialize_target


PAD, BOS, EOS, VOCAB_SIZE = 0, 1, 2, 259


def encode(text: str) -> list[int]:
    return [byte + 3 for byte in text.encode("utf-8")]


def padded(rows: list[list[int]]) -> tuple[Tensor, Tensor]:
    result = torch.full((len(rows), max(map(len, rows))), PAD, dtype=torch.long)
    for index, row in enumerate(rows):
        result[index, :len(row)] = torch.tensor(row, dtype=torch.long)
    return result, result.ne(PAD)


class TinyCausalModel(nn.Module):
    def __init__(self, hidden_size: int):
        super().__init__()
        self.embedding = nn.Embedding(VOCAB_SIZE, hidden_size, padding_idx=PAD)
        self.recurrent = nn.GRU(hidden_size, hidden_size, batch_first=True)
        self.lm_head = nn.Linear(hidden_size, VOCAB_SIZE)

    def forward(self, tokens: Tensor) -> tuple[Tensor, Tensor]:
        hidden, _ = self.recurrent(self.embedding(tokens))
        return self.lm_head(hidden), hidden

    def represent(self, tokens: Tensor, mask: Tensor) -> Tensor:
        _, hidden = self(tokens)
        return (hidden * mask[..., None]).sum(dim=1) / mask.sum(dim=1, keepdim=True)


def run_smoke(config_path: str | Path) -> dict:
    config_path = Path(config_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("status") != "toy CPU optimizer smoke; implementation choices, not paper hyperparameters":
        raise ValueError("smoke-losses requires the explicitly labeled toy configuration")
    if config.get("pooling") != "masked_mean":
        raise ValueError("this toy model implements only explicitly configured masked_mean pooling")
    if type(config["steps"]) is not int or config["steps"] < 1:
        raise ValueError("steps must be a positive integer")
    pairs = load_pairs(config_path.resolve().parent.parent / config["data"])
    if any(pair.provenance != "illustrative_fixture" for pair in pairs):
        raise ValueError("the toy smoke accepts only illustrative fixtures")
    sides = [pair.original for pair in pairs] + [pair.flipped for pair in pairs]
    torch.manual_seed(config["seed"])
    model = TinyCausalModel(config["hidden_size"])
    reference = copy.deepcopy(model).eval()
    reference.requires_grad_(False)
    shortcut = torch.tensor(config["shortcut_labels_original_then_flipped"], dtype=torch.long)
    semantic = torch.tensor(config["semantic_labels_original_then_flipped"], dtype=torch.long)
    if shortcut.shape != (len(sides),) or semantic.shape != (len(sides),):
        raise ValueError("critic label count must equal number of sides")
    if not torch.equal(semantic[:len(pairs)], semantic[len(pairs):]):
        raise ValueError("semantic labels must match within each pair")
    signs = torch.tensor([1.0 if pair.original.analysis.label == "Safe" else -1.0 for pair in pairs])
    safety_labels = torch.cat((signs, -signs)).lt(0).long()
    for labels in (shortcut, semantic):
        if bool(labels.lt(0).any()) or torch.equal(labels, safety_labels) or torch.equal(labels, 1 - safety_labels):
            raise ValueError("critic labels must be nonnegative domain/frame labels, not safety labels")
    objective = BCFTObjective(config["hidden_size"], int(shortcut.max()) + 1, int(semantic.max()) + 1,
                              **config["objective"])
    encoder_parameters = list(model.parameters()) + [objective.safety_direction]
    encoder_optimizer = torch.optim.AdamW(encoder_parameters, lr=config["learning_rate"],
                                          weight_decay=config["weight_decay"])
    critic_optimizer = torch.optim.AdamW(objective.critics.parameters(), lr=config["critic_learning_rate"],
                                         weight_decay=config["weight_decay"])
    token_rows, targets = [], []
    for side in sides:
        prompt = [BOS] + encode("Instruction: " + side.instruction + "\nTarget: ")
        target = encode(serialize_target(side)) + [EOS]
        token_rows.append(prompt + target)
        targets.append([-100] * len(prompt) + target)
    tokens, _ = padded(token_rows)
    labels = torch.full_like(tokens, -100)
    for index, row in enumerate(targets):
        labels[index, :len(row)] = torch.tensor(row)
    target_mask = labels.ne(-100)
    instruction_tokens, instruction_mask = padded([[BOS] + encode(side.instruction) + [EOS] for side in sides])
    response_tokens, response_mask = padded([[BOS] + encode(side.response.text) + [EOS] for side in sides])
    groups = {"model": list(model.parameters()), "safety_direction": [objective.safety_direction],
              "shortcut_critic": list(objective.critics.shortcut.parameters()),
              "semantic_critic": list(objective.critics.semantic.parameters())}
    before = {name: [parameter.detach().clone() for parameter in params] for name, params in groups.items()}
    records = []
    for step in range(config["steps"]):
        encoder_optimizer.zero_grad(set_to_none=True)
        critic_optimizer.zero_grad(set_to_none=True)
        policy_logits, _ = model(tokens)
        with torch.no_grad():
            reference_logits, _ = reference(tokens)
        h_x = model.represent(instruction_tokens, instruction_mask)
        h_y = model.represent(response_tokens, response_mask)
        count = len(pairs)
        terms = objective(policy_logits=policy_logits, reference_logits=reference_logits,
                          labels=labels, target_mask=target_mask,
                          instruction_original=h_x[:count], instruction_flipped=h_x[count:],
                          response_original=h_y[:count], response_flipped=h_y[count:], original_signs=signs,
                          shortcut_labels=shortcut, semantic_labels=semantic)
        if any(not bool(torch.isfinite(value)) for value in terms.values()):
            raise RuntimeError("non-finite objective term")
        terms["optimization_loss"].backward()
        for name, params in groups.items():
            if any(parameter.grad is None or not bool(torch.isfinite(parameter.grad).all()) for parameter in params):
                raise RuntimeError(f"missing or non-finite gradient in {name}")
        if any(parameter.grad is not None for parameter in reference.parameters()):
            raise RuntimeError("reference model must remain frozen")
        encoder_optimizer.step()
        critic_optimizer.step()
        records.append({"step": step + 1, **{key: round(value.detach().item(), 8) for key, value in terms.items()}})
    changed = {name: any(not torch.equal(old, current.detach()) for old, current in zip(before[name], params))
               for name, params in groups.items()}
    if not all(changed.values()):
        raise RuntimeError("optimizer smoke failed to update every parameter group")
    return {"status": "passed", "kind": "toy CPU optimizer smoke; not paper reproduction or benchmark",
            "torch_version": torch.__version__, "seed": config["seed"], "steps": config["steps"],
            "pairs": len(pairs), "supervised_target_tokens": int(target_mask.sum()),
            "parameter_groups_updated": changed, "reference_frozen": True,
            "label_provenance": config["label_note"],
            "scalar_note": "optimization_loss includes positive critic CEs with input-only gradient reversal. encoder_objective is the detached Eq.8/Eq.14 surrogate value. Neither is a benchmark metric or exact mutual information.",
            "records": records}
