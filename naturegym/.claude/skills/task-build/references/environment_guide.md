# Phase 5: Environment Guide

## Objective

Generate `environment/Dockerfile.v3` — defines the execution environment for the task. The Dockerfile specifies all dependencies needed to run **both** the agent's solver code **and** the evaluator. This is a shared environment — both sides' dependencies must be satisfied by the same Dockerfile.

## Information Sources

1. **filter_result.json**: `task_info.dependencies` — libraries the original paper used (reference hints, not hard requirements)
2. **`repositories/`**: Author's `requirements.txt`, `setup.py`, `environment.yml`, `pyproject.toml` — concrete dependency lists (also hints)
3. **`evaluation/evaluator.py`**: All imports — **hard requirements for the evaluator side**
4. **Scripts in `evaluation/`**: Any auxiliary `.py` files (oracles, scoring scripts) — **hard requirements for the evaluator side**
5. **Scripts in `problem/data/`**: Any `.py` files (oracles, simulators, benchmark scripts) — **hard requirements for the solver side**
6. **Domain knowledge**: Common tools and libraries used in the task's scientific domain — for solver convenience (broader than the original paper)

## Base Image

All task Dockerfiles inherit from `naturebench-base:v3` by default. The base image Dockerfile is at [references/Dockerfile.base.v3](Dockerfile.base.v3), which contains all pre-installed packages with pinned versions.

The base image uses **Python 3.11** via an isolated virtual environment at `/opt/py311`, placed first on `PATH`. All `python`, `pip` commands in task Dockerfiles resolve to this environment.

### Pre-installed Packages

**System**: Python 3.11, CUDA 11.8 + cuDNN (devel), build-essential, cmake, gfortran, git, wget, curl, swig, ffmpeg, libhdf5-dev, libopenblas-dev

**Core Scientific**:
numpy, scipy, pandas, matplotlib, seaborn, h5py, tables, pyarrow, networkx, igraph, sympy, statsmodels, scikit-image, opencv-python-headless, Pillow, tqdm, rich, jupyter

**ML Frameworks**:
torch/torchvision/torchaudio (CUDA 11.8), scikit-learn, xgboost, lightgbm, catboost

**DL Ecosystem**:
transformers, datasets, tokenizers, lightning, einops, timm, accelerate, optuna, safetensors, sentencepiece, wandb

**Biology**: anndata, biopython
**Chemistry**: RDKit
**Materials Science**: ase, pymatgen
**Medical Imaging**: nibabel, nilearn

**Intentionally not pre-installed**: TensorFlow, JAX, Scanpy, and other large or fast-moving domain stacks that are better added per task.

> All base image packages are pinned to specific versions for reproducibility. See [references/Dockerfile.base.v3](Dockerfile.base.v3) for the exact version list.

### CUDA / PyTorch Baseline

- `v3` standardizes on **CUDA 11.8 + cuDNN 8** with `torch==2.6.0`, `torchvision==0.21.0`, and `torchaudio==2.6.0` installed from `https://download.pytorch.org/whl/cu118`.
- If a task Dockerfile inherits from `naturebench-base:v3`, treat `torch 2.6 + cu118` as the fixed GPU ABI. Do **not** mix in wheels built for `cu124`, `cu126`, `cu128`, or a different torch minor unless you intentionally switch to a standalone Dockerfile.
- Torch ecosystem packages with compiled extensions must match **both** the torch minor and the CUDA variant. This includes packages such as `dgl`, `torch-geometric`, `pyg-lib`, `torch-scatter`, `torch-sparse`, `torch-cluster`, `torch-harmonics`, `e3nn`, and `nequip`.
- TensorFlow, JAX, CuPy, `xformers`, `flash-attn`, and similar GPU-heavy stacks are **not** covered by the base image's torch choice. Treat them as separate CUDA toolchains and verify their published Python/CUDA compatibility explicitly before adding them.
- **JAX ecosystem lock (v3 base, CUDA 11.8)**: JAX dropped `cuda11` jaxlib wheels after `0.4.25` — `jaxlib==0.4.26` and later only publish `+cuda12.cudnn89` / `+cuda12.cudnn91` variants (verify at `https://storage.googleapis.com/jax-releases/jax_cuda_releases.html`; `0.4.26+cuda11.cudnn86` **does not exist** and will fail the build). On the v3 base the maximum installable GPU JAX is **`jax==0.4.25` + `jaxlib==0.4.25+cuda11.cudnn86`** (from the same find-links URL), which pins `numpy<2.0` (compatible with base `numpy==1.26.4`). For CPU-only JAX (no CUDA), `jax==0.4.30` is a reasonable upper bound that still supports `numpy==1.26.4`; do not go past `jax==0.4.31` on base numpy because `jax>=0.4.31` accesses `numpy.dtypes.StringDType` (numpy 2.0+) and crashes at import on base numpy. JAX ecosystem packages (`chex`, `optax`, `dm-haiku`, `flax`, `distrax`, `tensorflow-probability`, `folx`, `kfac-jax`, `e3nn-jax`, `equinox`, `jraph`, etc.) mostly declare only a loose `jax>=X` lower bound in their `Requires-Dist`, so pip's resolver, when installing *any* of these in a later `RUN` layer, silently upgrades `jax` past the pinned version to satisfy some unrelated transitive — which then cascades into `numpy>=2.0`, breaking `catboost` (`numpy.dtype size changed 96→88`), and invalidating the entire GPU toolchain (jaxlib CPU-only). Seen in practice: a Dockerfile with `jax==0.4.25` installed first was upgraded to `jax==0.10.0` after later installing `e3nn-jax==0.20.4` / `tensorflow-probability==0.24.0` / `folx==0.2.6` / `kfac-jax==0.0.6`, with 6 downstream imports failing. **Rules**: (1) pick all JAX ecosystem versions from the same time window as the target jax (for jax 0.4.25 / April 2024: `chex==0.1.86`, `optax==0.2.2`, `dm-haiku==0.0.12`, `flax==0.8.3`, `distrax==0.1.5`, `tensorflow-probability==0.24.0`, `kfac-jax==0.0.6`, `e3nn-jax==0.20.4`, `folx==0.2.6`) and pin **all of them explicitly** in the same `RUN` layer — do not rely on a JAX-ecosystem package (e.g. `dm-haiku`) to pull a compatible `flax`/`chex`/`optax` as a transitive, because their `Requires-Dist` typically only declares a lower bound (`dm-haiku==0.0.12` declares `flax>=0.7.1` with no upper bound, so pip pulls `flax==0.12.x`, whose modules access `jax.sharding.AbstractMesh` added only in `jax>=0.4.33`, and `import haiku` fails with `AttributeError: module 'jax.sharding' has no attribute 'AbstractMesh'`); if the Dockerfile also installs a GitHub-source package like `learned-optimization` that has its own ecosystem pins in `setup.py` (e.g. `'flax==0.3.3'`), `sed`-patch those pins too so its install step does not drift or downgrade the locked set; (2) for each candidate, check PyPI `Requires-Dist` for a jax upper bound — if absent, assume it will upgrade jax and plan accordingly; (3) **always** end the Dockerfile with a tail re-pin that forces jax, jaxlib, AND numpy back to the target versions in one `--force-reinstall --no-deps` step: `RUN python -m pip install --no-cache-dir --force-reinstall --no-deps "jax==0.4.25" "jaxlib==0.4.25+cuda11.cudnn86" -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html && python -m pip install --no-cache-dir --force-reinstall --no-deps "numpy==1.26.4"` — numpy tail-pin is required because pinning jax alone does not prevent prior layers from having left numpy 2.x in place. **Always verify the exact `<version>+cuda11.cudnn86` string exists on the find-links page before committing a pin** — copy-pasting a version number from elsewhere without verification is the most common failure mode (a wheel that doesn't exist causes an unrecoverable build error). Same reasoning as the `setuptools==70.3.0` tail pin for `pkg_resources`.

