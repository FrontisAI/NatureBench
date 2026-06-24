# Level 1: Task Nature Filtering

The pipeline seeks papers whose core contribution is an ML algorithm that can be extracted as a standalone benchmark task. A valid paper must propose an algorithm where an independent ML researcher, given the same data, could improve upon the results by designing better models, architectures, losses, or training methods — not by collecting better data, changing equipment, or modifying experimental setups. Papers that fail this premise are rejected at this level.

---

## Rule 1.1: ML Task Extractability

### Pass Conditions

A paper passes if it satisfies **any one** of the following three conditions.

**A. Algorithmic Innovation**

Proposes mathematical-level improvements to model architecture, loss function, optimizer, or sampling strategy. Examples: new Attention mechanism, new regularization method, new training strategy.

**B. Problem Formulation**

Formalizes a specific scientific problem as a clear ML task (input/output/objective), where the formalization itself constitutes the primary contribution. Must satisfy both:
1. Introduces new input representations, output spaces, or objective functions — not merely applying existing models to standard tasks
2. Validates the effectiveness of ML methods on this formalized task

Examples: defining protein folding as end-to-end distance matrix prediction, formulating drug response as graph-level regression.

**C. Methodological Adaptation**

Adapts general ML methods (e.g., Transformer, GNN) for a specific domain with non-trivial structural/architectural engineering or design work tailored to the domain. Designing a novel domain-specific fine-tuning strategy also qualifies. 

Examples: GNN variants designed for special properties of molecular graphs.

> **Note**: For example, hyperparameter tuning, data augmentation, or changing input data alone do NOT qualify as methodological adaptation.

**Coexistence of Computational and Wet Lab/Physical Experiments**: When a paper contains both computational and wet lab/physical experiments, determine where the core contribution lies. Pass if the core contribution is the computational/ML method and wet lab serves solely as downstream validation. Reject if wet lab/physical experiments are the primary research content, with the computational part playing an auxiliary or screening role.

### Reject Conditions

A paper is rejected if it matches **any one** of the following conditions.

**1. Validation Tool Usage**

ML is only used as a standard data analysis tool to support conclusions of non-ML research (experimental, theoretical, or observational studies), with no new ML-driven insights.

**2. Non-computational**

Satisfying any one of the following triggers rejection:
- Only involves wet lab experiments
- Pure theoretical derivation
- Hardware implementation without data-driven components
- Paper has both computational and wet lab content, but wet lab/physical experiments are the primary research content or core contribution

**3. Non-ML-Factor Comparison**

The core comparison is between different non-ML-method factors, using the same or off-the-shelf ML model. The following are diagnostic signs — the more that apply, the stronger the case for rejection:
- The main comparison is "factor X vs. factor Y, same model architecture"
- The paper's conclusion is "our factor/approach improves model performance" rather than "our model/method improves on the task"
- Removing the non-ML innovation leaves no ML contribution
- The ML model is interchangeable (any standard model would show the same advantage)

> **What counts as a non-ML-method factor?**
> Non-ML-method factors are external factors that do not contain learnable parameters, do not modify model architecture, and are not part of the learning algorithm itself.
> 
> **Specific examples**:
> - **Data representations**: Hand-crafted deterministic transformations
> - **Data sources**: Dataset selection, data modality, acquisition devices, data scale, noise characteristics,
> - **Domain knowledge**: External constraints, scientific rules, expert heuristics
> - **Training signal**: Label quality, annotation granularity, label sources
>
> The following are **not** non-ML factors (they are part of the ML method): learned representations (word2vec, VAE latent spaces), architecture-level knowledge integration (PINNs structure, GNN inductive biases), loss function design, reward shaping.

**4. Intermediate Data Evaluation**

Algorithm A produces intermediate data (synthetic samples, augmented features, learned representations, etc.) that is not directly evaluated; instead, evaluation relies on separate downstream ML models trained from scratch on A's output. The following are diagnostic signs — the more that apply, the stronger the case for rejection:
- A's output is intermediate material, not a directly evaluated end-task output
- Evaluation requires feeding A's output into separate downstream ML models (SVM, kNN, neural networks, etc.) that are **trained from scratch** on A's output
- The downstream models are not part of A's contribution

> **Exception**: This condition does NOT apply when evaluation uses deterministic computational tools (e.g., physics simulators, chemical validity checkers like RDKit, energy calculators like Rosetta). Such tools directly assess the quality of A's output without requiring training.

**5. Attribution / Explainability Analysis**

Core contribution is an attribution method or explainability framework focused on interpreting model behavior rather than improving a quality metric. The model's performance on the scientific task only serves as a testbed for the explanation method.

**6. General Methodology / Training Framework**

Proposes a general training strategy or optimization paradigm for multiple diverse models/tasks, not tied to a specific task instance. Verification requires implementation across different base model architectures, making it hard to define a single task tuple.

**7. Hardware-Dependent Execution**

The algorithm cannot run on general-purpose computing hardware. Satisfying any one of the following triggers rejection:
- Real-time physical interaction dependency: acquisition or verification of D_dev or D_eval depends on real-time physical device interaction (e.g., algorithm must connect to electron microscope for real-time parameter adjustment)
- Non-standard hardware dependency: depends on non-standard instruction sets or specific proprietary hardware accelerators (e.g., algorithm designed for a specific FPGA)

> Note: when data has already been collected and is downloadable, the acquisition equipment (drones, microscopes, etc.) does not constitute hardware dependency.

**8. Other Out of Scope**

The paper does not fit any pass condition and does not neatly fall into the specific reject categories above. Used as a catch-all for papers that fail the end-to-end task tuple extraction paradigm.

### Auxiliary Decision Tool: Algorithm A Litmus Test

When the boundary between pass and reject is unclear, ask:

> "If an ML researcher received D_dev and D_eval without knowing the paper, what would they change to beat SOTA?"

- If the answer involves designing a better model/architecture/loss function/training method → algorithmic innovation space exists → **pass**
- If the answer is to collect better data/change physical equipment/modify experimental design → no algorithmic innovation space → **reject**

---

## Task Info Extraction

Fields extracted at this Level: `task_info.task_type`, `task_info.algorithm`
