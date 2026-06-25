
"""Base agent implementation for NatureBench, inspired by ScienceAgentBench."""
from __future__ import annotations

import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Tuple

# =============================================================================
# SYSTEM PROMPT
# =============================================================================
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
1.  **Interface Compliance**: Implement `run.py` exactly matching the template in README Section 6. Use `DATA_DIR` and `OUTPUT_DIR` environment variables.
2.  **Output Format**: Save results to `output/{{instance_name}}/` in the exact format specified in README Section 5 (file name, shape, dtype, value range).
3.  **Completeness Over Brevity**: Do NOT simplify the solution logic or skip steps just to keep the file short. You must implement a fully functional, robust, and comprehensive solution. If the task requires complex multi-step processing, implement ALL of it. Even if the code is long, it must completely fulfill the task requirements.
4.  **Metric Optimization**: Optimize for the Metrics (especially Primary Metric) in README.
5.  **Production Ready**: Code should be clean, commented, and handle potential missing values or edge cases defined in the Data Description.
6.  **Read-Only Data**: Do NOT modify any files in the data directory. Only write to the output directory.
7.  **Anti-Cheating & Data Integrity**: You are strictly FORBIDDEN from using ground truth labels (targets) corresponding to the test set for training, validation, feature engineering, or directly as output values.
{methodology_rule}

# Output Format
1. **Research Plan** (3-5 sentences): Goal, Method, Reasoning
2. **Implementation**: Single ```python``` code block with complete `run.py`
"""

# Reference mode additions
INITIAL_IDEA_SECTION = """- **Reference: Methodological Framework**: describes a high-quality SOTA approach. Use this as a starting point or inspiration."""

METHODOLOGY_RULE = """7. **Innovation & Optimization**: Use the **Reference: Methodological Framework** as a strong hint/baseline. You are encouraged to INNOVATE, try NOVEL approaches, or significantly OPTIMIZE the architecture. Do not feel constrained to simply reproduce it; your goal is to achieve the best possible performance, potentially OUTPERFORMING the reference."""

# =============================================================================
# CONTENT TEMPLATES
# =============================================================================
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

class BaseAgent:

    def __init__(
        self,
        model_name: str,
        backend_kwargs: Optional[Dict[str, Any]] = None,
        mode: str = "base",  # "base" or "reference"
    ) -> None:
        self.model_name = model_name
        # Imported lazily so the single-shot LLM backend (and its optional
        # openai/backoff dependencies) is only required when a BaseAgent is
        # actually constructed. The CLI agents do not use this path.
        from .backend.base_backend import LLMBackend
        self.backend = LLMBackend(model_name, **(backend_kwargs or {}))
        self.trajectory: List[Dict[str, Any]] = []
        self.system_prompt = ""
        self.mode = mode  # "base" or "reference"
        self.logger = logging.getLogger(f"cns_bench.agent.{self.__class__.__name__}")

    # ------------------------------------------------------------------
    # Prompt helpers
    # ------------------------------------------------------------------
    def build_system_prompt(self, task: Dict[str, Any]) -> str:
        """Build the complete prompt for the task."""
        task_description = task.get("task_description", "")
        data_description = task.get("data_description", "")
        initial_idea = task.get("initial_idea", "")
        
        # Build system prompt with mode-specific sections
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
        
        # Add initial_idea section in reference mode
        if self.mode == "reference" and initial_idea.strip():
            idea_section = INITIAL_IDEA_TEMPLATE.format(
                initial_idea=initial_idea.strip(),
            )
            sections.append(idea_section)
        
        return "\n".join(sections).strip()

    def build_messages(self, prompt: str) -> List[Dict[str, str]]:
        messages = [{"role": "user", "content": prompt}]
        return messages

    # ------------------------------------------------------------------
    # Core functionality
    # ------------------------------------------------------------------
    def call_model(
        self,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> Tuple[str, int, int, float]:
    
        # prompt_chars = sum(len(m.get("content", "")) for m in messages)
        # self.logger.info("Prompt built (chars=%d)", prompt_chars)
        
        temperature = kwargs.get("temperature", "N/A")
        self.logger.info("Calling LLM model='%s' temperature=%s", self.model_name, temperature)
        
        start_time = time.time()
        try:
            response, prompt_tokens, completion_tokens = self.backend.respond(messages, **kwargs)
            duration = time.time() - start_time
            self.logger.info("LLM call finished in %.1fs", duration)
            return response, prompt_tokens, completion_tokens, duration
        except Exception:
            duration = time.time() - start_time
            self.logger.info("LLM call failed in %.1fs", duration)
            raise

    def _extract_plan_and_code(self, assistant_output: str) -> Tuple[str, str]:
        """Split response into natural-language plan and python code."""
        match = re.search(r"```(?:python)?(.*?)```", assistant_output, re.DOTALL | re.IGNORECASE)
        if not match:
            return assistant_output.strip(), assistant_output.strip()
        plan = assistant_output[: match.start()].strip()
        code = match.group(1).strip()
        return plan, code

    def solve_task(
        self,
        task: Dict[str, Any],
        llm_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.system_prompt = self.build_system_prompt(task)

        workspace_path = Path(task.get("workspace_path"))
        workspace_path.mkdir(parents=True, exist_ok=True)
        run_file = workspace_path / "run.py"

        messages = self.build_messages(self.system_prompt)
        llm_kwargs = llm_kwargs or {}

        assistant_output, prompt_tokens, completion_tokens, duration = self.call_model(messages, **llm_kwargs)
        plan, code = self._extract_plan_and_code(assistant_output)
        self.logger.info(
            "Solution generation complete (prompt_tokens=%s, completion_tokens=%s)",
            prompt_tokens,
            completion_tokens,
        )

        run_file.write_text(code, encoding="utf-8")
        self.logger.info("Solution saved to %s", run_file)
        

        total_prompt_tokens = prompt_tokens
        total_completion_tokens = completion_tokens

        self.trajectory = [
            {
                "plan": plan,
                "code": code,
            }
        ]

        return {
            "trajectory": self.trajectory,
            "mode": self.mode,
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "model": self.model_name,
            "llm_call_duration": duration,
        }
