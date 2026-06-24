#!/usr/bin/env python3
"""Verify a case image built on top of naturebench-base:v3."""

import argparse
import json
import sys
from importlib import import_module, metadata
from pathlib import Path

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version


# Keep this list in sync with .claude/skills/task-build/references/Dockerfile.base.v3.
BASE_CHECKS = [
    ("numpy", "1.26.4", "numpy", "numpy"),
    ("scipy", "1.14.1", "scipy", "scipy"),
    ("pandas", "2.2.3", "pandas", "pandas"),
    ("matplotlib", "3.10.0", "matplotlib", "matplotlib"),
    ("seaborn", "0.13.2", "seaborn", "seaborn"),
    ("h5py", "3.12.1", "h5py", "h5py"),
    ("tables", "3.10.1", "tables", "tables"),
    ("pyarrow", "18.1.0", "pyarrow", "pyarrow"),
    ("networkx", "3.4.2", "networkx", "networkx"),
    ("igraph", "0.11.8", "igraph", "igraph"),
    ("sympy", "1.13.1", "sympy", "sympy"),
    ("statsmodels", "0.14.4", "statsmodels", "statsmodels"),
    ("scikit-image", "0.24.0", "scikit-image", "skimage"),
    ("opencv-python-headless", "4.11.0", "opencv-python-headless", "cv2"),
    ("Pillow", "11.1.0", "Pillow", "PIL"),
    ("tqdm", "4.67.1", "tqdm", "tqdm"),
    ("rich", "13.9.4", "rich", "rich"),
    ("jupyter", "1.1.1", "jupyter", "jupyter"),
    ("torch", "2.6.0", "torch", "torch"),
    ("torchvision", "0.21.0", "torchvision", "torchvision"),
    ("torchaudio", "2.6.0", "torchaudio", "torchaudio"),
    ("scikit-learn", "1.6.1", "scikit-learn", "sklearn"),
    ("xgboost", "2.1.3", "xgboost", "xgboost"),
    ("lightgbm", "4.5.0", "lightgbm", "lightgbm"),
    ("catboost", "1.2.7", "catboost", "catboost"),
    ("transformers", "4.48.1", "transformers", "transformers"),
    ("datasets", "3.2.0", "datasets", "datasets"),
    ("tokenizers", "0.21.0", "tokenizers", "tokenizers"),
    ("lightning", "2.5.0", "lightning", "lightning"),
    ("einops", "0.8.0", "einops", "einops"),
    ("timm", "1.0.12", "timm", "timm"),
    ("accelerate", "1.3.0", "accelerate", "accelerate"),
    ("optuna", "4.2.0", "optuna", "optuna"),
    ("safetensors", "0.5.2", "safetensors", "safetensors"),
    ("sentencepiece", "0.2.0", "sentencepiece", "sentencepiece"),
    ("wandb", "0.19.1", "wandb", "wandb"),
    ("anndata", "0.11.3", "anndata", "anndata"),
    ("biopython", "1.85", "biopython", "Bio"),
    ("rdkit", "2024.9.6", "rdkit", "rdkit"),
    ("ase", "3.23.0", "ase", "ase"),
    ("pymatgen", "2024.11.13", "pymatgen", "pymatgen"),
    ("nibabel", "5.3.2", "nibabel", "nibabel"),
    ("nilearn", "0.11.1", "nilearn", "nilearn"),
]

BASE_IMPORTS = {import_name for _, _, _, import_name in BASE_CHECKS}


def normalize_version(value: str) -> str:
    """Treat local tags and zero-padded segments as equivalent."""
    value = str(value).split("+", 1)[0]
    parts = []
    for part in value.split("."):
        if part.isdigit():
            parts.append(str(int(part)))
        else:
            parts.append(part)
    return ".".join(parts)


def version_matches(expected: str, actual: str) -> bool:
    expected = str(expected).strip()
    actual = str(actual).strip()

    if any(op in expected for op in ("<", ">", "=", "!", "~")):
        try:
            return Version(normalize_version(actual)) in SpecifierSet(expected)
        except (InvalidSpecifier, InvalidVersion):
            pass

    expected_norm = normalize_version(expected)
    actual_norm = normalize_version(actual)
    return actual_norm == expected_norm or actual_norm.startswith(expected_norm + ".")


def check_base_packages(overridden_imports: set[str] | None = None) -> tuple[int, int]:
    passed = 0
    failed = 0
    overridden_imports = overridden_imports or set()

    print(f"Python: {sys.version}")
    print("=" * 70)

    for display_name, expected, dist_name, import_name in BASE_CHECKS:
        if import_name in overridden_imports:
            print(f"↷ {display_name:<25} SKIP base check (overridden by task package)")
            continue

        try:
            import_module(import_name)
        except Exception as e:
            print(f"❌ {display_name:<25} IMPORT ERROR: {type(e).__name__}: {e}")
            failed += 1
            continue

        try:
            actual = metadata.version(dist_name)
        except Exception as e:
            print(f"❌ {display_name:<25} VERSION ERROR: {type(e).__name__}: {e}")
            failed += 1
            continue

        if version_matches(expected, actual):
            print(f"✅ {display_name:<25} OK (v{actual})")
            passed += 1
        else:
            print(f"❌ {display_name:<25} FAIL: expected {expected}, got {actual}")
            failed += 1

    return passed, failed


