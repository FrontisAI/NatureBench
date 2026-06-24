#!/usr/bin/env python3
"""
inspect_data.py - Data file inspection utility for the data-check skill.

Detects file formats, reads metadata (shape, keys, columns, sample count),
and verifies file integrity. Outputs JSON for programmatic consumption.

Usage:
    python inspect_data.py inspect <file_path>
    python inspect_data.py inspect-dir <directory_path> [--recursive]
    python inspect_data.py verify-archive <archive_path>

Supported formats:
    h5/hdf5, csv/tsv, npy/npz, pkl/pickle, json/jsonl, parquet,
    fasta/fastq, pdb, sdf/mol2, pt/pth (readability only)
"""

import argparse
import json
import os
import pickle
import subprocess
import sys
from pathlib import Path


def detect_format(file_path: str) -> str:
    """Detect file format by extension and magic bytes."""
    ext = Path(file_path).suffix.lower()
    # Also check double extensions like .tar.gz
    name_lower = Path(file_path).name.lower()

    ext_map = {
        ".h5": "h5",
        ".hdf5": "h5",
        ".hdf": "h5",
        ".he5": "h5",
        ".csv": "csv",
        ".tsv": "tsv",
        ".npy": "npy",
        ".npz": "npz",
        ".pkl": "pkl",
        ".pickle": "pkl",
        ".json": "json",
        ".jsonl": "jsonl",
        ".parquet": "parquet",
        ".pq": "parquet",
        ".fasta": "fasta",
        ".fa": "fasta",
        ".fna": "fasta",
        ".faa": "fasta",
        ".fastq": "fastq",
        ".fq": "fastq",
        ".pdb": "pdb",
        ".sdf": "sdf",
        ".mol2": "mol2",
        ".pt": "pt",
        ".pth": "pt",
        ".tar.gz": "tar.gz",
        ".tgz": "tar.gz",
        ".tar.bz2": "tar.bz2",
        ".tar.xz": "tar.xz",
        ".zip": "zip",
        ".gz": "gz",
        ".bz2": "bz2",
        ".7z": "7z",
        ".txt": "txt",
        ".md": "txt",
        ".h5ad": "h5",
        ".loom": "h5",
        ".nii": "nii",
        ".nii.gz": "nii.gz",
        ".tif": "tiff",
        ".tiff": "tiff",
        ".mat": "mat",
        ".rds": "rds",
        ".rdata": "rds",
    }

    # Check double extensions first
    for double_ext in [".tar.gz", ".tar.bz2", ".tar.xz", ".nii.gz"]:
        if name_lower.endswith(double_ext):
            return ext_map[double_ext]

    if ext in ext_map:
        return ext_map[ext]

    # Try magic bytes for common formats
    try:
        with open(file_path, "rb") as f:
            header = f.read(16)
            if header[:4] == b"\x89HDF":
                return "h5"
            if header[:6] == b"\x93NUMPY":
                return "npy"
            if header[:2] == b"PK":
                # Could be zip or npz
                if ext == ".npz":
                    return "npz"
                return "zip"
            if header[:4] == b"PAR1":
                return "parquet"
            if header[:2] == b"\x1f\x8b":
                return "gz"
            if header[:3] == b"BZh":
                return "bz2"
    except (OSError, IOError):
        pass

    return "unknown"


def inspect_h5(file_path: str) -> dict:
    """Inspect HDF5 file."""
    try:
        import h5py
    except ImportError:
        return {"readable": False, "error": "h5py not installed", "metadata": None}

    try:
        with h5py.File(file_path, "r") as f:
            keys = list(f.keys())
            metadata = {"keys": keys}

            # Get shapes for top-level datasets
            shapes = {}
            dtypes = {}
            for key in keys:
                item = f[key]
                if hasattr(item, "shape"):
                    shapes[key] = list(item.shape)
                    dtypes[key] = str(item.dtype)
                elif hasattr(item, "keys"):
                    # It's a group - list its keys
                    shapes[key] = f"group({len(item.keys())} items)"

            if shapes:
                metadata["shapes"] = shapes
            if dtypes:
                metadata["dtypes"] = dtypes

            # Estimate sample count from first dataset with a shape
            for key in keys:
                item = f[key]
                if hasattr(item, "shape") and len(item.shape) > 0:
                    metadata["sample_count"] = item.shape[0]
                    break

        return {"readable": True, "error": None, "metadata": metadata}
    except Exception as e:
        return {"readable": False, "error": str(e), "metadata": None}


