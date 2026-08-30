from __future__ import annotations

import json
import shutil
from importlib.resources import files
from pathlib import Path
from typing import Any

CACHE_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")

_GPU_TYPES_BY_GROUP = {
    "cpu": (),
    "gpu_low": ("RTX 3090", "RTX 4090"),
    "gpu_high": ("A800", "A100"),
}

_RELEASE_DOMAINS = {
    "Biomedical Modeling",
    "Cellular Omics",
    "Molecular Design",
    "Physical Modeling",
    "Protein Biology",
    "Relational Reasoning",
}

def _template_path() -> Path:
    return Path(str(files("naturebench_adapter").joinpath("task_template")))


def _source_paper_index_path() -> Path:
    return Path(
        str(
            files("naturebench_adapter").joinpath(
                "source_data", "judge_source_papers.jsonl"
            )
        )
    )


def _source_paper_record(index_path: Path, task_id: str) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        index_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"invalid source-paper record at {index_path}:{line_number}"
            ) from error
        if isinstance(record, dict) and record.get("case_id") == task_id:
            matches.append(record)
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one source-paper record for {task_id}, found {len(matches)}"
        )
    return matches[0]


def _release_domain(source_paper: dict[str, Any], task_id: str) -> str:
    domain = source_paper.get("domain")
    if domain not in _RELEASE_DOMAINS:
        raise ValueError(f"invalid release domain for {task_id}: {domain!r}")
    return domain


def _read_metadata(source_task: Path) -> dict[str, Any]:
    metadata_path = source_task / "metadata.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(metadata_path)
    value = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"metadata must be an object: {metadata_path}")
    return value


def _source_dockerfile(source_task: Path) -> Path:
    dockerfile = source_task / "environment" / "Dockerfile.v3"
    if not dockerfile.is_file():
        raise FileNotFoundError(dockerfile)
    return dockerfile


def _resource_group(task_id: str) -> str:
    group_dir = files("naturebench_adapter").joinpath("source_data", "task_set")
    matches: list[str] = []
    for group in _GPU_TYPES_BY_GROUP:
        task_ids = {
            line.strip()
            for line in group_dir.joinpath(f"{group}.txt").read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        }
        if task_id in task_ids:
            matches.append(group)
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one release resource group for {task_id}, "
            f"found {matches}"
        )
    return matches[0]


def _toml_string(value: Any) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def _gpu_healthcheck_command(
    acceptable_types: tuple[str, ...],
    required_count: int,
) -> str:
    model_pattern = "|".join(acceptable_types)
    return (
        "nvidia-smi --query-gpu=name --format=csv,noheader | "
        "awk '{ total++ } $0 ~ /(" + model_pattern + ")/ { matched++ } "
        "END { exit(total == "
        f"{required_count} && matched == {required_count} ? 0 : 1) }}'"
    )


def _task_toml(
    task_id: str,
    metadata: dict[str, Any],
    resource_group: str,
    domain: str,
) -> str:
    title = metadata.get("task_name") or task_id
    acceptable_types = _GPU_TYPES_BY_GROUP[resource_group]
    gpus = 1 if acceptable_types else 0
    gpu_types = ""
    gpu_healthcheck = "\n"
    if acceptable_types:
        gpu_types = "gpu_types = [" + ", ".join(
            _toml_string(value) for value in acceptable_types
        ) + "]\n"
        healthcheck_command = _gpu_healthcheck_command(acceptable_types, gpus)
        gpu_healthcheck = f'''\n[environment.healthcheck]
command = {_toml_string(healthcheck_command)}
timeout_sec = 30.0
interval_sec = 2.0
retries = 3

'''
    return f'''schema_version = "1.4"

artifacts = [
  {{ source = "/workspace", service = "main" }},
  {{ source = "/logs/agent/trajectory.json", service = "main" }},
  {{ source = "/state/submissions.jsonl", service = "naturebench-eval" }},
  {{ source = "/state/best_score.json", service = "naturebench-eval" }},
  {{ source = "/state/eval_service.log", service = "naturebench-eval" }},
]

[task]
name = "naturebench/{task_id}"
description = {_toml_string(title)}
keywords = ["naturebench", "scientific-machine-learning", {_toml_string(domain)}]

[agent]
timeout_sec = 43200.0

[environment]
build_timeout_sec = 7200.0
gpus = {gpus}
{gpu_types}network_mode = "public"
{gpu_healthcheck}[verifier]
environment_mode = "separate"
timeout_sec = 1800.0

[verifier.environment]
build_timeout_sec = 1200.0
gpus = 0
network_mode = "public"

[verifier.env]
JUDGE_MODEL = "${{JUDGE_MODEL:-gpt-5.5}}"
JUDGE_API_KEY = "${{JUDGE_API_KEY:-}}"
JUDGE_BASE_URL = "${{JUDGE_BASE_URL:-}}"

[[verifier.collect]]
service = "naturebench-eval"
command = "/opt/naturebench/bin/drain-and-finalize"
timeout_sec = 3700.0
'''