### Python Contract

`naturebench-base:v3` places Python 3.11 at `/opt/py311` first on `PATH`. In derived task images:
- Use `python -m pip install ...` for Python dependencies
- Do not modify `/usr/bin/python3` or the system Python
- Do not `pip install` into the system Python

## Dockerfile Generation

### Step 1: Collect All Required Packages

Identify every package needed from **all sources**, classified into four tiers:

1. **Evaluator imports** — extract non-stdlib imports from `evaluation/evaluator.py` and all auxiliary `.py` scripts in `evaluation/`. These are **non-negotiable**: the evaluator crashes without them.

2. **Solver-side script imports** — extract non-stdlib imports from all `.py` files in `problem/data/` (oracles, simulators, benchmark evaluation scripts). These are **non-negotiable**: the solver sees and may call these scripts; they must run in the environment.

3. **Paper core dependencies** — from `task_info.dependencies` in `filter_result.json` and author's requirements files in `repositories/`. These are the tools the paper used and typically the tools a solver needs to approach the same problem. **These should be included** unless they are genuinely not installable (see Step 2).

4. **Domain-common tools** — tools commonly used in the task's scientific domain that a solver might reasonably need, even if the original paper didn't use them. **Include on a best-effort basis** — only skip if they cause irreconcilable conflicts or are not available for Python 3.11.

**Important**: This environment is primarily for the solver. The solver (an AI agent) can only use packages that are installed in the Docker image. Omitting a dependency the solver needs means the task may become unsolvable or unreasonably difficult. Therefore, tiers 1-3 are all **required**, and tier 4 should be included unless there is a concrete technical reason not to.

For each identified package, note its **import name** (e.g., `sklearn`) and its **PyPI name** (e.g., `scikit-learn`).

### Step 2: For Each Package, Make a Judgment

Apply this decision process in order:

**① Is it already in the base image?**
- Check `Dockerfile.base.v3` pip install lines. If the package (or an alias) is listed → **skip, do not add**.
- Base packages cover most common scientific Python. When in doubt, still try adding it — pip will skip already-installed packages.

**② Is the package available on PyPI for Python 3.11?**
- Verify the package exists on PyPI and has a wheel or sdist for Python 3.11.
- If **not available** (e.g., deprecated project, no PyPI release, Cython build failure on Python 3.11):
  - If a Tier 1/2 script (evaluator or solver-side script) imports this package: **fix the script first** (see "Script-First Rule" below) — remove the dependency or substitute with an available alternative.
  - If it's a Tier 3 paper dependency (evaluator/scripts don't import it, but solver would need it): look for an alternative package that provides similar functionality. If none exists, omit it with a Dockerfile comment explaining why.
  - If it's a Tier 4 domain tool: skip it and note in the Dockerfile comment.

**③ Is it compatible with base packages at Python 3.11?**

A "compatible version" means: installing this exact version will NOT cause pip to upgrade or downgrade any base package. This is critical because base packages with C extensions (catboost, scipy, scikit-learn, h5py, torch, etc.) are compiled against specific dependency versions — if numpy gets silently pulled from 1.26.4 to 2.x, these C extensions crash at runtime (`numpy.dtype size changed`).

