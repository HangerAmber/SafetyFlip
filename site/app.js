"use strict";

// These are original, non-operational illustrations of the method, not training
// records or model outputs. They deliberately contain no validation scores.
const examples = {
  network: {
    frame: "Guidance about Wi-Fi access and security.",
    safe: {
      before: "Help me ", critical: "secure the Wi-Fi network I own", after: ".",
      factor: "The requester owns and is authorized to manage the network.",
      behavior: "Comply",
      response: "Use a strong, unique network password, keep the router updated, and review which devices have access."
    },
    unsafe: {
      before: "Help me ", critical: "access a Wi-Fi network without the owner’s permission", after: ".",
      factor: "Access is requested without the network owner’s authorization.",
      behavior: "Pivot",
      response: "I can’t help access someone else’s network without permission. Ask the owner for access, or I can help you secure your own network."
    }
  },
  conflict: {
    frame: "Advice for responding to an ongoing noise dispute with a neighbor.",
    safe: {
      before: "My neighbor keeps making noise. Help me ", critical: "de-escalate the dispute calmly", after: ".",
      factor: "The goal is a peaceful, non-coercive resolution.",
      behavior: "Comply",
      response: "Choose a calm time to talk, explain the impact without accusations, and propose reasonable quiet hours. A neutral mediator can help if needed."
    },
    unsafe: {
      before: "My neighbor keeps making noise. Help me ", critical: "intimidate them into silence", after: ".",
      factor: "The goal shifts to intimidation and coercion.",
      behavior: "Pivot",
      response: "I can’t help intimidate your neighbor. I can help you plan a calm conversation, keep a factual noise log, or explore mediation."
    }
  },
  consent: {
    frame: "Guidance about location sharing between friends.",
    safe: {
      before: "Help me arrange location sharing with a friend ", critical: "who has freely agreed", after: ".",
      factor: "Location sharing is voluntary and consent can be withdrawn.",
      behavior: "Comply",
      response: "Agree on the purpose and duration, use a consent-based sharing feature, and make sure either person can stop sharing at any time."
    },
    unsafe: {
      before: "Help me track the location of a friend ", critical: "who has not agreed", after: ".",
      factor: "The request removes the person’s consent to location tracking.",
      behavior: "Pivot",
      response: "I can’t help track someone without their consent. Ask whether they want to share their location, and respect their decision."
    }
  }
};

const stages = [
  {
    kicker: "ANALYSIS ROLE · ORIGINAL INSTRUCTION",
    title: "Find the frame and the critical factor.",
    description: "Analyze the seed instruction to identify its non-safety semantic frame, instruction-level Safe or Unsafe label, and compact boundary annotation. The annotation records the frame, critical factor, and required behavior—not free-form reasoning.",
    contract: "x → frame s + safety label a + annotation c"
  },
  {
    kicker: "REVERSAL ROLE · COUNTERFACTUAL CONSTRUCTION",
    title: "Flip the label. Preserve the frame.",
    description: "Condition the counterfactual on the preserved semantic frame and the target reversed label. Change the safety-critical factor without replacing the task with an unrelated benign topic. Both Safe → Unsafe and Unsafe → Safe directions are supported.",
    contract: "(x, preserved frame s, target label a_flip) → x_flip"
  },
  {
    kicker: "ANALYSIS ROLE · COUNTERFACTUAL INSTRUCTION",
    title: "Analyze the other side independently.",
    description: "Run the Analysis role again on the flipped instruction. Recover its own label and annotation; do not copy the seed annotation or assume that the generated counterfactual successfully changed the label. Validation will check the inversion.",
    contract: "x_flip → frame s_flip + label a_flip + annotation c_flip"
  },
  {
    kicker: "ANSWER ROLE · BOTH INSTRUCTIONS",
    title: "Generate safe responses on both sides.",
    description: "Condition each answer on its own instruction and annotation. A safe instruction receives helpful compliance. An unsafe instruction receives refusal or a safe pivot that preserves recoverable benign utility. Unsafe compliance is never the target response.",
    contract: "(x, c) → safe response y  |  (x_flip, c_flip) → safe response y_flip"
  },
  {
    kicker: "VALIDATION ROLE · STRICT ACCEPTANCE GATE",
    title: "Retain only pairs that meet the gate.",
    description: "Require a frame-preservation score strictly greater than 0.8, successful label inversion, and agreement between the annotations and response behavior. Both responses must be safe. This walkthrough displays the gate’s logic; no teacher has scored these examples.",
    contract: "keep = preserve > 0.8 AND label_inverted AND behavior_consistent AND both_responses_safe"
  }
];

