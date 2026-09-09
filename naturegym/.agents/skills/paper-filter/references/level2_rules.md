# Level 2: Evaluation System Validity Filtering

Ensure the task has objective, quantifiable evaluation criteria: Algorithm A must win on a recognized quality metric, and that metric must be deterministic and automated.

---

## Rule 2.1: Performance Absoluteness

### Pass Conditions

The paper passes if **both** of the following hold:

1. **Quality metric as core winning criterion**: The primary metric justifying Algorithm A's superiority or SOTA status is a quality metric from the whitelist below. Merely reporting a whitelist metric is insufficient — it must be the metric where A demonstrates its primary advantage.

2. **Competitive quality performance**: Algorithm A achieves quality performance at or above the best baseline reported in the paper, such that the reported SOTA S serves as a meaningful, challenging benchmark.

**Quality metric whitelist** (allowed as core winning criteria):
- Classification/Detection: Accuracy, Precision, Recall, F1-Score, AUC-ROC, mAP
- Regression: RMSE, MAE, MSE, R²
- Correlation: Pearson Correlation, Spearman Correlation
- Generation/Translation: BLEU, ROUGE, METEOR, CIDEr
- Language Models: Perplexity (PPL)
- Reinforcement Learning: Success Rate, Cumulative Reward
- Structure Prediction: GDT-TS, TM-score, LDDT, RMSD
- Image Quality: PSNR, SSIM, FID, IS
- Other Quality Metrics: IoU, Dice Score, Edit Distance, etc.

### Reject Conditions

**1. Efficiency/Resource Consumption**

The paper's core winning criterion is an efficiency/resource metric: Inference Latency, Training Time, FLOPS, Parameter Count, Peak Memory Usage, Energy, Throughput, GPU Utilization, etc.

**2. Model Analysis**

The paper's core winning criterion is based on interpretability/analysis effectiveness or qualitative argumentation rather than task-performance metrics. Includes: Interpretability/Explainability analysis, Visualization analysis, Qualitative case studies.

**3. Non-competitive Quality**

Algorithm A's quality performance is below the best baseline on the core quality metric. The paper's advantage lies solely in efficiency, resource savings, or analysis — SOTA S does not represent the quality frontier.

### Clarifications

**ML replacing traditional methods for acceleration**: When ML replaces traditional time-consuming methods (e.g., physics simulation), "acceleration" is the motivation or background explanation for choosing ML, not the core contribution. The core contribution remains quality performance. Such papers pass if quality metrics are the primary basis for comparison, even if A's quality is slightly lower than the traditional method — the comparison is ML-vs-traditional, not ML-vs-ML. However, if the paper also compares against other ML baselines, A must still achieve competitive quality against them (the Dual Objective rule below applies to the ML-vs-ML comparison).

**Dual objective (quality + efficiency)**: When a paper compares both quality and efficiency against other ML baselines, determine the core winning factor. Pass if A's quality matches or exceeds all baselines (quality is the primary factor, efficiency is auxiliary). Reject if A's quality is below any baseline but efficiency is better (the winning criterion is purely efficiency).

---

## Rule 2.2: Metric Determinism

### Pass Conditions

Metric M must satisfy all three:
1. **Deterministic function**: `Score = M(Y_out, Y_ref)` — the metric is a function of only the algorithm's output and the reference
2. **Fully automated**: Given Y_out and Y_ref, a unique numerical value can be computed without human intervention. For Oracle-type tasks, M may involve running a simulator or scoring function; this is acceptable as long as the scorer is reproducible and locally executable.
3. **Reproducible**: Same input must always produce same output

### Reject Conditions

**1. Human Subjective Evaluation as Core Criterion**

Human evaluation / user study as the main evaluation method. Human evaluation as auxiliary qualitative demonstration is allowed, but cannot be the core criterion.

**2. Visual Inspection**

Relies on manual visual inspection to judge result quality.

**3. Black-box Evaluation Tools**

All tools and resources needed to compute the metric must be obtainable by an independent evaluator. Common violations:
- Metric computation depends on proprietary software not disclosed by the paper
- Metric computation depends on domain-specific expert knowledge bases that are not publicly accessible

**4. Algorithm A-Dependent Evaluation**

The evaluation mechanism requires a component of Algorithm A itself (e.g., A's trained discriminator, A's encoder, A's learned reward model) to compute scores. This leaks method information and prevents fair benchmarking — a Solver using a different approach cannot be evaluated.

**5. Non-reproducible External Service**

The evaluation depends on an external service or API (e.g., cloud-hosted model endpoint, online scoring platform) with no locally executable alternative. Reproducibility cannot be guaranteed.

---

## Task Info Extraction

Fields extracted at this Level: `task_info.metrics`, `task_info.sota`, `task_info.baseline`

### Metric extraction rules

Only extract metrics that satisfy **all** of the following:
1. **Used to evaluate Algorithm A** in the paper's main result tables/figures — not metrics that only appear in ablation studies, sensitivity analysis, or auxiliary demonstrations
2. **Quality metrics** from the whitelist above — do not extract efficiency/resource metrics or analysis-only metrics
3. **Have explicit score reporting** — each metric must have a traceable score_source (e.g., "Table 2", "Figure 3") where Algorithm A's scores are reported
4. **Per-metric determinism** — each metric must individually satisfy Rule 2.2. Exclude metrics whose computation involves human evaluation, visual inspection, proprietary tools, Algorithm A's own components, or non-reproducible external services

### SOTA and baseline extraction rules

- `sota`: The method name of Algorithm A (including all named variants). Must be consistent with `task_info.algorithm` from Level 1.
- `baseline`: The names of comparison methods reported in the main result tables alongside Algorithm A on the extracted metrics. May be empty (`[]`) if the paper has no baselines.