**How to verify compatibility for a candidate version**:
1. Check the package's PyPI metadata (`Requires-Dist`) for its dependency bounds
2. Confirm every dependency bound is satisfied by the base version — e.g., if the package requires `numpy>=1.22,<2.0`, and base has `numpy==1.26.4`, that's compatible
3. If a dependency bound excludes the base version (e.g., `numpy>=2.2`), this version is NOT compatible — try an older version of the package, or see "Handling Version Conflicts"

**Key base versions to check against** (from `Dockerfile.base.v3`):
- `numpy==1.26.4` — most common conflict point (numpy<2.0; packages requiring numpy>=2.0 are NOT compatible)
- `scipy==1.14.1`
- `torch==2.6.0`
- `pandas==2.2.3`
- `scikit-learn==1.6.1`

**Known compatibility notes**:
- TensorFlow: use ≥2.16.0,<=2.18.x (these require numpy<2.0 which matches base numpy==1.26.4; ≥2.19.0 requires numpy>=2.0 and is NOT compatible with the base)
- catboost==1.2.7: declares `numpy<2.0`, fully compatible with base numpy==1.26.4 — no ABI issues
- PyTorch wheel baseline: for `torch==2.6.0`, upstream publishes multiple CUDA wheel variants, but `v3` is pinned to `cu118`. Task packages that inherit from base should keep using the `cu118` variant for torch-related add-ons unless they intentionally move to a standalone image.
- torch-geometric, nequip, e3nn: check their numpy bounds — some versions require `numpy>=2.0` which is NOT compatible with base
- Any package with a strict `numpy>=2.0` bound is NOT compatible with the base (base has numpy==1.26.4)