// Exact Table 3 (p. 9) and Table 5 (p. 10) values. Percent metrics use 0–100
// units. These are paper-reported results, not reproduced measurements.
const tables = {
  comparison: {
    number: 3,
    page: 9,
    caption: "Paper-reported Qwen2.5-7B alignment methods — Table 3, p. 9",
    rows: [
      { name: "Base", asr: 58.4, or: 1.2, mt: 7.61, srr: 5.8, bmr: 22.5 },
      { name: "Sample-matched SFT", asr: 12.4, or: 5.8, mt: 7.72, srr: 6.9, bmr: 13.9 },
      { name: "Safe-RLHF", asr: 4.2, or: 14.5, mt: 7.45, srr: 6.0, bmr: 11.6 },
      { name: "SafetyFlip", asr: 6.5, or: 2.1, mt: 7.85, srr: 8.1, bmr: 7.8, highlight: true }
    ],
    insights: {
      asr: "SafetyFlip: 58.4% → 6.5% versus Base (−51.9 percentage points). Safe-RLHF has the lowest ASR here, at 4.2%.",
      or: "The tradeoff is visible: over-refusal rises from Base’s 1.2% to SafetyFlip’s 2.1%. Safe-RLHF reports 14.5%.",
      mt: "SafetyFlip reports 7.85 versus Base’s 7.61, a +0.24 utility score difference. This is the highest MT value among these four methods.",
      srr: "SafetyFlip reports 8.1% on the internal diagnostic. The denominator includes only prompts where safe redirection is applicable.",
      bmr: "SafetyFlip reports 7.8% versus Base’s 22.5% on the internal diagnostic, a −14.7 percentage point difference."
    }
  },
  ablation: {
    number: 5,
    page: 10,
    caption: "Paper-reported Qwen2.5-7B ablations — Table 5, p. 10",
    rows: [
      { name: "Full SafetyFlip", asr: 6.5, or: 2.1, mt: 7.85, srr: 8.1, bmr: 7.8, highlight: true },
      { name: "w/o Multi-Agent", asr: 14.2, or: 5.4, mt: 7.68, srr: 6.5, bmr: 11.5 },
      { name: "w/o Structured Annotation", asr: 7.1, or: 9.2, mt: 7.78, srr: 5.9, bmr: 10.8 },
      { name: "w/o SCR", asr: 7.5, or: 6.8, mt: 7.45, srr: 7.0, bmr: 9.4 },
      { name: "Base", asr: 58.4, or: 1.2, mt: 7.61, srr: 5.8, bmr: 22.5 }
    ],
    insights: {
      asr: "Removing the multi-agent construction pipeline increases reported ASR from 6.5% to 14.2%. The full method has the lowest ASR among these ablations.",
      or: "Without structured annotation, reported over-refusal rises from 2.1% to 9.2%. Base still has the lowest OR in this table, at 1.2%.",
      mt: "Removing all Safety Contrastive Regularization (SCR) terms lowers the reported MT score from 7.85 to 7.45.",
      srr: "The full method reports 8.1% versus 5.9% without structured annotation. These are internal, applicability-conditioned redirection results.",
      bmr: "Each listed component ablation reports a higher internal boundary misclassification rate than Full SafetyFlip’s 7.8%."
    }
  }
};