def inspect_csv(file_path: str, sep: str = ",") -> dict:
    """Inspect CSV/TSV file."""
    import csv
    try:
        import pandas as pd
    except ImportError:
        # Fallback: basic line counting
        try:
            with open(file_path, "r", errors="replace", newline="") as f:
                reader = csv.reader(f, delimiter=sep)
                header = next(reader, [])
                line_count = sum(1 for _ in reader)
            return {
                "readable": True,
                "error": None,
                "metadata": {
                    "columns": header,
                    "num_columns": len(header),
                    "sample_count": line_count,
                },
            }
        except Exception as e:
            return {"readable": False, "error": str(e), "metadata": None}

    try:
        # Read only first few rows to get structure, then count lines
        df_head = pd.read_csv(file_path, sep=sep, nrows=5)
        columns = list(df_head.columns)
        dtypes = {col: str(dtype) for col, dtype in df_head.dtypes.items()}

        # Count total rows efficiently handling newlines correctly
        with open(file_path, "r", errors="replace", newline="") as f:
            reader = csv.reader(f, delimiter=sep)
            next(reader, None)  # skip header
            total_lines = sum(1 for _ in reader)

        metadata = {
            "columns": columns,
            "num_columns": len(columns),
            "dtypes": dtypes,
            "sample_count": total_lines,
            "shape": [total_lines, len(columns)],
        }
        return {"readable": True, "error": None, "metadata": metadata}
    except Exception as e:
        return {"readable": False, "error": str(e), "metadata": None}


def inspect_npy(file_path: str) -> dict:
    """Inspect numpy .npy file."""
    try:
        import numpy as np
    except ImportError:
        return {"readable": False, "error": "numpy not installed", "metadata": None}

    try:
        arr = np.load(file_path, mmap_mode="r")
        metadata = {
            "shape": list(arr.shape),
            "dtype": str(arr.dtype),
            "sample_count": arr.shape[0] if len(arr.shape) > 0 else 1,
        }
        return {"readable": True, "error": None, "metadata": metadata}
    except Exception as e:
        return {"readable": False, "error": str(e), "metadata": None}


def inspect_npz(file_path: str) -> dict:
    """Inspect numpy .npz file."""
    try:
        import numpy as np
    except ImportError:
        return {"readable": False, "error": "numpy not installed", "metadata": None}

    try:
        with np.load(file_path, allow_pickle=False) as data:
            keys = list(data.keys())
            shapes = {}
            dtypes = {}
            for key in keys:
                arr = data[key]
                shapes[key] = list(arr.shape)
                dtypes[key] = str(arr.dtype)

            metadata = {"keys": keys, "shapes": shapes, "dtypes": dtypes}

            # Sample count from first array
            for key in keys:
                if len(shapes[key]) > 0:
                    metadata["sample_count"] = shapes[key][0]
                    break

        return {"readable": True, "error": None, "metadata": metadata}
    except Exception as e:
        # Retry with allow_pickle=True for pickle-containing npz
        try:
            import numpy as np

            with np.load(file_path, allow_pickle=True) as data:
                keys = list(data.keys())
                metadata = {"keys": keys, "note": "contains pickled objects"}
                shapes = {}
                for key in keys:
                    obj = data[key]
                    if hasattr(obj, "shape"):
                        shapes[key] = list(obj.shape)
                if shapes:
                    metadata["shapes"] = shapes
            return {"readable": True, "error": None, "metadata": metadata}
        except Exception as e2:
            return {"readable": False, "error": str(e2), "metadata": None}


def _read_pickle_protocol(file_path: str) -> int | None:
    """Read pickle protocol version from file header."""
    try:
        with open(file_path, "rb") as f:
            first_byte = f.read(2)
            if len(first_byte) >= 2 and first_byte[0:1] == b"\x80":
                return first_byte[1]
            # Protocol 0 (ASCII) or 1 (binary) don't have the \x80 prefix
            return 0
    except Exception:
        return None