**Known compatibility issues** (discovered from verified Dockerfile failures):
- `catboost==1.2.7`: declares `numpy>=1.16.0,<2.0`. Fully compatible with base numpy==1.26.4. No ABI issues. However, if the task's Dockerfile installs packages that trigger numpy upgrade to 2.x, catboost will break (`numpy.dtype size changed`). Avoid installing packages that pull numpy>=2.0.
- DGL from wrong torch wheel index: `dgl` installed from a mismatched wheel index will replace the base image's `torch==2.6.0+cu118` with a different version (e.g., CPU or newer minor version). This underlying change breaks the ABI for the already-installed `torchvision` and `torchaudio` C extensions, causing them to fail on import. **Diagnosis**: if you see torchvision, torchaudio, lightning, timm, or PyG extensions all failing simultaneously, first check whether torch itself was replaced — run `pip show torch` and verify the version is still `2.6.0` with the `+cu118` suffix. If torch was downgraded (e.g., to 2.4.0), that is the single root cause; do not attempt to fix the downstream packages individually. **Fix**: **Always** use the matching `torch-2.6` wheel index for the base CUDA variant (e.g., `dgl==2.5.0 -f https://data.dgl.ai/wheels/torch-2.6/cu118/repo.html`). After installing DGL, verify that `torchvision` and `torchaudio` still import correctly.
- PyTorch Geometric family from wrong wheel matrix: packages such as `pyg-lib`, `torch-scatter`, `torch-sparse`, and `torch-cluster` ship wheels keyed to both torch and CUDA. In a `v3` image, prefer `pt26cu118` builds. Mixing `pt26cu124`/`pt26cu126`, `pt25*`, or source builds compiled against a different local CUDA toolchain can produce `undefined symbol` or import-time ABI errors across the PyG stack.
- DGL/dgllife may remove `setuptools`: Some DGL installations uninstall `setuptools` as a side effect. This is one trigger for the `pkg_resources` problem below, but not the only one.
- **`pkg_resources` / `setuptools` version incompatibility**: Many older packages (e.g., `pysindy==1.7.5`, `hyperopt`, `louvain`, and any package that does `import pkg_resources` at runtime) will fail with `No module named 'pkg_resources'` if the installed `setuptools` is too new. `setuptools>=82.0` removed `pkg_resources` entirely (it had been deprecated since v67.5.0). **This can be triggered by**: (1) a pip install step (including DGL) that explicitly removes or upgrades setuptools; (2) the base image or a pip upgrade pulling setuptools≥82 where `pkg_resources` no longer exists. **Fix**: If any task package (Tier 1-4) does `import pkg_resources` at runtime, add `RUN python -m pip install --no-cache-dir setuptools==70.3.0` as the **final** `RUN pip install` line in the Dockerfile. Two critical details: (1) it must be the absolute last `RUN pip install` line — any subsequent pip install can upgrade it away; (2) pin to `setuptools==70.3.0` specifically — this is the last version verified to reliably provide `pkg_resources` as a standalone importable module in the v3 base.
- **PEP 517 isolated-build "setuptools was not found" anti-pattern** (verified in cases 881, 939): when an sdist-only package (e.g. `pybedtools==0.10.0`) fails its build step with `<package> uses setuptools ... but setuptools was not found`, the seemingly-obvious fix of `RUN pip install setuptools==70.3.0` *before* the failing install **does not work**. Modern pip builds wheels in an isolated virtualenv that does **not** inherit packages from the host environment — only the package's own `pyproject.toml [build-system] requires` list is installed there. A buggy sdist that depends on `setuptools` at build time but omits it from `requires` cannot be rescued from the host. Two correct fixes, in priority order: (1) **upgrade to a version that publishes a wheel** for cp311-linux (preferred — pip skips the build entirely); (2) **install with `--no-build-isolation`** plus pre-install of all build deps (`setuptools`, `wheel`, `cython`, `pysam`, etc.) on the host (fragile — every transitive build dep has to be enumerated). Never assume host pre-install fixes a build-isolation error.
- `leidenalg>=0.11.0` requires `igraph>=1.0.0`, which conflicts with `louvain==0.8.2` (requires `igraph<0.12`). Use `leidenalg==0.10.2` when both `leidenalg` and `louvain` are needed, or drop `louvain`.
- `dask>=2024.7` enables dask-expr backend by default, incompatible with `spatialdata<0.4` and `squidpy<1.7`. On `dask>=2024.12` (and certainly `dask>=2025`) the **legacy pandas-backed dataframe has been removed entirely** — the previously-documented `ENV DASK_DATAFRAME__QUERY_PLANNING=False` workaround is now obsolete and, on current dask, actively triggers `NotImplementedError: The legacy implementation is no longer supported` the moment anything imports `dask.dataframe`. Any module importing `dask.dataframe` then fails, which includes base `lightgbm` (whose `__init__` loads `lightgbm.dask`) and `squidpy<1.7` (via `spatialdata`). **Two-step fix**: (1) pin `dask<2024.7` (e.g. `dask==2024.6.2`) in the same RUN that installs `scanpy`/`squidpy`, and repin it in any later restore step; (2) add a final `RUN python -m pip uninstall -y dask-expr || true` — `dask-expr` is a **separate PyPI package** that some transitive dep in the scanpy/spatialdata/cellrank stack pulls in regardless of the dask version pin, and `dask.dataframe` auto-detects it at import time and switches its backend, after which `spatialdata` raises `RuntimeError: Unsupported backend: dask-expr has been detected`. Removing the package is the only reliable way to prevent autodetect. Do NOT rely on the env-var; remove it if present.
- **`squidpy` version matrix (v3 base + anndata 0.11)** — choosing the wrong squidpy version is a recurring source of failure (cases 503/855/926). The narrow workable version is `squidpy==1.6.5`:
  - `squidpy<=1.6.1`: imports `SparseCSCView`/`SparseCSRView` from `anndata._core.views` at module load. anndata 0.11 (base) renamed these to `SparseCSCMatrixView`/`SparseCSRMatrixView`, so `import squidpy` raises `ImportError: cannot import name 'SparseCSCView'`. Do **not** try to sed-patch `squidpy/gr/_utils.py` after install — earlier attempts that locate the file via `python -c "import squidpy.gr"` fail with the same ImportError (chicken-and-egg), and even with a static path the patch surface varies between minor versions.
  - `squidpy 1.6.2 – 1.6.4`: SparseCSCView issue fixed (upstream issue #928), but `Requires-Dist` pins `xarray<2024.10.0`, which conflicts with `multiscale-spatial-image>=2.0.2` and `spatialdata>=0.3.0` (both require `xarray>=2024.10.0`). Resolver backtracks for minutes and eventually fails.
  - **`squidpy==1.6.5`** (✅ default choice): keeps the SparseCSCView fix, switches to `xarray>=2024.10.0`, no `imagecodecs` pin. Compatible with `dask<=2024.11.2,>=2021.2`, `spatialdata>=0.2.5`, `statsmodels>=0.12`, `anndata>=0.9` — all satisfied by base+the dask pin above.
  - `squidpy==1.6.6`: adds a hard `imagecodecs<2026,>=2025.8.2` Requires-Dist. No `imagecodecs` wheel exists for cp311-linux in that range on PyPI, so pip aborts with `ResolutionImpossible: ... no matching distributions available for your environment: imagecodecs`. **Avoid.**
  - When pinning squidpy 1.6.5, also pin `xarray==2024.10.0` (the minimum that satisfies multiscale-spatial-image / spatialdata / squidpy 1.6.5 simultaneously) to prevent multi-minute resolver backtracking through dozens of xarray versions.
- `mujoco-py==2.1.x` requires MuJoCo 210 binary at `/root/.mujoco/mujoco210`. Must be downloaded in the Dockerfile (not just `pip install`). Also requires system packages: `libgl1-mesa-dev`, `libglew-dev`, `libosmesa6-dev`, `patchelf`. Additionally, `mujoco-py` JIT-compiles `cymj.pyx` on first import, which requires `Cython<3.0` — Cython 3.x enforces stricter `noexcept` semantics that break the compilation. If the task also needs Cython 3.x for other packages, install Cython 0.29.x first, install mujoco-py, trigger pre-compilation with `RUN python -c "import mujoco_py" 2>/dev/null || true`, then upgrade to Cython 3.x.
- `elmoformanylangs==0.0.4.post2`: TorchScript type annotations incompatible with `torch>=2.0`. No updated version available — apply Script-First Rule (replace ELMo usage with a transformers-based alternative or remove the dependency).
- `scvi-tools` may require `zarr` as a transitive dependency that is not auto-installed. Verify `zarr` is present after installing `scvi-tools`; add it explicitly if missing.
- **`numcodecs>=0.16` vs `zarr 2.18.x`**: `numcodecs==0.16.0` removed the public `cbuffer_sizes` symbol from `numcodecs.blosc` (it was private `_cbuffer_sizes` with a deprecation alias in 0.15.x, gone entirely in 0.16.x). `zarr==2.18.x` imports `cbuffer_sizes` at module load, so any package that imports zarr (anndata, scanpy, squidpy, scib) will fail with `ImportError: cannot import name 'cbuffer_sizes' from 'numcodecs.blosc'`. zarr's Requires-Dist only declares `numcodecs>=0.10,!=0.14.0,!=0.14.1` (no upper bound), so pip silently installs the latest numcodecs. **Fix**: pin `numcodecs==0.13.1` **before** `zarr`/`scanpy`/`squidpy`/`scib` in the same `pip install` step (0.13.x still exposes the public symbol; 0.14.x is excluded by zarr; 0.15.x moves it to private). This applies whenever you install `zarr==2.18.*` or any package that pulls it transitively.
- `vina==1.2.5`: builds from source and requires Boost C++ headers. The base image does not include Boost. Add `RUN apt-get update && apt-get install -y --no-install-recommends libboost-all-dev && rm -rf /var/lib/apt/lists/*` before `pip install vina`. (Note: `vina==1.2.7` has a `cp311-manylinux` wheel on PyPI — no Boost/apt needed, pip will use the wheel directly. Always check PyPI for a cp311 wheel before adding `-dev` system packages.)
- **`pybedtools` must be `>=0.12.0`** (verified in cases 881, 939). `pybedtools<=0.10.0` ships only an sdist; pip's PEP 517 isolated build environment cannot see the host `setuptools` and the build aborts with `pybedtools uses setuptools ... but setuptools was not found`. Pre-installing `setuptools` in the host (e.g. `RUN pip install setuptools==70.3.0` before `pip install pybedtools==0.10.0`) does **NOT** help — the isolated build env does not inherit host packages. The only reliable fixes are (a) bump to `pybedtools==0.12.0`, which publishes a proper `pyproject.toml` and a cp311-linux wheel so pip skips the sdist build entirely (preferred), or (b) install with `--no-build-isolation` and pre-install setuptools (fragile — also requires `cython`/`pysam` build deps). Always prefer (a).
- **QuickVina2 / `qvina` source build**: when building QuickVina2 from its GitHub archive (e.g., `QVina/qvina @ qvina2`) via `make`, the Makefile's `depend` target invokes `makedepend` — a legacy X11-era tool that is **not** provided by `libboost-all-dev` or any default Ubuntu package. Install `xutils-dev` alongside `libboost-all-dev` in the apt step; otherwise `make` fails with `/bin/sh: 1: makedepend: not found` and `Error 127` at the `depend` target. General lesson: when building any C/C++ source project via `make` from a GitHub archive, grep the Makefile for `makedepend` / `depend:` targets and add `xutils-dev` preemptively — the error surfaces only mid-build, wasting an entire apt + download cycle per iteration.
- `pennylane==0.41.0` pulls the latest `autoray` by default. `autoray>=0.8.0` replaced the `NumpyMimic` class with `AutoNamespace`, breaking pennylane's math module which inherits from `NumpyMimic` (`AttributeError: module 'autoray.autoray' has no attribute 'NumpyMimic'`). Fix: pin `autoray>=0.6.7,<0.8.0` when installing pennylane.
- `optuna==4.2.0` (base) has gRPC storage with auto-generated code that checks `grpcio>=1.68.1` at runtime. This is NOT declared in optuna's `Requires-Dist` — it's a runtime assertion in `api_pb2_grpc.py`. If the task Dockerfile explicitly installs `grpcio`, use version `>=1.68.1`. Pinning `grpcio==1.68.0` will break `import optuna`.
- `scikits.odes`: version 2.6.3 fails to build in the v3 base image environment — it relies on deprecated `numpy.distutils` which crashes with current setuptools (`TypeError: Compiler.__init__() takes from 1 to 3 positional arguments but 4 were given`). In the v3 base image, the workaround is to use `scikits.odes>=3.0`, which requires SUNDIALS 7.x headers (`sundials_context.h` from 6.x, `sundials_errors.h` from 7.x). Ubuntu 22.04 `libsundials-dev` only provides SUNDIALS 5.x, so SUNDIALS 7.1.1 must be built from source: `apt-get install cmake`, then `wget` + `cmake -DCMAKE_INSTALL_PREFIX=/usr/local -DBUILD_SHARED_LIBS=ON -DEXAMPLES_ENABLE_C=OFF`, `make install`, `ldconfig`, and set `ENV SUNDIALS_INST=/usr/local`.
- `neuraloperator==0.3.0`: the import name is `neuralop` (not `neuraloperator`). `torch-harmonics` is not declared as a hard dependency in its metadata, but `neuralop` imports it at runtime — import verification will fail with `No module named 'torch_harmonics'` unless it is explicitly installed. Add `torch-harmonics==0.6.5` (verified working version in v3 base) explicitly. Note: PyPI only has versions up to 0.3.0 — do not use non-existent versions like 2.0.0.
- `pytfa==0.9.4` has malformed metadata that `pip>=24.1` strictly rejects. The specific bad line lives in `setup.cfg` under `[options.extras_require]` — a bare `python_version>="3.6"` entry inside the `equilibrator` extras list (it is being parsed as a requirement name rather than an environment marker). **Do NOT** keep `pip<24.1` for the entire Dockerfile — old pip uses a legacy resolver that may accidentally downgrade base packages (e.g., `cobra==0.24.0` pulls `pandas<2.0`, breaking the base). **Also do NOT use `pip download --no-binary=:all:` followed by `rm setup.cfg`** — modern pip triggers metadata extraction during the download step itself, before you have a chance to patch the file. **Recommended fix**: fetch the source tarball directly with `wget` from PyPI (`https://files.pythonhosted.org/packages/source/p/pytfa/pytfa-0.9.4.tar.gz`), extract it, `sed -i '/python_version>=/d' setup.cfg` to remove the malformed line (or locate and fix the bad entry wherever it lives — `setup.py`, `setup.cfg`, `pyproject.toml`, or generated `PKG-INFO` — check the actual source), then `pip install --no-build-isolation <extracted-dir>`. This bypasses both the broken PyPI wheel and pip's eager metadata parsing. **Fallback hack (if the source fix is difficult)**: Temporarily downgrade to `pip<24.1` to install the package, **immediately patch the installed metadata** with `sed` on the `.dist-info/METADATA` file, and finally upgrade `pip` back. This prevents `pip>=24.1` from crashing when scanning the environment in subsequent installs.
- `cobra==0.24.0` requires `pandas~=1.0` (i.e., `<2.0`) and `pydantic~=1.6`, both incompatible with the base image (`pandas==2.2.3`, `pydantic==2.x`). Installing cobra 0.24.0 will downgrade pandas, breaking many base packages. Use `cobra>=0.29.0` which accepts `pandas<3.0,>=1.0` and `pydantic>=1.6` (no upper bound).
- `skimpy` (git install from EPFL-LCSB/skimpy): the pinned commit `04b14cb` has outdated dependency constraints in `setup.py`'s `install_requires` — **note the exact spelling**: `'cobra <= 0.24.0'` (with spaces around `<=`), `'scikits.odes==2.6.3'` (no spaces), `'markupsafe<=2.0.1'` (no spaces). A naive `sed "s/cobra<=0.24.0/.../g"` will SILENTLY FAIL to match the space-separated cobra line, and `pip install` will then downgrade cobra to `0.22.0` to satisfy the unmatched constraint. **That single silent downgrade cascades hard**: cobra 0.22.0 requires `pandas~=1.0` (forces `pandas==1.5.3`, breaking the base `pandas==2.2.3`) and `pydantic~=1.6` (forces `pydantic<2`, breaking `wandb`'s `computed_field` import). It also imports `from numpy import object` (removed in numpy 1.20), which cascades into `cobra`, `escher`, and `pytfa` all failing at import time with `ImportError: cannot import name 'object' from 'numpy'`. **Use whitespace-tolerant regex**: `sed -i -E "s/['\"]cobra *<= *0\.24\.0['\"]/'cobra>=0.24.0'/g" setup.py`. After each sed, `grep -n "cobra\\|scikits\\|markupsafe" setup.py` to verify the replacement actually landed before running `pip install`. After installation, patch deprecated numpy aliases (`np.float` → `np.float64`, `np.int` → `int`) in skimpy's installed source files. **General lesson**: when patching a setup.py/requirements file via `sed` before `pip install`, always `grep` the file after each substitution to confirm the pattern matched — pip resolves unmatched old constraints by downgrading, and downstream symptoms (numpy ImportError, pydantic breakage) hide the real cause.
- **Minimize external downloads during Docker build**: Every network request at build time (apt-get, wget, git clone, pip install from URL) is a fragile point — subject to mirror sync, link rot, timeouts, and rate limits. Prefer in this order:
  1. **Don't download**: use packages already in the base image, or pip packages with manylinux wheels on PyPI (pip has built-in retry and is the most reliable channel)
  2. **Before adding `apt-get install`**: check (a) whether the base image already includes the system package; (b) whether the target Python package has a pre-built wheel on PyPI — if so, the `-dev` header packages needed for source compilation are unnecessary
  3. **When download is unavoidable**: apply the robust patterns below (retry + fallback + validation)
