# Core Definitions

## Purpose

The pipeline extracts ML tasks from scientific papers to build benchmark challenges. The goal is **not** to reproduce the paper's algorithm or results — it is to test whether an AI agent (the "Solver") can independently solve the same ML problem, potentially using entirely different methods that surpass the original. The Solver receives the same initial data the paper's authors had, without knowing the paper or its algorithm. Its results are scored against ground truth using the paper's metrics, with the paper's reported scores (S/B) serving as performance baselines for comparison.

**Fairness principle**: The benchmark must give the Solver a fair starting point — including all legitimate initial data (excluding any would make the task unfairly harder) while withholding Algorithm A's own outputs (including any would leak solutions). This principle drives data boundary decisions throughout the pipeline.

## Candidate Task Tuple

Represent each potential ML task from a paper as a tuple:

```
T = (A, Data, M, S, B)
```

| Element | Name | Definition |
|---------|------|------------|
| A | Algorithm | The core algorithm or strategy proposed by the paper |
| Data | Data Environment | All data involved in the task, divided into D_dev and D_eval |
| M | Metric | The mathematical metric function used to measure result quality |
| S | SOTA | The performance values of the proposed core algorithm on evaluation metrics |
| B | Baseline | The baseline metric values reported in the paper (optional, may not exist) |

> Note: The extracted task must target the complete version of A proposed by the paper. All tuple elements (Data, M, S, B) and all filtering/extraction must correspond to the experiments of the complete A, not an ablation variant or partial component.

## Data Flow Definitions

### D_dev (Development Data Space)

**Definition**: All prior information that objectively exists and can be utilized by the original authors when starting to solve the problem.

**Components**:
- **Training data**: Used for learning parameters
- **Validation data**: Used for hyperparameter tuning
- **External resources**: Resources external to Algorithm A that the method depends on — pre-trained models, embeddings, knowledge bases, vocabularies, ontologies, simulators, oracles, parameter files, metadata files, etc. These may come from other work, the problem domain, or be provided by the paper's authors as part of the problem definition or data resouces (not as part of Algorithm A).

### D_eval (Evaluation Data Space)

**Definition**: The specific data used by the original paper to compute final metrics.

**Structure**:
```
D_eval = (X_test, Y_ref)
```

| Component | Name | Definition | Solver Visibility |
|-----------|------|------------|-------------------|
| X_test | Evaluation Input | The "problem" input to the algorithm during testing | Visible |
| Y_ref | Evaluation Reference | The "ground truth" used by the evaluator to compute metrics | Invisible |

**Y_ref types**:

| Type | X_test | Y_ref | D_dev typically includes |
|------|--------|-------|------------------------|
| **Label** — static ground truth (labels, scores, structures) | Input samples to predict on | Correct labels / reference values | Training data + validation data + external resources |
| **Oracle** — deterministic scoring function or simulator | Search space constraints / initial state | Objective function / simulator | Training data + validation data + external resources (including oracle if Solver needs it) |
| **Distribution** — target distribution or quality reference | Generation conditions / constraints | Reference sample set, distribution statistics, and/or oracles for quality evaluation | Training data + validation data + external resources (including oracle if Solver needs it) |

**Examples**:
- Classification (Label): X_test = images to classify, Y_ref = correct labels
- Protein folding (Label): X_test = sequences to predict, Y_ref = true 3D structure PDB files
- Image compression (Label): X_test = original images, Y_ref = original images (physically identical, logically separate)
- Optimization (Oracle): X_test = search space constraints/initial state, Y_ref = objective function/simulator
- Molecule generation (Distribution): X_test = generation conditions (e.g., target properties), Y_ref = reference sample set or quality statistics

## Process Completeness

A task is judged as "process complete" if and only if it satisfies all three of the following conditions:

### 1. D_dev Initial State Completeness

- **Algorithm Reachability**: Based on D_dev, the Solver must theoretically be able to derive the mapping function f: X → Y through e.g., training or fine-tuning
- **Dependency Closure**: If algorithm A depends on specific prior knowledge (pre-trained weights, knowledge graphs, etc.), these must be included in D_dev or directly indexable and publicly obtainable via meta-information in D_dev

**Failure cases**: SOTA is fine-tuned from an unpublished private model, or training data is insufficient

### 2. Evaluation Loop Completeness

- **Input/Reference Separation**: D_eval must be decomposable into X_test (problem) and Y_ref (answer)
- **Metric Computability**: M must be a deterministic function `Score = M(Y_out, Y_ref)` that yields a unique numerical value given only the algorithm's output `Y_out` and reference `Y_ref`, without human intervention. For Oracle-type tasks, M may involve running a simulator or scoring function; this is acceptable as long as the scorer is reproducible and locally executable.

**Failure cases**: Problem without solution (X_test exists but Y_ref is missing), or metric depends on subjective evaluation

### 3. Evaluation Alignment Completeness

- **Data Consistency**: The test set used by the original paper to produce S must be strictly identical to the obtainable D_eval
- **Version Consistency**: If D_eval has multiple versions, S must clearly correspond to the provided version

**Failure cases**: The original paper uses a private dataset, or public data has distribution bias compared to the original data

---

**Multiple Evaluation Settings Note**

A paper may involve multiple independent evaluation settings: D_total = {d_1, d_2, ..., d_n} (n ≥ 1).
An **Evaluation Setting** is the smallest unit for verifying process completeness, i.e., a (D_dev, D_eval) pair equipped with evaluation metrics.

> **Handling Principle**: The above three process completeness conditions are verified **independently for each evaluation setting**; as long as **at least one** setting satisfies all conditions, completeness is considered met.

## Usage Instructions

The main purpose of core definitions is to help understand the basic criteria and requirements for task extraction before filtering:

1. **Understand Task Structure**: Clarify what elements an extractable ML task should contain
2. **Guide Filtering Judgments**: Reference these definitions when evaluating whether a paper satisfies requirements in each rule