def _write_agent_dockerfile(source: Path, target: Path) -> None:
    original = source.read_text(encoding="utf-8").rstrip()
    original = original.replace(
        "FROM cnsbench-base:v3",
        "FROM naturebench-base:v3",
    )
    lines = original.splitlines()
    workdir_indices = [
        index
        for index, line in enumerate(lines)
        if line.lstrip().split(maxsplit=1)
        and line.lstrip().split(maxsplit=1)[0].upper() == "WORKDIR"
    ]
    if not workdir_indices:
        rendered = original + "\n\nWORKDIR /workspace\n"
    else:
        index = workdir_indices[-1]
        current = lines[index].lstrip().split(maxsplit=1)
        if len(current) < 2 or current[1].strip() != "/workspace":
            indentation = lines[index][: len(lines[index]) - len(lines[index].lstrip())]
            lines[index] = indentation + "WORKDIR /workspace"
        rendered = "\n".join(lines) + "\n"
    target.write_text(rendered, encoding="utf-8")


def _validate_source(source_task: Path) -> None:
    required = (
        source_task / "problem" / "README.md",
        source_task / "problem" / "data_description.md",
        source_task / "problem" / "data",
        source_task / "evaluation" / "evaluator.py",
        source_task / "licenses",
        source_task / "metadata.json",
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("missing NatureBench task inputs: " + ", ".join(missing))


def convert_task(
    source_task: Path,
    output_root: Path,
    *,
    overwrite: bool = False,
    source_paper_index_path: Path | None = None,
) -> Path:
    source_task = source_task.resolve()
    _validate_source(source_task)
    metadata = _read_metadata(source_task)
    task_id = source_task.name
    resource_group = _resource_group(task_id)
    source_paper_index_path = (
        source_paper_index_path
        or _source_paper_index_path()
    )
    source_paper = _source_paper_record(source_paper_index_path, task_id)
    domain = _release_domain(source_paper, task_id)
    output_root.mkdir(parents=True, exist_ok=True)
    target = output_root / task_id
    if target.exists():
        if not overwrite:
            raise FileExistsError(target)
        shutil.rmtree(target)

    template = _template_path()
    shutil.copytree(template, target, ignore=CACHE_IGNORE)
    instruction_template = target / "instruction.md.j2"
    instruction_template.rename(target / "instruction.md")
    compose_template = target / "environment" / "docker-compose.yaml.j2"
    gpu_reservation = ""
    if _GPU_TYPES_BY_GROUP[resource_group]:
        gpu_reservation = '''    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]'''
    compose = (
        compose_template.read_text(encoding="utf-8")
        .replace("__TASK_ID__", task_id)
        .replace("__GPU_RESERVATION__", gpu_reservation)
    )
    compose_template.with_suffix("").write_text(compose, encoding="utf-8")
    compose_template.unlink()

    shutil.copytree(
        source_task / "problem",
        target / "environment" / "input",
        ignore=CACHE_IGNORE,
    )
    shutil.copytree(
        source_task / "evaluation",
        target / "environment" / "sidecar" / "evaluation",
        ignore=CACHE_IGNORE,
    )
    shutil.copy2(source_task / "metadata.json", target / "environment" / "sidecar" / "metadata.json")
    _write_agent_dockerfile(_source_dockerfile(source_task), target / "environment" / "Dockerfile")
    shutil.copytree(
        source_task / "licenses",
        target / "licenses",
        ignore=CACHE_IGNORE,
    )

    context = target / "tests" / "context"
    context.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_task / "problem" / "README.md", context / "README.md")
    shutil.copy2(source_task / "problem" / "data_description.md", context / "data_description.md")
    (target / "tests" / "judge_source_papers.jsonl").write_text(
        json.dumps(source_paper, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (target / "task.toml").write_text(
        _task_toml(task_id, metadata, resource_group, domain),
        encoding="utf-8",
    )
    return target