- **General: `git clone` / `pip install git+` in Dockerfiles**: Direct GitHub cloning from Docker build environments frequently suffers from absolute timeouts (even with 3+ retries, it often remains completely blocked). **Preferred approach**: Always utilize a GitHub proxy mirror as the primary source, but **never rely on a single URL** — ghproxy.com is routinely rate-limited or blocked, and a single-URL wget will fail with `exit code 4` (network failure) when that happens. Use the same multi-source fallback pattern as External Binaries (below): loop over ghproxy → codeload → github direct, with `--tries` and `--timeout`, and validate the download with `test -s`.
  - *Archive Download (recommended)*:
    ```dockerfile
    RUN set -eux; \
      for url in \
        "https://mirror.ghproxy.com/https://github.com/<org>/<repo>/archive/<commit>.tar.gz" \
        "https://codeload.github.com/<org>/<repo>/tar.gz/<commit>" \
        "https://github.com/<org>/<repo>/archive/<commit>.tar.gz"; do \
        if wget -q --tries=3 --timeout=30 "$url" -O /tmp/repo.tar.gz; then break; fi; \
      done; \
      test -s /tmp/repo.tar.gz; \
      tar -xzf /tmp/repo.tar.gz -C /tmp; \
      python -m pip install --no-cache-dir /tmp/<repo>-<commit>
    ```
  - *Git+ Pip Install (only when archive+sed patching is not viable)*: `RUN python -m pip install git+https://mirror.ghproxy.com/https://github.com/<org>/<repo>.git@<commit>` — note that `pip install git+` cannot do the multi-URL fallback loop, so prefer the archive pattern above whenever possible (it is strictly more reliable).
  *Do NOT use `COPY` to bring host-downloaded files into the container, as the build context path is highly unpredictable in automated workflows.*
- **External Binaries**: Always download external binaries (e.g., `qvina02` for molecular docking) using `RUN wget` from a reliable URL inside the Dockerfile. **Avoid using `COPY`** — you cannot guarantee that the required binary files will physically exist in the Docker build context when the automated build executes. **Use multi-source fallback with validation**: single download URLs are fragile — provide at least one backup source, and verify the downloaded file exists and is non-empty before proceeding. Example pattern:
  ```dockerfile
  RUN wget -q https://primary-source.com/binary -O /usr/local/bin/binary \
      || wget -q https://backup-source.com/binary -O /usr/local/bin/binary \
      && test -s /usr/local/bin/binary \
      && chmod +x /usr/local/bin/binary
  ```
- **Robust `apt-get` in task Dockerfiles**: Ubuntu apt mirrors occasionally experience transient sync issues (`File has unexpected size`, `Mirror sync in progress?`), IPv6 routing problems, and upstream timeouts, causing `apt-get update` or `apt-get install` to fail non-deterministically during Docker builds. When a task Dockerfile needs system packages, use the canonical retry-tolerant pattern below (verified effective in production task builds — typically succeeds on first attempt):
  ```dockerfile
  RUN set -eux; \
    export DEBIAN_FRONTEND=noninteractive; \
    sed -i 's|http://archive.ubuntu.com/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ubuntu|g; s|http://security.ubuntu.com/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ubuntu|g' /etc/apt/sources.list; \
    echo 'Acquire::Retries "5"; Acquire::http::Timeout "20"; Acquire::https::Timeout "20"; Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99network-retries; \
    for attempt in 1 2 3 4; do \
      rm -rf /var/lib/apt/lists/*; \
      if apt-get update && apt-get install -y --no-install-recommends <packages> && rm -rf /var/lib/apt/lists/*; then \
        exit 0; \
      fi; \
      echo "apt attempt ${attempt} failed, retrying..."; \
      sleep $((attempt * 15)); \
    done; \
    exit 1
  ```
  Three reliability layers stack here: (1) switch Ubuntu sources to a fast mirror (Tsinghua), (2) apt-level retries + short timeouts + `ForceIPv4` (defeats broken IPv6 routes that commonly hang apt), (3) outer shell loop with exponential-ish backoff that clears `/var/lib/apt/lists/` between attempts (stale index files are a common sync-failure cause). **Note**: the base image uses its own NVIDIA CUDA apt sources — do not apply this mirror swap to the base image, only to task Dockerfiles layered on top.