def _extract_pkl_metadata(obj: object) -> dict:
    """Extract metadata from a deserialized pickle object."""
    metadata = {"type": type(obj).__name__}
    if hasattr(obj, "shape"):
        metadata["shape"] = list(obj.shape)
        if len(obj.shape) > 0:
            metadata["sample_count"] = obj.shape[0]
    elif isinstance(obj, (list, tuple)):
        metadata["length"] = len(obj)
        metadata["sample_count"] = len(obj)
    elif isinstance(obj, dict):
        metadata["keys"] = list(obj.keys())[:50]
        metadata["num_keys"] = len(obj)
    elif hasattr(obj, "__len__"):
        metadata["length"] = len(obj)
    return metadata


class _LenientUnpickler(pickle.Unpickler):
    """Unpickler that substitutes placeholder for missing modules."""

    def find_class(self, module, name):
        try:
            return super().find_class(module, name)
        except (ModuleNotFoundError, AttributeError):
            # Return a placeholder so deserialization can continue
            return type(f"{module}.{name}", (), {})


def inspect_pkl(file_path: str) -> dict:
    """Inspect pickle file with layered fallback for compatibility."""
    protocol = _read_pickle_protocol(file_path)

    # Layer 1: normal load
    try:
        with open(file_path, "rb") as f:
            obj = pickle.load(f)
        metadata = _extract_pkl_metadata(obj)
        if protocol is not None:
            metadata["protocol"] = protocol
        return {"readable": True, "error": None, "metadata": metadata}
    except Exception:
        pass

    # Layer 2: Python 2 encoding fallback
    try:
        with open(file_path, "rb") as f:
            obj = pickle.load(f, encoding="latin1")
        metadata = _extract_pkl_metadata(obj)
        metadata["note"] = "loaded with encoding='latin1' (Python 2 pickle)"
        if protocol is not None:
            metadata["protocol"] = protocol
        return {"readable": True, "error": None, "metadata": metadata}
    except Exception:
        pass

    # Layer 3: lenient unpickler for missing modules
    try:
        with open(file_path, "rb") as f:
            obj = _LenientUnpickler(f, encoding="latin1").load()
        metadata = _extract_pkl_metadata(obj)
        metadata["note"] = "loaded with lenient unpickler (some classes substituted)"
        if protocol is not None:
            metadata["protocol"] = protocol
        return {"readable": True, "error": None, "metadata": metadata}
    except Exception as e:
        metadata = {}
        if protocol is not None:
            metadata["protocol"] = protocol
        return {
            "readable": False,
            "error": str(e),
            "metadata": metadata or None,
        }


def inspect_json(file_path: str) -> dict:
    """Inspect JSON file."""
    try:
        with open(file_path, "r", errors="replace") as f:
            data = json.load(f)

        metadata = {"type": type(data).__name__}

        if isinstance(data, list):
            metadata["sample_count"] = len(data)
            if len(data) > 0:
                metadata["first_item_type"] = type(data[0]).__name__
                if isinstance(data[0], dict):
                    metadata["first_item_keys"] = list(data[0].keys())
        elif isinstance(data, dict):
            metadata["keys"] = list(data.keys())[:50]
            metadata["num_keys"] = len(data)

        return {"readable": True, "error": None, "metadata": metadata}
    except Exception as e:
        return {"readable": False, "error": str(e), "metadata": None}


