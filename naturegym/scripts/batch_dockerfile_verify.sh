#!/bin/bash
# =============================================================================
# batch_dockerfile_verify.sh — Batch-build Dockerfiles and verify Python package loading
#
# Prerequisites:
#   Before running this script, the base image that the Dockerfiles under test
#   depend on must already be built or loaded into the local Docker environment
#   (check with docker images). Otherwise the subsequent `docker build` steps
#   will fail because the base image cannot be found.
# Usage:
#   bash batch_dockerfile_verify.sh [options] <target parent directory path>
#
# Options:
#   --single <case name>  Run only the specified single case
#   --start <range start> Start from the case at the given index (sorted alphabetically)
#   --end <range end>     Stop at the case at the given index
#   --dockerfile <name>   Specify the Dockerfile file name (default: Dockerfile.v3)
#   --require-gpu         Require the GPU/CUDA check to pass, otherwise mark as failed (and enable --gpus all)
#   --gpus <config>       GPU config for docker run (e.g. all / 1 / '"device=0"')
#   --cpus <count>        CPU limit for docker run (e.g. 4 / 2.5)
#   --memory <size>       Memory limit for docker run (e.g. 8g / 16384m)
#   --build-cpus <count>  CPU limit for docker build (e.g. 4 / 2.5)
#   --build-memory <size> Memory limit for docker build (e.g. 8g / 16384m)
#
# Examples:
#   1. Batch-verify the environment for all cases (default Dockerfile.v3):
#      bash batch_dockerfile_verify.sh /mnt/d/research/project/cns-agent/pass
#   2. Verify a single case only:
#      bash batch_dockerfile_verify.sh --single case_5 /mnt/d/research/project/cns-agent/pass
#   3. Verify a range (e.g. cases 11 through 20):
#      bash batch_dockerfile_verify.sh --start 11 --end 20 /mnt/d/research/project/cns-agent/pass
#   4. Use an older Dockerfile (v2 or the original):
#      bash batch_dockerfile_verify.sh --dockerfile Dockerfile.v2 /mnt/d/research/project/cns-agent/pass
#   5. Force GPU-availability verification:
#      bash batch_dockerfile_verify.sh --require-gpu /mnt/d/research/project/cns-agent/pass
#   6. Limit run resources:
#      bash batch_dockerfile_verify.sh --require-gpu --gpus '"device=0"' --cpus 4 --memory 16g /mnt/d/research/project/cns-agent/pass
#   7. Limit both build and run resources:
#      bash batch_dockerfile_verify.sh --build-cpus 4 --build-memory 8g --cpus 4 --memory 16g /mnt/d/research/project/cns-agent/pass
#
# Behavior:
#   1. Iterate over all subdirectories under <target parent directory path> (e.g. pass/case1, pass/case2)
#   2. Check that the subdirectory's environment/ contains the specified Dockerfile and packages.json
#   3. Extract all import fields (package import names) from packages.json
#   4. Build a temporary Docker image from that Dockerfile using an empty directory as context
#   5. Run Python inside the image to verify that the packages can be imported successfully
#      and additionally check torch/CUDA/NVML GPU information (optionally enforced)
#   6. Write a verify_result.txt test report under each case's environment/
#   7. Print a build-status summary to the terminal after all cases finish (no extra files written)
# =============================================================================

PASS_DIR=""
SINGLE_CASE=""
START_INDEX=""
END_INDEX=""
DOCKERFILE_NAME="Dockerfile.v3"
REQUIRE_GPU=0
GPU_SPEC=""
RUN_CPUS=""
RUN_MEMORY=""
BUILD_CPUS=""
BUILD_MEMORY=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERIFY_PY="$SCRIPT_DIR/docker_env_verify.py"

cpu_to_quota() {
    python - "$1" <<'PY'
import sys
value = float(sys.argv[1])
print(int(value * 100000))
PY
}

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --single) SINGLE_CASE="$2"; shift ;;
        --start) START_INDEX="$2"; shift ;;
        --end) END_INDEX="$2"; shift ;;
        --dockerfile) DOCKERFILE_NAME="$2"; shift ;;
        --require-gpu) REQUIRE_GPU=1 ;;
        --gpus) GPU_SPEC="$2"; shift ;;
        --cpus) RUN_CPUS="$2"; shift ;;
        --memory) RUN_MEMORY="$2"; shift ;;
        --build-cpus) BUILD_CPUS="$2"; shift ;;
        --build-memory) BUILD_MEMORY="$2"; shift ;;
        -*) echo "Unknown argument: $1"; exit 1 ;;
        *) PASS_DIR="$1" ;;
    esac
    shift
done

if [ -z "$PASS_DIR" ]; then
    echo "Error: missing required argument <target parent directory path>"
    echo "Usage: bash batch_verify.sh [options] <target parent directory path>"
    exit 1
fi