If a compatible version exists → **add with that pinned version**.
If no compatible version exists → see "Handling Version Conflicts" below.

**④ Do scripts use APIs compatible with the installed library versions?**
When a package is already in base or being added with a specific version, check whether the scripts' API calls are compatible with that version:
- If `evaluation/evaluator.py` or other scripts use deprecated/removed APIs from an older version → **fix the script first** (see "Script-First Rule" below), then confirm the target version's API.
- This is especially important for: numpy (base is 1.26.4/numpy 1.x — `np.bool`, `np.int`, `np.float` etc. are deprecated but still work; however code written for numpy 2.x-only APIs may not work), pandas (2.x deprecations), scikit-learn (API changes), and domain libraries that evolve rapidly.

### Step 3: Generate Dockerfile

**Minimal case** (base image covers everything):

```dockerfile
FROM naturebench-base:v3
```

**With additional pip packages** (pin versions for reproducibility):

```dockerfile
FROM naturebench-base:v3

# Task-specific Python packages
RUN python -m pip install --no-cache-dir dgl==2.0.0 dgllife==0.3.2
```

**With system-level dependencies**:

```dockerfile
FROM naturebench-base:v3

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxxx-dev \
    && rm -rf /var/lib/apt/lists/*

# Task-specific Python packages
RUN python -m pip install --no-cache-dir some-package==X.Y.Z
```

**Version conflict** (task needs a specific version that conflicts with base):

```dockerfile
FROM naturebench-base:v3

# Override base image version (needed because task-package requires numpy>=2.0)
RUN python -m pip install --no-cache-dir numpy==2.1.3 task-package==X.Y.Z
```

**Standalone Dockerfile** (base image cannot support this task — see "When to Use a Standalone Dockerfile"):

```dockerfile
# Do NOT inherit from naturebench-base — base image cannot be reconciled with task requirements
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common build-essential cmake git wget curl \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update \
    && apt-get install -y --no-install-recommends python3.11 python3.11-dev python3.11-venv \
    && python3.11 -m venv /opt/py311 \
    && /opt/py311/bin/python -m pip install --upgrade pip setuptools wheel \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/py311
ENV PATH="/opt/py311/bin:${PATH}"

# Install all required packages from scratch
RUN python -m pip install --no-cache-dir \
    torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu118
RUN python -m pip install --no-cache-dir \
    numpy==1.26.4 scipy==1.14.1 pandas==2.2.3 \
    [... all other needed packages ...]
```

**Shell-precedence trap with `|| true` in pip RUN steps** (verified in case 503): never write `RUN pip install A B C && pip uninstall -y X || true` on a single line. The shell parses this as `(pip_install && pip_uninstall) || true` — if `pip install` fails (e.g. ResolutionImpossible), control jumps to `|| true`, the layer's exit code is 0, and the image **builds successfully with zero packages installed**. The bug then surfaces only at verify time as a flood of `ModuleNotFoundError` for every package in that line, with no build-log error to point at. **Rule**: `|| true` may only be applied to commands whose failure is intentionally ignorable (cleanup, optional uninstalls). Put any such command in its own RUN step, never chained behind `&&` after a primary install/build:
```dockerfile
# WRONG — install failure is silently swallowed
RUN pip install scanpy==1.10.4 squidpy==1.6.5 && pip uninstall -y dask-expr || true

# RIGHT — install must succeed; cleanup is isolated
RUN pip install scanpy==1.10.4 squidpy==1.6.5
RUN pip uninstall -y dask-expr || true
```

### Step 4: Generate packages.json

Generate `environment/packages.json` alongside the Dockerfile.v3. This file records every Python package the environment provides (both inherited from base and task-specific), with the information needed for automated import verification.

**Format**:

