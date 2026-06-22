"""Baseline dummy agent that mirrors BaseAgent prompts but avoids LLM calls."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional


SYSTEM_PROMPT = """# Role
You are an expert AI Researcher and Scientific Coder. Your goal is to solve the Scientific Machine Learning task described below.

# Context
The task documentation is provided in the following sections:
- **Task Description**: defines the problem, evaluation metrics, output format, and submission guidelines (including a `run.py` template).
- **Data Description**: introduces the dataset overview, data schema, file formats, and other relevant details.
{initial_idea_section}

# Environment
Your `run.py` will be executed with two environment variables:
- `DATA_DIR`: path to the read-only data directory (contains instance sub-folders).
- `OUTPUT_DIR`: path where you must write output files (one sub-folder per instance).

# Rules
1. **Interface Compliance**: Implement `run.py` exactly matching the template in README Section 6.
2. **Output Format**: Save results to `output/{{instance_name}}/` in the exact format specified in README Section 5.
3. **Complete Implementation**: Do NOT simplify logic. Implement ALL required steps even if code is long.
4. **Metric Optimization**: Optimize for the Primary Metric in README.
5. **Read-Only Data**: Do NOT modify existing files. Only write to the output directory.
6. **Anti-Cheating**: NEVER use test-set labels for training/validation/feature engineering.
{methodology_rule}

# Output Format
1. **Research Plan** (3-5 sentences): Goal, Method, Reasoning
2. **Implementation**: Single ```python``` code block with complete `run.py`
"""

INITIAL_IDEA_SECTION = """- **Reference: Methodological Framework**: describes a high-quality SOTA approach. Use this as a starting point or inspiration."""

METHODOLOGY_RULE = """7. **Innovation & Optimization**: Use the **Reference: Methodological Framework** as a strong hint/baseline. You are encouraged to INNOVATE, try NOVEL approaches, or significantly OPTIMIZE the architecture. Do not feel constrained to simply reproduce it; your goal is to achieve the best possible performance, potentially OUTPERFORMING the reference."""

TASK_DESCRIPTION_TEMPLATE = """
---
**Task Description**

{task_description}
"""

DATA_DESCRIPTION_TEMPLATE = """
---
**Data Description**

{data_description}
"""

INITIAL_IDEA_TEMPLATE = """
---
**Reference: Methodological Framework (SOTA Approach)**

{initial_idea}
"""


class DummyAgent:

    def __init__(
        self,
        mode: str = "base",
    ) -> None:
        self.trajectory: List[Dict[str, Any]] = []
        self.system_prompt = ""
        self.mode = mode
        self.logger = logging.getLogger("cns_bench.agent.DummyAgent")

    def build_system_prompt(self, task: Dict[str, Any]) -> str:
        """Build the complete prompt for the task."""
        task_description = task.get("task_description", "")
        data_description = task.get("data_description", "")
        initial_idea = task.get("initial_idea", "")

        if self.mode == "reference":
            initial_idea_section = INITIAL_IDEA_SECTION
            methodology_rule = METHODOLOGY_RULE
        else:
            initial_idea_section = ""
            methodology_rule = ""

        system_section = SYSTEM_PROMPT.format(
            initial_idea_section=initial_idea_section,
            methodology_rule=methodology_rule,
        )

        task_section = TASK_DESCRIPTION_TEMPLATE.format(
            task_description=task_description.strip(),
        )

        data_section = DATA_DESCRIPTION_TEMPLATE.format(
            data_description=data_description.strip(),
        )

        sections = [system_section, task_section, data_section]

        if self.mode == "reference" and initial_idea.strip():
            idea_section = INITIAL_IDEA_TEMPLATE.format(
                initial_idea=initial_idea.strip(),
            )
            sections.append(idea_section)

        return "\n".join(sections).strip()

    def _build_plan(self, task: Dict[str, Any]) -> str:
        return (
            "This is a dummy baseline solution. "
            "It implements a minimal run.py that loads data and generates placeholder predictions. "
            "The goal is to validate the evaluation pipeline works correctly."
        )

    def _build_code(self) -> str:
        return '''import os
import numpy as np

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "problem", "data"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(os.path.dirname(__file__), "output"))

def main():
    if not os.path.isdir(DATA_DIR):
        print(f"DATA_DIR not found: {DATA_DIR}")
        return

    instances = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]
    print(f"Instances: {instances}")

    for instance in instances:
        output_path = os.path.join(OUTPUT_DIR, instance)
        os.makedirs(output_path, exist_ok=True)
        np.save(os.path.join(output_path, "output.npy"), np.zeros(10))
        print(f"Saved dummy output for {instance}")

if __name__ == "__main__":
    main()
'''

    def solve_task(
        self,
        task: Dict[str, Any],
        llm_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.system_prompt = self.build_system_prompt(task)

        workspace_path = Path(task.get("workspace_path"))
        workspace_path.mkdir(parents=True, exist_ok=True)
        run_file = workspace_path / "run.py"

        plan = self._build_plan(task)
        code = self._build_code()

        run_file.write_text(code, encoding="utf-8")
        self.logger.info("Solution saved to %s", run_file)

        self.trajectory = [
            {
                "step": 0,
                "plan": plan,
                "code": code,
            }
        ]

        return {
            "trajectory": self.trajectory,
            "mode": self.mode,
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }
