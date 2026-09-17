"""Reference BCFT mathematics (paper Eqs. 4--8 and Appendix C Eqs. 13--14).

All reductions are token means or batch means, documented implementation choices.
Pooling, beta, lambda_info, target serialization and critic architecture were not
fully reported; callers must choose them explicitly. No value here is exact MI.

The adversarial update has TWO gradient objectives: critics minimize both CEs,
while the encoder receives -lambda_3*CE_shortcut + lambda_3*lambda_info*CE_sem.
Input-only gradient scaling implements this in one backward pass without scaling
critic parameter gradients. Its forward scalar is not the encoder objective.
"""

from dataclasses import dataclass
import math

import torch
from torch import Tensor, nn
from torch.nn import functional as F


def _coefficient(value: float, name: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be an explicit finite nonnegative number")
    return float(value)


def masked_mean(values: Tensor, mask: Tensor) -> Tensor:
    if mask.dtype != torch.bool or mask.shape != values.shape:
        raise ValueError("mask must be boolean and match values")
    if not bool(mask.any()):
        raise ValueError("loss mask selects no tokens")
    return values.masked_select(mask).mean()


def forward_kl(policy_logits: Tensor, reference_logits: Tensor, mask: Tensor) -> Tensor:
    """Token-mean KL(p_policy || p_frozen_base); reference receives no gradient."""
    if policy_logits.shape != reference_logits.shape or policy_logits.ndim != 3:
        raise ValueError("logits must have matching [batch, time, vocabulary] shapes")
    policy_log = F.log_softmax(policy_logits.float(), dim=-1)
    reference_log = F.log_softmax(reference_logits.detach().float(), dim=-1)
    divergence = (policy_log.exp() * (policy_log - reference_log)).sum(dim=-1)
    return masked_mean(divergence, mask)


def joint_kl_sft(policy_logits: Tensor, reference_logits: Tensor, labels: Tensor,
                 target_mask: Tensor, *, beta: float) -> dict[str, Tensor]:
    """Causal joint c+y CE + forward KL, excluding prompt/padding tokens.

    logits[:,t] predicts labels[:,t+1]. Labels at all prompt/padding positions
    must be -100; target_mask marks ALL serialized annotation+response tokens.
    This implementation scopes KL to exactly those same target positions.
    The caller is responsible for marking both c and y, not only y.
    """
    beta = _coefficient(beta, "beta")
    if policy_logits.shape != reference_logits.shape or policy_logits.ndim != 3:
        raise ValueError("policy/reference logits must have matching [B,T,V] shapes")
    if labels.shape != policy_logits.shape[:2] or labels.dtype != torch.long:
        raise ValueError("labels must be long [B,T]")
    if target_mask.dtype != torch.bool or target_mask.shape != labels.shape:
        raise ValueError("target_mask must be boolean [B,T]")
    if not torch.equal(target_mask, labels.ne(-100)):
        raise ValueError("labels must mask every prompt/padding position with -100")
    if bool(target_mask[:, 0].any()):
        raise ValueError("first position cannot be a supervised causal target")
    shifted_logits, shifted_labels = policy_logits[:, :-1], labels[:, 1:]
    mask = target_mask[:, 1:]
    ce_tokens = F.cross_entropy(shifted_logits.float().transpose(1, 2), shifted_labels,
                               ignore_index=-100, reduction="none")
    ce = masked_mean(ce_tokens, mask)
    kl = forward_kl(shifted_logits, reference_logits[:, :-1], mask)
    return {"sft": ce, "kl": kl, "kl_sft": ce + beta * kl}


def unit_direction(direction: Tensor) -> Tensor:
    if direction.ndim != 1 or not bool(torch.isfinite(direction).all()):
        raise ValueError("safety direction must be a finite vector")
    if bool(direction.norm() <= 1e-8):
        raise ValueError("safety direction must be nonzero")
    return F.normalize(direction, dim=0)


def signed_displacement(original: Tensor, flipped: Tensor, signs: Tensor) -> Tensor:
    """g(Safe)=+1, g(Unsafe)=-1; reversing pair orientation leaves this unchanged."""
    if original.shape != flipped.shape or original.ndim != 2 or signs.shape != original.shape[:1]:
        raise ValueError("representations must be matching [B,D] and signs [B]")
    if not bool(((signs == 1) | (signs == -1)).all()):
        raise ValueError("signs must be +1 for Safe or -1 for Unsafe")
    return signs[:, None] * (F.normalize(original, dim=-1) - F.normalize(flipped, dim=-1))


def directional_loss(original: Tensor, flipped: Tensor, signs: Tensor, direction: Tensor) -> Tensor:
    displacement = signed_displacement(original, flipped, signs)
    axis = unit_direction(direction)
    if axis.shape[0] != displacement.shape[-1]:
        raise ValueError("direction dimension mismatch")
    return (1 - F.cosine_similarity(displacement, axis[None, :], dim=-1)).mean()


def orthogonal_projection(representations: Tensor, direction: Tensor) -> Tensor:
    axis = unit_direction(direction)
    if representations.shape[-1] != axis.shape[0]:
        raise ValueError("direction dimension mismatch")
    return representations - (representations * axis).sum(dim=-1, keepdim=True) * axis


def consistency_loss(original_response: Tensor, flipped_response: Tensor, direction: Tensor) -> Tensor:
    """Eq.6: sum squared orthogonal difference over dimensions, then mean over pairs.

    Inputs are caller-selected response representations. No normalization occurs
    here: adding a safety-axis component must leave the projection unchanged.
    """
    if original_response.ndim != 2 or original_response.shape != flipped_response.shape:
        raise ValueError("response representations must have matching [B,D] shapes")
    delta = orthogonal_projection(original_response - flipped_response, direction)
    return delta.square().sum(dim=-1).mean()


class _ScaleInputGradient(torch.autograd.Function):
    @staticmethod
    def forward(ctx, inputs: Tensor, scale: float) -> Tensor:
        ctx.scale = scale
        return inputs.view_as(inputs)

    @staticmethod
    def backward(ctx, output_gradient: Tensor):
        return output_gradient * ctx.scale, None


def scale_input_gradient(inputs: Tensor, scale: float) -> Tensor:
    """Identity forward; gradient reversal when scale<0, parameter gradients unchanged."""
    if not math.isfinite(scale):
        raise ValueError("gradient scale must be finite")
    return _ScaleInputGradient.apply(inputs, float(scale))


@dataclass
class CriticTerms:
    optimization: Tensor
    encoder_surrogate: Tensor
    shortcut_ce: Tensor
    semantic_ce: Tensor


class BoundaryCritics(nn.Module):
    """Linear critics are a smoke/reference choice, not the unreleased architecture.

    shortcut labels encode trigger/category shortcuts; semantic labels encode
    the preserved non-safety frame. Neither label is the safety attribute. Their
    original ontology is forthcoming. Use stable supplied labels, never hashes.
    """

    def __init__(self, hidden_size: int, shortcut_classes: int, semantic_classes: int):
        super().__init__()
        if min(hidden_size, shortcut_classes, semantic_classes) < 2:
            raise ValueError("hidden dimension and each critic class count must be >=2")
        self.shortcut = nn.Linear(hidden_size, shortcut_classes)
        self.semantic = nn.Linear(hidden_size, semantic_classes)

    def forward(self, representations: Tensor, shortcut_labels: Tensor, semantic_labels: Tensor,
                *, lambda_info: float, encoder_weight: float) -> CriticTerms:
        lambda_info = _coefficient(lambda_info, "lambda_info")
        encoder_weight = _coefficient(encoder_weight, "encoder_weight")
        shortcut = F.cross_entropy(self.shortcut(scale_input_gradient(representations, -encoder_weight)),
                                   shortcut_labels)
        semantic = F.cross_entropy(self.semantic(scale_input_gradient(representations, encoder_weight * lambda_info)),
                                   semantic_labels)
        # Critic gradients match Eq.13, even when lambda_info or lambda_3 differs from 1.
        optimization = shortcut + semantic
        # Logging only: its value matches Eq.14 (before lambda_3), but it is not backpropagated.
        encoder_surrogate = -shortcut.detach() + lambda_info * semantic.detach()
        return CriticTerms(optimization, encoder_surrogate, shortcut, semantic)


class BCFTObjective(nn.Module):
    """Joint graph with learned direction and separately weighted critic/encoder gradients.

    Backpropagate `optimization_loss` ONCE; step model/direction and critic
    optimizers. Do not externally multiply the critic term by lambda_3: its input
    gradients already contain that coefficient. `encoder_objective` is detached
    for reporting and should never be used for backward().
    """

    def __init__(self, hidden_size: int, shortcut_classes: int, semantic_classes: int, *,
                 beta: float, lambda_1: float, lambda_2: float, lambda_3: float, lambda_info: float):
        super().__init__()
        self.beta = _coefficient(beta, "beta")
        self.lambda_1 = _coefficient(lambda_1, "lambda_1")
        self.lambda_2 = _coefficient(lambda_2, "lambda_2")
        self.lambda_3 = _coefficient(lambda_3, "lambda_3")
        self.lambda_info = _coefficient(lambda_info, "lambda_info")
        self.safety_direction = nn.Parameter(F.normalize(torch.randn(hidden_size), dim=0))
        self.critics = BoundaryCritics(hidden_size, shortcut_classes, semantic_classes)

    def forward(self, *, policy_logits: Tensor, reference_logits: Tensor, labels: Tensor,
                target_mask: Tensor, instruction_original: Tensor, instruction_flipped: Tensor,
                response_original: Tensor, response_flipped: Tensor, original_signs: Tensor,
                shortcut_labels: Tensor, semantic_labels: Tensor) -> dict[str, Tensor]:
        terms = joint_kl_sft(policy_logits, reference_logits, labels, target_mask, beta=self.beta)
        direction = directional_loss(instruction_original, instruction_flipped, original_signs, self.safety_direction)
        # h(.) denotes normalized pooled states; normalize before the orthogonal
        # projection. The primitive consistency_loss accepts already chosen h(.)
        # values so its safety-axis invariance can be inspected independently.
        consistency = consistency_loss(F.normalize(response_original, dim=-1),
                                       F.normalize(response_flipped, dim=-1), self.safety_direction)
        # Ordering is all original sides followed by all flipped sides, shared by supplied labels.
        z = F.normalize(torch.cat((instruction_original, instruction_flipped)), dim=-1)
        critics = self.critics(z, shortcut_labels, semantic_labels,
                               lambda_info=self.lambda_info, encoder_weight=self.lambda_3)
        primary = terms["kl_sft"] + self.lambda_1 * direction + self.lambda_2 * consistency
        return {**terms, "direction": direction, "consistency": consistency,
                "shortcut_ce": critics.shortcut_ce, "semantic_ce": critics.semantic_ce,
                "mi_encoder_surrogate": critics.encoder_surrogate,
                "encoder_objective": primary.detach() + self.lambda_3 * critics.encoder_surrogate,
                "optimization_loss": primary + critics.optimization}