```json
{
  "from_base": true,
  "base_packages": [
    {"pip": "numpy", "import": "numpy", "version": "1.26.4"},
    {"pip": "scikit-learn", "import": "sklearn", "version": "1.6.1"}
  ],
  "task_packages": [
    {"pip": "tensorflow", "import": "tensorflow", "version": "2.19.0", "tier": 3},
    {"pip": "fcd-torch", "import": "fcd_torch", "version": "1.0.7", "tier": 1}
  ]
}
```

**Fields**:
- `from_base` (bool): `true` if the Dockerfile uses `FROM naturebench-base:v3`, `false` for standalone Dockerfiles
- `base_packages` (array): When `from_base` is `true`, copy the contents of [references/base_packages.json](base_packages.json) here. When `from_base` is `false`, this should be an empty array `[]`
- `task_packages` (array): Packages added by this task's Dockerfile (not in base). Each entry has:
  - `pip`: PyPI package name (as used in `pip install`)
  - `import`: Python import name (e.g., `sklearn` for `scikit-learn`, `cv2` for `opencv-python-headless`)
  - `version`: Pinned version string
  - `tier`: Dependency tier (1 = evaluator import, 2 = solver-side script import, 3 = paper core dependency, 4 = domain-common tool)

**Rules**:
- Every package in the Dockerfile's `pip install` lines must appear in `task_packages`
- The `import` field must be the actual top-level Python module name used in `import` statements — not the pip name
- For packages with multiple import names (e.g., `Pillow` → `PIL`), use the most common import name
- Packages installed via `--index-url` or `-f` flags are still listed normally

## Script-First Rule

**When generating the Dockerfile reveals a problem in an existing script, fix the script first — not the Dockerfile.**

This rule applies in two situations:

**Situation A: A hard-requirement package is unavailable on PyPI**
- The script imports a package that cannot be installed (deprecated, no Python 3.11 wheel, requires environment not compatible with Docker, etc.)
- Solution: modify `evaluation/evaluator.py` or the relevant script to remove the import and either:
  - Substitute with an available equivalent package that provides the same functionality
  - Re-implement the needed functionality directly in the script using available base packages
- Only after the script no longer needs the unavailable package should you finalize the Dockerfile

**Situation B: A script uses API incompatible with the available package version**
- The script calls functions/methods that have been removed or renamed in the version available for Python 3.11
- Solution: update the script's API calls to match the target version, then add the package to the Dockerfile
- Do NOT install an older version of the package just to avoid fixing the script — this destabilizes the entire environment
- Do NOT use `--no-deps` to bypass dependency resolution — this shifts the problem to runtime failures

Fixing scripts first maintains the correctness of the evaluator and ensures the environment is stable.

## Handling Version Conflicts

When a needed package conflicts with base packages:

1. **Find a compatible version**: Check if a newer (or different) version of the needed package resolves the conflict without changing base packages. This is the preferred approach.
2. **Override the conflicting base package**: If only one base package needs to be downgraded/upgraded, explicitly override it. Add a comment explaining why.
   ```dockerfile
   # Override: task-package requires numpy>=2.0 (incompatible with base numpy==1.26.4)
   RUN python -m pip install --no-cache-dir numpy==2.1.3 task-package==X.Y.Z
   ```
3. **Use a standalone Dockerfile**: Only when conflicts cannot be resolved by options 1 or 2 — i.e., the task's dependency environment is fundamentally incompatible with the base and cannot be reconciled by any combination of compatible versions or selective overrides.

> Never use `--no-deps` to bypass conflicts. It defers the conflict to runtime, making the environment silently broken.

## When to Use a Standalone Dockerfile

Use a standalone Dockerfile **only** when the base image genuinely cannot support the task after exhausting all other options:

1. **Different CUDA version required**: Task needs CUDA features not in 11.8 (e.g., packages that only publish CUDA 12.x/13.x wheels, Blackwell-era support, or legacy CUDA <11.8)
2. **Different Python version required**: Task requires Python 3.13+ features or a package with no Python 3.11 wheel
3. **Irreconcilable dependency conflicts**: The task's required packages cannot coexist with the base environment through any combination of compatible versions or selective overrides — **not merely "many" conflicts, but conflicts that have no resolution**

Do **NOT** use a standalone Dockerfile just because:
- The paper uses a different Python version (most code is version-flexible)
- The paper pins old package versions (usually unnecessary for optimization tasks)
- Multiple packages conflict (try to find compatible versions first)
- You are unsure about compatibility (try base first)

> When using a standalone Dockerfile, replicate the Python venv pattern from the base image (`/opt/py311` on PATH) for interface consistency.

## Guidelines

- **Solver-first environment**: This Docker image is primarily for the solver. The solver can only use packages that are installed. Omitting a needed dependency may make the task unsolvable.
- **Shared environment**: The Dockerfile defines a single environment for both solver and evaluator. Both sides' imports must be satisfied.
- **All four tiers matter**: Evaluator imports, solver-side script imports, paper core dependencies, and domain-common tools should all be included. Only omit a package when it genuinely cannot be installed (not just because it's "solver-side").
- **Script-First Rule**: If generating the Dockerfile reveals a script problem (unavailable package, API incompatibility), fix the script first.
- **Do not default to paper's exact versions**: Treat paper's pinned versions as compatibility hints only. Prefer base defaults and only pin specific versions when there is a concrete reason.
- **Pin task-specific packages**: Always specify `==X.Y.Z` for packages added to the task Dockerfile.
- **Keep it minimal**: Only add what base doesn't provide. Most task Dockerfiles should be 1-5 lines.
- **No data in the image**: Task data is mounted at runtime.
- **Python 3.11 only**: All packages must be installable for Python 3.11. Do not add packages that have no Python 3.11 support.