if [ ! -f "$VERIFY_PY" ]; then
    echo "Error: missing verification script -> $VERIFY_PY"
    exit 1
fi

case_dirs=()

if [ -n "$SINGLE_CASE" ]; then
    target_path="$PASS_DIR/$SINGLE_CASE/"
    if [ ! -d "$target_path" ]; then
        echo "Error: the specified case directory does not exist -> $target_path"
        exit 1
    fi
    case_dirs=("$target_path")
else
    # Find all subdirectories and sort by name
    mapfile -t all_dirs < <(find "$PASS_DIR" -mindepth 1 -maxdepth 1 -type d | sort)
    
    start=${START_INDEX:-1}
    end=${END_INDEX:-${#all_dirs[@]}}
    
    idx=0
    for d in "${all_dirs[@]}"; do
        idx=$((idx + 1))
        if [ "$idx" -ge "$start" ] && [ "$idx" -le "$end" ]; then
            case_dirs+=("$d/")
        fi
    done
fi

echo ">> Number of cases to process: ${#case_dirs[@]}"
if [ -n "$GPU_SPEC" ]; then
    echo ">> Run GPU config: $GPU_SPEC"
elif [ "$REQUIRE_GPU" -eq 1 ]; then
    echo ">> Run GPU config: all"
fi
if [ -n "$RUN_CPUS" ]; then
    echo ">> Run CPU limit: $RUN_CPUS"
fi
if [ -n "$RUN_MEMORY" ]; then
    echo ">> Run memory limit: $RUN_MEMORY"
fi
if [ -n "$BUILD_CPUS" ]; then
    echo ">> Build CPU limit: $BUILD_CPUS"
fi
if [ -n "$BUILD_MEMORY" ]; then
    echo ">> Build memory limit: $BUILD_MEMORY"
fi

# Summary statistics (printed to stdout only at the end, not written to a file)
SKIP_NO_DOCKERFILE=()
SKIP_NO_PACKAGES_JSON=()
SKIP_NO_IMPORTS=()
FAIL_BUILD=()
FAIL_VERIFY=()
FAIL_GPU=()
OK_COUNT=0

for case_dir in "${case_dirs[@]}"; do
    case_name=$(basename "$case_dir")
    dockerfile="$case_dir/environment/$DOCKERFILE_NAME"
    packages_json="$case_dir/environment/packages.json"
    result_file="$case_dir/environment/verify_result.txt"

    if [ ! -f "$dockerfile" ]; then
        echo "[$case_name] Skipped — no $DOCKERFILE_NAME"
        SKIP_NO_DOCKERFILE+=("$case_name")
        continue
    fi

    if [ ! -f "$packages_json" ]; then
        echo "[$case_name] Skipped — no packages.json"
        SKIP_NO_PACKAGES_JSON+=("$case_name")
        continue
    fi

    image_name="verify-${case_name}:latest"

    echo ""
    echo "========================================"
    echo "  Processing: $case_name"
    echo "========================================"

    # ── 1. Extract extra package info from packages.json (name / import / version) ──
    # Parse JSON with Python instead of jq to avoid a missing-command issue
    PYTHON_CMD="python"
    if command -v python3 >/dev/null 2>&1; then PYTHON_CMD="python3"; fi
    extra_imports_json=$(mktemp)
    parse_ok=1
    $PYTHON_CMD -c "
import json, sys
with open(sys.argv[1], encoding='utf-8') as f:
    data = json.load(f)
items = []
seen = set()
for key in ['base_packages', 'task_packages']:
    for pkg in data.get(key, []):
        if not isinstance(pkg, dict):
            continue
        import_name = pkg.get('import')
        if not isinstance(import_name, str):
            continue
        import_name = import_name.strip()
        dedupe_key = (key, import_name)
        if not import_name or dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        items.append({
            'name': pkg.get('name') or import_name,
            'pip': pkg.get('pip') or pkg.get('name') or import_name,
            'import': import_name,
            'version': pkg.get('version'),
            'expected_version': pkg.get('expected_version'),
            'specifier': pkg.get('specifier'),
            'constraint': pkg.get('constraint'),
            'source': key,
        })
json.dump(items, sys.stdout)
" "$packages_json" > "$extra_imports_json" || parse_ok=0

    if [ "$parse_ok" -ne 1 ]; then
        echo ">> Failed to parse packages.json, skipping"
        rm -f "$extra_imports_json"
        SKIP_NO_IMPORTS+=("$case_name")
        continue
    fi

    # ── 2. Build the image ──
    echo ">> Building image..."
    # Use an empty temporary directory as the build context to avoid permission issues
    build_ctx=$(mktemp -d)
    build_cmd=(docker build --no-cache -t "$image_name" -f "$dockerfile")
    if [ -n "$BUILD_MEMORY" ]; then
        build_cmd+=(--memory "$BUILD_MEMORY")
    fi
    if [ -n "$BUILD_CPUS" ]; then
        build_cmd+=(--cpu-period 100000 --cpu-quota "$(cpu_to_quota "$BUILD_CPUS")")
    fi
    build_cmd+=("$build_ctx")
    build_output=$("${build_cmd[@]}" 2>&1)
    build_exit=$?
    rm -rf "$build_ctx"

    if [ $build_exit -ne 0 ]; then
        echo ">> Build failed!"
        {
            echo "case: $case_name"
            echo "dockerfile: $DOCKERFILE_NAME"
            echo "time: $(date -Iseconds)"
            echo "status: build failed"
            echo ""
            echo "build error:"
            echo "$build_output"
        } > "$result_file"
        rm -f "$extra_imports_json"
        FAIL_BUILD+=("$case_name")
        continue
    fi
    echo ">> Build succeeded"

    # ── 4. Run verification ──
    echo ">> Verifying base.v3 base environment and case imports..."
    run_cmd=(docker run --rm -v "$VERIFY_PY:/workspace/docker_env_verify.py:ro" -v "$extra_imports_json:/workspace/extra_imports.json:ro")
    if [ -n "$GPU_SPEC" ]; then
        run_cmd+=(--gpus "$GPU_SPEC")
    elif [ "$REQUIRE_GPU" -eq 1 ]; then
        run_cmd+=(--gpus all)
    fi
    if [ -n "$RUN_CPUS" ]; then
        run_cmd+=(--cpus "$RUN_CPUS")
    fi
    if [ -n "$RUN_MEMORY" ]; then
        run_cmd+=(--memory "$RUN_MEMORY")
    fi
    verify_args=(python /workspace/docker_env_verify.py --extra-imports-json /workspace/extra_imports.json)
    if [ "$REQUIRE_GPU" -eq 1 ]; then
        verify_args+=(--require-gpu)
    fi
    verify_output=$("${run_cmd[@]}" "$image_name" "${verify_args[@]}" 2>&1)
    verify_exit=$?
    rm -f "$extra_imports_json"

    # ── 5. Write the result file ──
    {
        echo "case: $case_name"
        echo "dockerfile: $DOCKERFILE_NAME"
        echo "time: $(date -Iseconds)"
        if [ $verify_exit -eq 0 ]; then
            echo "status: all passed"
        elif [ $verify_exit -eq 2 ]; then
            echo "status: GPU check failed"
        else
            echo "status: has failures"
        fi
        echo ""
        echo "$verify_output"
    } > "$result_file"

    echo ">> Result saved to: $result_file"

    if [ $verify_exit -eq 0 ]; then
        OK_COUNT=$((OK_COUNT + 1))
    elif [ $verify_exit -eq 2 ]; then
        FAIL_GPU+=("$case_name")
    else
        FAIL_VERIFY+=("$case_name")
    fi

    # ── 6. Clean up the image ──
    docker rmi "$image_name" > /dev/null 2>&1

done

echo ""
echo "========================================"
echo "  All done"
echo "========================================"
echo ""
echo "========== Build status summary (terminal output only) =========="
echo "Cases planned for processing: ${#case_dirs[@]}"
echo ""
echo "Skipped — no $DOCKERFILE_NAME: ${#SKIP_NO_DOCKERFILE[@]}"
if [ "${#SKIP_NO_DOCKERFILE[@]}" -gt 0 ]; then
    for n in "${SKIP_NO_DOCKERFILE[@]}"; do echo "  - $n"; done
fi
echo ""
echo "Skipped — no packages.json: ${#SKIP_NO_PACKAGES_JSON[@]}"
if [ "${#SKIP_NO_PACKAGES_JSON[@]}" -gt 0 ]; then
    for n in "${SKIP_NO_PACKAGES_JSON[@]}"; do echo "  - $n"; done
fi
echo ""
echo "Skipped — packages.json parse failed / no usable import: ${#SKIP_NO_IMPORTS[@]}"
if [ "${#SKIP_NO_IMPORTS[@]}" -gt 0 ]; then
    for n in "${SKIP_NO_IMPORTS[@]}"; do echo "  - $n"; done
fi
echo ""
echo "Build failed: ${#FAIL_BUILD[@]}"
if [ "${#FAIL_BUILD[@]}" -gt 0 ]; then
    for n in "${FAIL_BUILD[@]}"; do echo "  - $n"; done
fi
echo ""
echo "Build succeeded but environment verification failed: ${#FAIL_VERIFY[@]}"
if [ "${#FAIL_VERIFY[@]}" -gt 0 ]; then
    for n in "${FAIL_VERIFY[@]}"; do echo "  - $n"; done
fi
echo ""
echo "Build succeeded but GPU check failed: ${#FAIL_GPU[@]}"
if [ "${#FAIL_GPU[@]}" -gt 0 ]; then
    for n in "${FAIL_GPU[@]}"; do echo "  - $n"; done
fi
echo ""
echo "Build and environment verification all passed: $OK_COUNT"
echo "=============================================="