def inspect_jsonl(file_path: str) -> dict:
    """Inspect JSONL file."""
    try:
        count = 0
        first_item = None
        with open(file_path, "r", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line:
                    if first_item is None:
                        first_item = json.loads(line)
                    count += 1

        metadata = {"sample_count": count}
        if first_item is not None:
            metadata["first_item_type"] = type(first_item).__name__
            if isinstance(first_item, dict):
                metadata["first_item_keys"] = list(first_item.keys())

        return {"readable": True, "error": None, "metadata": metadata}
    except Exception as e:
        return {"readable": False, "error": str(e), "metadata": None}


def inspect_parquet(file_path: str) -> dict:
    """Inspect Parquet file."""
    try:
        import pandas as pd
    except ImportError:
        return {"readable": False, "error": "pandas not installed", "metadata": None}

    try:
        # Read just metadata first
        import pyarrow.parquet as pq

        pf = pq.ParquetFile(file_path)
        metadata = {
            "num_rows": pf.metadata.num_rows,
            "num_columns": pf.metadata.num_columns,
            "sample_count": pf.metadata.num_rows,
            "columns": [pf.schema.field(i).name for i in range(pf.schema_arrow.__len__())],
            "shape": [pf.metadata.num_rows, pf.metadata.num_columns],
        }
        return {"readable": True, "error": None, "metadata": metadata}
    except ImportError:
        # Fallback to pandas
        try:
            df = pd.read_parquet(file_path)
            metadata = {
                "shape": list(df.shape),
                "columns": list(df.columns),
                "sample_count": df.shape[0],
            }
            return {"readable": True, "error": None, "metadata": metadata}
        except Exception as e:
            return {"readable": False, "error": str(e), "metadata": None}
    except Exception as e:
        return {"readable": False, "error": str(e), "metadata": None}


def inspect_fasta(file_path: str) -> dict:
    """Inspect FASTA file."""
    try:
        seq_count = 0
        with open(file_path, "r", errors="replace") as f:
            for line in f:
                if line.startswith(">"):
                    seq_count += 1

        metadata = {"sample_count": seq_count, "sequence_count": seq_count}
        return {"readable": True, "error": None, "metadata": metadata}
    except Exception as e:
        return {"readable": False, "error": str(e), "metadata": None}


def inspect_fastq(file_path: str) -> dict:
    """Inspect FASTQ file."""
    try:
        line_count = 0
        with open(file_path, "r", errors="replace") as f:
            for _ in f:
                line_count += 1

        seq_count = line_count // 4  # FASTQ has 4 lines per record
        metadata = {"sample_count": seq_count, "sequence_count": seq_count}
        return {"readable": True, "error": None, "metadata": metadata}
    except Exception as e:
        return {"readable": False, "error": str(e), "metadata": None}


def inspect_pdb(file_path: str) -> dict:
    """Inspect PDB file."""
    try:
        atom_count = 0
        hetatm_count = 0
        model_count = 0
        chains = set()
        with open(file_path, "r", errors="replace") as f:
            for line in f:
                if line.startswith("ATOM"):
                    atom_count += 1
                    if len(line) > 21:
                        chains.add(line[21])
                elif line.startswith("HETATM"):
                    hetatm_count += 1
                elif line.startswith("MODEL"):
                    model_count += 1

        metadata = {
            "atom_count": atom_count,
            "hetatm_count": hetatm_count,
            "model_count": max(model_count, 1),
            "chains": sorted(chains),
            "sample_count": max(model_count, 1),
        }
        return {"readable": True, "error": None, "metadata": metadata}
    except Exception as e:
        return {"readable": False, "error": str(e), "metadata": None}


def inspect_sdf(file_path: str) -> dict:
    """Inspect SDF file."""
    try:
        mol_count = 0
        with open(file_path, "r", errors="replace") as f:
            for line in f:
                if line.strip() == "$$$$":
                    mol_count += 1

        metadata = {"molecule_count": mol_count, "sample_count": mol_count}
        return {"readable": True, "error": None, "metadata": metadata}
    except Exception as e:
        return {"readable": False, "error": str(e), "metadata": None}


def inspect_mol2(file_path: str) -> dict:
    """Inspect MOL2 file."""
    try:
        mol_count = 0
        with open(file_path, "r", errors="replace") as f:
            for line in f:
                if line.strip().startswith("@<TRIPOS>MOLECULE"):
                    mol_count += 1

        metadata = {"molecule_count": mol_count, "sample_count": mol_count}
        return {"readable": True, "error": None, "metadata": metadata}
    except Exception as e:
        return {"readable": False, "error": str(e), "metadata": None}


def inspect_pt(file_path: str) -> dict:
    """Inspect PyTorch file (readability check only)."""
    try:
        import torch
    except ImportError:
        return {"readable": False, "error": "torch not installed", "metadata": None}

    try:
        # Only check readability, do not fully load large models
        obj = torch.load(file_path, map_location="cpu", weights_only=True)

        metadata = {"type": type(obj).__name__}
        if isinstance(obj, dict):
            metadata["keys"] = list(obj.keys())[:50]
            metadata["num_keys"] = len(obj)
        elif hasattr(obj, "shape"):
            metadata["shape"] = list(obj.shape)

        return {"readable": True, "error": None, "metadata": metadata}
    except Exception:
        # Retry with weights_only=False for non-weight files
        try:
            obj = torch.load(file_path, map_location="cpu", weights_only=False)
            metadata = {"type": type(obj).__name__, "note": "loaded with weights_only=False"}
            if isinstance(obj, dict):
                metadata["keys"] = list(obj.keys())[:50]
                metadata["num_keys"] = len(obj)
            elif hasattr(obj, "shape"):
                metadata["shape"] = list(obj.shape)
            return {"readable": True, "error": None, "metadata": metadata}
        except Exception as e:
            return {"readable": False, "error": str(e), "metadata": None}


def inspect_mat(file_path: str) -> dict:
    """Inspect MATLAB .mat file."""
    try:
        import scipy.io
        mat = scipy.io.whosmat(file_path)
        metadata = {"keys": [m[0] for m in mat]}
        return {"readable": True, "error": None, "metadata": metadata}
    except ImportError:
        # Might be v7.3 which uses HDF5
        return inspect_h5(file_path)
    except Exception as e:
        # Try HDF5 fallback for v7.3 as well
        h5_res = inspect_h5(file_path)
        if h5_res.get("readable"):
            return h5_res
        return {"readable": False, "error": str(e), "metadata": None}


def inspect_nii(file_path: str) -> dict:
    """Inspect NIfTI file."""
    try:
        import nibabel as nib
        img = nib.load(file_path)
        metadata = {"shape": list(img.shape)}
        return {"readable": True, "error": None, "metadata": metadata}
    except Exception as e:
        err = str(e) if "No module" not in str(e) else "nibabel not installed"
        return {"readable": False, "error": err, "metadata": None}


def inspect_tiff(file_path: str) -> dict:
    """Inspect TIFF file."""
    try:
        import tifffile
        with tifffile.TiffFile(file_path) as tif:
            metadata = {"num_pages": len(tif.pages)}
        return {"readable": True, "error": None, "metadata": metadata}
    except Exception as e:
        err = str(e) if "No module" not in str(e) else "tifffile not installed"
        return {"readable": False, "error": err, "metadata": None}


def inspect_rds(file_path: str) -> dict:
    """Inspect R data file."""
    return {"readable": False, "error": "R data format requires R environment", "metadata": None}


def verify_archive(file_path: str) -> dict:
    """Verify archive integrity."""
    fmt = detect_format(file_path)
    result = {
        "file_path": file_path,
        "format": fmt,
        "size_bytes": os.path.getsize(file_path),
    }

    commands = {
        "tar.gz": ["tar", "-tzf", file_path],
        "tar.bz2": ["tar", "-tjf", file_path],
        "tar.xz": ["tar", "-tJf", file_path],
        "zip": ["unzip", "-t", file_path],
        "gz": ["gzip", "-t", file_path],
        "bz2": ["bzip2", "-t", file_path],
        "7z": ["7z", "t", file_path],
    }

    if fmt not in commands:
        result["integrity"] = "not_checked"
        result["error"] = f"Unsupported archive format: {fmt}"
        return result

    try:
        proc = subprocess.run(
            commands[fmt],
            capture_output=True,
            text=True,
            timeout=7200,
        )
        if proc.returncode == 0:
            result["integrity"] = "valid"
            result["error"] = None
        else:
            result["integrity"] = "corrupted"
            result["error"] = proc.stderr.strip()[:500]
    except subprocess.TimeoutExpired:
        result["integrity"] = "not_checked"
        result["error"] = "Verification timed out (>7200s)"
    except FileNotFoundError as e:
        result["integrity"] = "not_checked"
        result["error"] = f"Command not found: {e}"
    except Exception as e:
        result["integrity"] = "not_checked"
        result["error"] = str(e)

    return result


def inspect_file(file_path: str) -> dict:
    """Inspect a single file and return metadata."""
    file_path = os.path.abspath(file_path)

    if not os.path.exists(file_path):
        return {
            "file_path": file_path,
            "exists": False,
            "format": "unknown",
            "size_bytes": 0,
            "readable": False,
            "error": "File does not exist",
            "metadata": None,
        }

    size = os.path.getsize(file_path)
    fmt = detect_format(file_path)

    result = {
        "file_path": file_path,
        "exists": True,
        "format": fmt,
        "size_bytes": size,
    }

    if size == 0:
        result["readable"] = False
        result["error"] = "File is empty"
        result["metadata"] = None
        return result

    # Archive formats: verify integrity instead of reading content
    archive_formats = {"tar.gz", "tar.bz2", "tar.xz", "zip", "gz", "bz2", "7z"}
    if fmt in archive_formats:
        archive_result = verify_archive(file_path)
        result["readable"] = archive_result["integrity"] == "valid"
        result["integrity"] = archive_result["integrity"]
        result["error"] = archive_result.get("error")
        result["metadata"] = None
        return result

    # Content formats: read and extract metadata
    inspectors = {
        "h5": inspect_h5,
        "csv": lambda p: inspect_csv(p, sep=","),
        "tsv": lambda p: inspect_csv(p, sep="\t"),
        "npy": inspect_npy,
        "npz": inspect_npz,
        "pkl": inspect_pkl,
        "json": inspect_json,
        "jsonl": inspect_jsonl,
        "parquet": inspect_parquet,
        "fasta": inspect_fasta,
        "fastq": inspect_fastq,
        "pdb": inspect_pdb,
        "sdf": inspect_sdf,
        "mol2": inspect_mol2,
        "pt": inspect_pt,
        "mat": inspect_mat,
        "nii": inspect_nii,
        "nii.gz": inspect_nii,
        "tiff": inspect_tiff,
        "rds": inspect_rds,
    }

    if fmt in inspectors:
        inspection = inspectors[fmt](file_path)
        result.update(inspection)
    else:
        result["readable"] = False
        result["error"] = f"Unsupported format: {fmt}"
        result["metadata"] = None

    return result


def inspect_directory(dir_path: str, recursive: bool = True) -> list:
    """Inspect all data files in a directory."""
    results = []
    dir_path = os.path.abspath(dir_path)

    # File extensions to inspect
    data_extensions = {
        ".h5", ".hdf5", ".hdf", ".he5",
        ".csv", ".tsv",
        ".npy", ".npz",
        ".pkl", ".pickle",
        ".json", ".jsonl",
        ".parquet", ".pq",
        ".fasta", ".fa", ".fna", ".faa",
        ".fastq", ".fq",
        ".pdb",
        ".sdf", ".mol2",
        ".pt", ".pth",
        ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz",
        ".zip", ".gz", ".bz2", ".7z",
        ".h5ad", ".loom", ".nii", ".nii.gz",
        ".tif", ".tiff", ".mat", ".rds", ".rdata",
    }

    if recursive:
        for root, dirs, files in os.walk(dir_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in sorted(files):
                if any(fname.lower().endswith(ext) for ext in data_extensions):
                    fpath = os.path.join(root, fname)
                    results.append(inspect_file(fpath))
    else:
        for fname in sorted(os.listdir(dir_path)):
            fpath = os.path.join(dir_path, fname)
            if os.path.isfile(fpath) and any(fname.lower().endswith(ext) for ext in data_extensions):
                results.append(inspect_file(fpath))

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Inspect data files for format, readability, and metadata."
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # inspect command
    inspect_parser = subparsers.add_parser("inspect", help="Inspect a single file")
    inspect_parser.add_argument("file_path", help="Path to the file to inspect")

    # inspect-dir command
    dir_parser = subparsers.add_parser("inspect-dir", help="Inspect all data files in a directory")
    dir_parser.add_argument("directory_path", help="Path to the directory")
    dir_parser.add_argument(
        "--recursive", action="store_true", default=True,
        help="Recursively inspect subdirectories (default: True)"
    )
    dir_parser.add_argument(
        "--no-recursive", action="store_false", dest="recursive",
        help="Only inspect files in the top-level directory"
    )

    # verify-archive command
    archive_parser = subparsers.add_parser("verify-archive", help="Verify archive integrity")
    archive_parser.add_argument("archive_path", help="Path to the archive file")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "inspect":
        result = inspect_file(args.file_path)
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "inspect-dir":
        results = inspect_directory(args.directory_path, recursive=args.recursive)
        print(json.dumps(results, indent=2, default=str))

    elif args.command == "verify-archive":
        result = verify_archive(args.archive_path)
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