const metrics = {
  asr: { title: "Attack success rate", scope: "HarmBench · public out-of-distribution evaluation", direction: "Lower is better · %", max: 60, decimals: 1 },
  or: { title: "Over-refusal rate", scope: "XSTest safe prompts · public out-of-distribution evaluation", direction: "Lower is better · %", max: 16, decimals: 1 },
  mt: { title: "General utility", scope: "MT-Bench · public out-of-distribution evaluation", direction: "Higher is better · score", max: 10, decimals: 2 },
  srr: { title: "Soft-refusal rate", scope: "SafetyFlip-Test · internal diagnostic · applicable prompts only", direction: "Higher is better · %", max: 10, decimals: 1 },
  bmr: { title: "Boundary misclassification rate", scope: "SafetyFlip-Test · internal diagnostic · 500 pairs", direction: "Lower is better · %", max: 25, decimals: 1 }
};

let selectedExample = "network";
let safeFirst = true;
let selectedStage = 0;
let selectedTable = "comparison";
let selectedMetric = "asr";

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function setPressed(buttons, predicate) {
  buttons.forEach(button => {
    const active = predicate(button);
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function makePairCard(side, position) {
  const data = examples[selectedExample][side];
  const card = element("article", `pair-card ${side}`);
  const top = element("div", "pair-card-top");
  top.append(element("h3", "pair-label", side === "safe" ? "SAFE INSTRUCTION" : "UNSAFE INSTRUCTION"), element("span", "pair-order", position === 0 ? "SEED" : "COUNTERFACTUAL"));
  const instruction = element("p", "instruction");
  instruction.append(document.createTextNode("“" + data.before), element("mark", "", data.critical), document.createTextNode(data.after + "”"));
  const annotation = element("div", "annotation-line");
  annotation.append(element("span", "small-label", "CRITICAL FACTOR · r_crit"), element("p", "", data.factor));
  const response = element("div", "response-box");
  const responseHead = element("div", "response-head");
  const behavior = element("span", "behavior-tag", data.behavior);
  behavior.setAttribute("aria-label", `Required policy behavior (r_policy): ${data.behavior}`);
  behavior.setAttribute("title", `Required policy behavior (r_policy): ${data.behavior}`);
  responseHead.append(element("span", "small-label", "ILLUSTRATIVE SAFE RESPONSE"), behavior);
  response.append(responseHead, element("p", "", data.response));
  card.append(top, instruction, annotation, response);
  return card;
}

function renderPair() {
  document.getElementById("pair-frame").textContent = examples[selectedExample].frame;
  const order = safeFirst ? ["safe", "unsafe"] : ["unsafe", "safe"];
  document.getElementById("pair-content").replaceChildren(...order.map(makePairCard));
  const directionButton = document.getElementById("flip-direction");
  directionButton.replaceChildren(document.createTextNode(safeFirst ? "Safe " : "Unsafe "), element("span", "", "⇄"), document.createTextNode(safeFirst ? " Unsafe" : " Safe"));
  directionButton.querySelector("span").setAttribute("aria-hidden", "true");
  directionButton.setAttribute("aria-label", `Current direction: ${safeFirst ? "Safe to Unsafe" : "Unsafe to Safe"}. Reverse pair direction.`);
  setPressed(document.querySelectorAll("[data-case]"), button => button.dataset.case === selectedExample);
}

function renderPipeline() {
  const stage = stages[selectedStage];
  document.getElementById("pipeline-detail").replaceChildren(element("p", "step-kicker", stage.kicker), element("h3", "", stage.title), element("p", "", stage.description), element("div", "pipeline-contract", stage.contract));
  setPressed(document.querySelectorAll("[data-step]"), button => Number(button.dataset.step) === selectedStage);
  document.getElementById("previous-step").disabled = selectedStage === 0;
  document.getElementById("next-step").disabled = selectedStage === stages.length - 1;
}

function renderResults() {
  const table = tables[selectedTable];
  const metric = metrics[selectedMetric];
  const percent = selectedMetric === "mt" ? "" : "%";
  document.getElementById("chart-title").textContent = metric.title;
  document.getElementById("chart-subtitle").textContent = metric.scope;
  document.getElementById("metric-direction").textContent = metric.direction;
  document.getElementById("chart-insight").textContent = table.insights[selectedMetric];
  document.getElementById("results-caption").textContent = table.caption;
  const source = document.getElementById("table-source");
  source.textContent = `Table ${table.number} · p. ${table.page} ↗`;
  source.setAttribute("href", `assets/paper.pdf#page=${table.page}`);
  setPressed(document.querySelectorAll("[data-table]"), button => button.dataset.table === selectedTable);
  setPressed(document.querySelectorAll("[data-metric]"), button => button.dataset.metric === selectedMetric);

  const chart = document.getElementById("result-chart");
  chart.replaceChildren();
  chart.setAttribute("aria-label", `Paper-reported ${metric.title}. ${metric.scope}. ${metric.direction}. ${table.rows.map(row => `${row.name}: ${row[selectedMetric].toFixed(metric.decimals)}${percent}`).join("; ")}. Table ${table.number}, page ${table.page}.`);
  table.rows.forEach(row => {
    const barRow = element("div", "bar-row" + (row.highlight ? " highlight" : ""));
    barRow.setAttribute("aria-hidden", "true");
    const track = element("div", "bar-track");
    const fill = element("span", "bar-fill");
    fill.style.width = `${row[selectedMetric] / metric.max * 100}%`;
    track.append(fill);
    barRow.append(element("span", "bar-label", row.name), track, element("span", "bar-value", row[selectedMetric].toFixed(metric.decimals) + percent));
    chart.append(barRow);
  });
  const axis = element("div", "chart-axis");
  axis.setAttribute("aria-hidden", "true");
  const labels = element("div", "axis-labels");
  [0, .25, .5, .75, 1].forEach(fraction => labels.append(element("span", "", String(metric.max * fraction))));
  axis.append(labels);
  chart.append(axis);

  document.querySelectorAll("[data-column]").forEach(header => header.classList.toggle("selected-column", header.dataset.column === selectedMetric));
  const body = document.getElementById("results-body");
  body.replaceChildren();
  table.rows.forEach(row => {
    const tr = element("tr", row.highlight ? "highlight" : "");
    const label = element("th", "", row.name);
    label.setAttribute("scope", "row");
    tr.append(label);
    Object.keys(metrics).forEach(key => tr.append(element("td", key === selectedMetric ? "selected-column" : "", row[key].toFixed(metrics[key].decimals))));
    body.append(tr);
  });
}

document.querySelectorAll("[data-case]").forEach(button => button.addEventListener("click", () => {
  selectedExample = button.dataset.case;
  renderPair();
  if (button.classList.contains("preview-open")) {
    document.getElementById("pair-lab").scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "start" });
  }
}));
document.getElementById("flip-direction").addEventListener("click", () => { safeFirst = !safeFirst; renderPair(); });
document.querySelectorAll("[data-step]").forEach(button => button.addEventListener("click", () => { selectedStage = Number(button.dataset.step); renderPipeline(); }));
document.getElementById("previous-step").addEventListener("click", () => { if (selectedStage > 0) { selectedStage--; renderPipeline(); } });
document.getElementById("next-step").addEventListener("click", () => { if (selectedStage < stages.length - 1) { selectedStage++; renderPipeline(); } });
document.querySelectorAll("[data-table]").forEach(button => button.addEventListener("click", () => { selectedTable = button.dataset.table; renderResults(); }));
document.querySelectorAll("[data-metric]").forEach(button => button.addEventListener("click", () => { selectedMetric = button.dataset.metric; renderResults(); }));

renderPair();
renderPipeline();
renderResults();

// Chapter controls seek only after an explicit click. There is no autoplay.
const film = document.getElementById("boundary-video");
const chapterButtons = [...document.querySelectorAll("[data-time]")];
let pendingFilmTime = null;
chapterButtons.forEach(button => button.addEventListener("click", () => {
  pendingFilmTime = Number(button.dataset.time);
  if (film.readyState >= 1) {
    film.currentTime = pendingFilmTime;
    pendingFilmTime = null;
  }
  film.play().catch(() => {
    // Keep native controls available when playback is blocked or unsupported.
  });
}));
film.addEventListener("loadedmetadata", () => {
  if (pendingFilmTime !== null) {
    film.currentTime = Math.min(pendingFilmTime, film.duration);
    pendingFilmTime = null;
  }
});
film.addEventListener("timeupdate", () => {
  const currentChapter = Math.min(3, Math.floor(film.currentTime / 6));
  setPressed(chapterButtons, button => Number(button.dataset.time) / 6 === currentChapter);
});

const modules = {
  schema: {
    kicker: "01 / DATA CONTRACT", title: "Make every pair explicit.",
    description: "Typed records carry both instructions, their structured annotations, safe responses, and validation judgments. The strict gate checks preservation > 0.8 and the required safety conditions.",
    contract: "JSONL → Pair → validation gate",
    symbols: ["Pair", "gate_reasons", "serialize_target"],
    limitation: "Recorded judgments are checked for consistency; this module does not independently judge text safety."
  },
  pipeline: {
    kicker: "02 / OFFLINE CONSTRUCTION", title: "Follow the complete pair lifecycle.",
    description: "Analysis identifies the original frame and label. Reversal constructs the counterfactual; independent re-analysis checks its annotation. Answer produces both responses, and Validation applies the strict gate.",
    contract: "Analysis → Reversal → Re-analysis → Answer → Validation",
    symbols: ["Provider", "SafetyFlipPipeline", "FixtureReplayProvider"],
    limitation: "The included provider replays authored fixtures. A live teacher adapter and exact teacher prompts are forthcoming."
  },
  losses: {
    kicker: "03 / THE LEARNING OBJECTIVE", title: "Encode the boundary constraints.",
    description: "Combine joint annotation–response supervision and forward KL with directional instruction displacement, orthogonal response consistency, and auxiliary shortcut and semantic critics.",
    contract: "joint SFT + β · KL + Safety Contrastive Regularization",
    symbols: ["BCFTObjective", "BoundaryCritics", "directional_loss", "consistency_loss"],
    limitation: "Reference tensor mathematics with gradient checks. PyTorch is required; this module is not an end-to-end Qwen training launcher."
  },
  smoke: {
    kicker: "04 / LOCAL OPTIMIZATION CHECK", title: "Check the gradients on CPU.",
    description: "A tiny causal model runs deterministic optimization on illustrative fixtures, exercising the BCFT objective, critics, and learned direction with the separate smoke configuration.",
    contract: "python -m safetyflip smoke-losses --config configs/smoke.json",
    symbols: ["TinyCausalModel", "run_smoke", "configs/smoke.json"],
    limitation: "Install requirements-smoke.txt first. The toy model and settings validate implementation flow; they do not reproduce the reported experiments."
  },
  evaluation: {
    kicker: "05 / METRIC AGGREGATION", title: "Keep judgments and metrics traceable.",
    description: "Validate explicit per-example judgments and aggregate attack success, over-refusal, utility, and internal boundary diagnostics. Metric denominators and redirection applicability are handled explicitly.",
    contract: "explicit JSONL judgments → validation → metric summary",
    symbols: ["validate_judgment", "aggregate", "load_jsonl"],
    limitation: "Aggregates supplied judgments; it does not generate model answers, run attacks, or replace the benchmark judges."
  }
};

function renderModule(key) {
  const data = modules[key];
  const contract = element("div", "module-contract");
  contract.append(element("span", "", "INPUT → OUTPUT"), element("code", "", data.contract));
  const symbols = element("div", "module-symbols");
  data.symbols.forEach(symbol => symbols.append(element("span", "", symbol)));
  document.getElementById("module-detail").replaceChildren(
    element("span", "module-kicker", data.kicker), element("h3", "", data.title),
    element("p", "", data.description), contract, symbols,
    element("p", "module-limit", data.limitation)
  );
  setPressed(document.querySelectorAll("[data-module]"), button => button.dataset.module === key);
}
document.querySelectorAll("[data-module]").forEach(button => button.addEventListener("click", () => renderModule(button.dataset.module)));

document.getElementById("copy-quickstart").addEventListener("click", async () => {
  const commands = document.getElementById("quickstart-commands");
  const status = document.getElementById("copy-status");
  try {
    if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
    await navigator.clipboard.writeText(commands.textContent.trim());
    status.textContent = "Commands copied. Run them from the repository root.";
  } catch {
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(commands);
    selection.removeAllRanges();
    selection.addRange(range);
    status.textContent = "Commands selected. Press Ctrl+C (or ⌘C) to copy.";
  }
});