def get_overridden_base_imports(imports: list[tuple[str, str | None, str, str, str]]) -> set[str]:
    overridden = set()
    for _display_name, _expected_version, import_name, _pip_name, source in imports:
        if source == "task_packages" and import_name in BASE_IMPORTS:
            overridden.add(import_name)
    return overridden


def _extract_expected_version(entry: dict) -> str | None:
    for key in ("version", "expected_version", "specifier", "constraint"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            value = value.strip()
            if value.startswith("=="):
                value = value[2:].strip()
            return value
    return None


def load_extra_imports(path: str | None) -> list[tuple[str, str | None, str, str, str]]:
    if not path:
        return []

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("extra imports JSON must be a list")

    result = []
    seen = set()
    for item in data:
        if not isinstance(item, dict):
            continue

        source = item.get("source")
        if not isinstance(source, str) or not source.strip():
            source = "task_packages"
        else:
            source = source.strip()

        import_name = item.get("import")
        if not isinstance(import_name, str):
            continue

        import_name = import_name.strip()
        if not import_name:
            continue

        if source == "base_packages" and import_name in BASE_IMPORTS:
            continue

        dedupe_key = (source, import_name)
        if dedupe_key in seen:
            continue

        display_name = item.get("name")
        if not isinstance(display_name, str) or not display_name.strip():
            display_name = import_name
        else:
            display_name = display_name.strip()

        pip_name = item.get("pip")
        if not isinstance(pip_name, str) or not pip_name.strip():
            pip_name = display_name
        else:
            pip_name = pip_name.strip()

        expected_version = _extract_expected_version(item)

        seen.add(dedupe_key)
        result.append((display_name, expected_version, import_name, pip_name, source))
    return result


def _distribution_candidates(display_name: str, import_name: str, pip_name: str) -> list[str]:
    candidates = []
    for value in (
        display_name,
        import_name,
        pip_name,
        display_name.replace("_", "-"),
        import_name.replace("_", "-"),
        pip_name.replace("_", "-"),
    ):
        if value and value not in candidates:
            candidates.append(value)
    return candidates


def check_extra_imports(imports: list[tuple[str, str | None, str, str, str]]) -> tuple[int, int]:
    passed = 0
    failed = 0

    print("=" * 70)
    print("===== EXTRA CASE PACKAGES =====")

    if not imports:
        print("(none)")
        return passed, failed

    for display_name, expected_version, import_name, pip_name, source in imports:
        try:
            module = import_module(import_name)
        except Exception as e:
            print(f"❌ {display_name:<25} IMPORT ERROR [{source}]: {type(e).__name__}: {e}")
            failed += 1
            continue

        if not expected_version:
            print(f"✅ {display_name:<25} IMPORT OK [{source}]")
            passed += 1
            continue

        actual_version = None
        for candidate in _distribution_candidates(display_name, import_name, pip_name):
            try:
                actual_version = metadata.version(candidate)
                break
            except Exception:
                continue

        if not actual_version:
            actual_version = getattr(module, "__version__", None)

        if not actual_version:
            print(f"❌ {display_name:<25} VERSION ERROR [{source}]: could not determine version")
            failed += 1
            continue

        if version_matches(expected_version, actual_version):
            print(f"✅ {display_name:<25} OK [{source}] (v{actual_version})")
            passed += 1
        else:
            print(
                f"❌ {display_name:<25} FAIL [{source}]: expected {expected_version}, got {actual_version}"
            )
            failed += 1

    return passed, failed


def smoke_numpy():
    import numpy as np

    return np.array([1.0, 2.0, 3.0]).mean()


def smoke_scipy():
    from scipy import linalg

    return linalg.det([[1.0, 2.0], [3.0, 5.0]])


def smoke_pandas():
    import pandas as pd

    return pd.DataFrame({"x": [1, 2], "y": [3, 4]}).shape


def smoke_matplotlib():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.figure()
    plt.plot([0, 1], [0, 1])
    plt.close("all")
    return "plot ok"


def smoke_rdkit():
    from rdkit import Chem

    mol = Chem.MolFromSmiles("CCO")
    return mol.GetNumAtoms()


def smoke_pymatgen():
    from pymatgen.core import Lattice, Structure

    structure = Structure(Lattice.cubic(3.5), ["Li"], [[0, 0, 0]])
    return structure.formula


def smoke_sklearn():
    from sklearn.linear_model import LinearRegression

    return LinearRegression().fit([[0], [1], [2]], [0, 1, 2]).predict([[3]])[0]


def smoke_networkx():
    import networkx as nx

    return nx.path_graph(4).number_of_edges()


def smoke_transformers():
    from transformers import AutoConfig

    return AutoConfig.for_model("bert").model_type


def smoke_lightning():
    from lightning import Trainer

    trainer = Trainer(
        accelerator="cpu",
        devices=1,
        fast_dev_run=True,
        logger=False,
        enable_checkpointing=False,
    )
    return trainer.__class__.__name__


SMOKE_TESTS = [
    ("numpy", smoke_numpy),
    ("scipy", smoke_scipy),
    ("pandas", smoke_pandas),
    ("matplotlib", smoke_matplotlib),
    ("rdkit", smoke_rdkit),
    ("pymatgen", smoke_pymatgen),
    ("scikit-learn", smoke_sklearn),
    ("networkx", smoke_networkx),
    ("transformers", smoke_transformers),
    ("lightning", smoke_lightning),
]


def run_smoke_tests() -> tuple[int, int]:
    passed = 0
    failed = 0

    print("=" * 70)
    print("===== SMOKE TESTS =====")

    for name, fn in SMOKE_TESTS:
        try:
            result = fn()
            print(f"✅ {name:<25} SMOKE OK ({result})")
            passed += 1
        except Exception as e:
            print(f"❌ {name:<25} SMOKE FAIL: {type(e).__name__}: {e}")
            failed += 1

    return passed, failed


def run_gpu_check(require_gpu: bool) -> tuple[int, int, list[str]]:
    passed = 0
    failed = 0
    gpu_errors = []

    print("=" * 70)
    print("===== GPU / CUDA check =====")

    try:
        import torch
    except Exception as e:
        print(f"  ❌ Torch/CUDA check failed: {type(e).__name__}: {e}")
        if require_gpu:
            gpu_errors.append("torch unavailable or check raised an error")
            failed += 1
        return passed, failed, gpu_errors

    cuda_available = torch.cuda.is_available()
    device_count = torch.cuda.device_count()
    torch_cuda_version = torch.version.cuda

    print(f"  torch.cuda.is_available: {cuda_available}")
    print(f"  torch.cuda.device_count: {device_count}")
    print(f"  torch.version.cuda: {torch_cuda_version}")

    if cuda_available and device_count > 0:
        try:
            gpu_name = torch.cuda.get_device_name(0)
            print(f"  torch GPU0 name: {gpu_name}")
        except Exception as e:
            print(f"  torch GPU0 name: failed to retrieve ({e})")
            if require_gpu:
                gpu_errors.append("failed to retrieve torch GPU name")
                failed += 1

        try:
            x = torch.randn(512, 512, device="cuda")
            y = torch.mm(x, x)
            print(f"  ✅ CUDA compute OK, output shape={tuple(y.shape)}")
            passed += 1
        except Exception as e:
            print(f"  ❌ CUDA compute failed: {e}")
            if require_gpu:
                gpu_errors.append("CUDA compute failed")
                failed += 1
    else:
        print("  CUDA not available")
        if require_gpu:
            gpu_errors.append("torch.cuda.is_available() is False or no GPU device")
            failed += 1

    if require_gpu:
        if gpu_errors:
            print()
            print("GPU check conclusion: failed")
            for err in gpu_errors:
                print(f"  - {err}")
        else:
            print()
            print("GPU check conclusion: passed")
    else:
        print()
        print("GPU check conclusion: info mode (not enforced)")

    return passed, failed, gpu_errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a case image built from naturebench-base:v3")
    parser.add_argument("--extra-imports-json", help="JSON file containing extra import names")
    parser.add_argument("--require-gpu", action="store_true", help="Require CUDA checks to pass")
    args = parser.parse_args()

    passed = 0
    failed = 0

    extra_imports = load_extra_imports(args.extra_imports_json)
    overridden_base_imports = get_overridden_base_imports(extra_imports)

    base_passed, base_failed = check_base_packages(overridden_base_imports)
    passed += base_passed
    failed += base_failed

    extra_passed, extra_failed = check_extra_imports(extra_imports)
    passed += extra_passed
    failed += extra_failed

    smoke_passed, smoke_failed = run_smoke_tests()
    passed += smoke_passed
    failed += smoke_failed

    gpu_passed, gpu_failed, gpu_errors = run_gpu_check(args.require_gpu)
    passed += gpu_passed
    failed += gpu_failed

    print("=" * 70)
    print(f"Result: {passed} passed, {failed} failed, {passed + failed} total")
    if failed == 0:
        print("🎉 All checks passed!")
    else:
        print(f"⚠️  {failed} check(s) failed!")

    if base_failed or extra_failed or smoke_failed:
        return 1
    if args.require_gpu and gpu_errors:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
