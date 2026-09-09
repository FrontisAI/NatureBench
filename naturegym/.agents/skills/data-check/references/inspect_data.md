# inspect_data.py Usage Guide

The script at `scripts/inspect_data.py` inspects data files for format, readability, and metadata. All output is JSON printed to stdout.

---

## Commands

### inspect — Single file inspection

```bash
python scripts/inspect_data.py inspect <file_path>
```

Output:

```json
{
  "file_path": "string (absolute path)",
  "exists": "boolean",
  "format": "string (detected format, e.g., 'h5', 'csv', 'unknown')",
  "size_bytes": "number",
  "readable": "boolean",
  "error": "string | null",
  "metadata": {
    "shape": "list | null (e.g., [2000, 500])",
    "keys": "list | null (top-level keys for h5/npz/pkl/json)",
    "columns": "list | null (column names for csv/tsv/parquet)",
    "sample_count": "number | null (estimated sample count)",
    "dtypes": "object | null (per-key or per-column dtypes)"
  }
}
```

Notes:
- `metadata` fields vary by format — only applicable fields are present
- When `readable` is `false`, `metadata` is `null`
- For archive formats (tar.gz, zip, etc.), the script automatically performs integrity verification instead of content inspection, returning `integrity` field instead of `metadata`

### inspect-dir — Directory inspection

```bash
python scripts/inspect_data.py inspect-dir <directory_path>
python scripts/inspect_data.py inspect-dir <directory_path> --no-recursive
```

Output: array of `inspect` results (one per data file).

Notes:
- Default behavior is recursive (scans all subdirectories)
- Use `--no-recursive` to inspect only top-level files
- Only scans files with recognized data extensions (see Supported Formats below) — other files are skipped
- Hidden directories (starting with `.`) are skipped

### verify-archive — Archive integrity check

```bash
python scripts/inspect_data.py verify-archive <archive_path>
```

Output:

```json
{
  "file_path": "string (absolute path)",
  "format": "string (e.g., 'tar.gz', 'zip')",
  "size_bytes": "number",
  "integrity": "valid | corrupted | not_checked",
  "error": "string | null"
}
```

Notes:
- `not_checked`: verification could not be performed (unsupported format, command not found, or timeout)
- Verification timeout is 7200 seconds

---

## Supported Formats

| Category | Extensions | Inspection level |
|----------|-----------|-----------------|
| HDF5 | `.h5`, `.hdf5`, `.hdf`, `.he5`, `.h5ad`, `.loom` | Full metadata (keys, shapes, dtypes, sample count) |
| Tabular | `.csv`, `.tsv`, `.parquet`, `.pq` | Full metadata (columns, dtypes, shape, sample count) |
| NumPy | `.npy`, `.npz` | Full metadata (shape, dtype, keys for npz) |
| Pickle | `.pkl`, `.pickle` | Full metadata (type, shape/length/keys); layered fallback for Python 2 pickles and missing modules |
| JSON | `.json`, `.jsonl` | Structure metadata (type, keys, sample count) |
| Bioinformatics | `.fasta`, `.fa`, `.fna`, `.faa`, `.fastq`, `.fq` | Sequence count |
| Structural | `.pdb`, `.sdf`, `.mol2` | Atom/molecule count, chains |
| Medical/Images | `.nii`, `.nii.gz`, `.tif`, `.tiff` | Structure metadata (shape, pages) |
| MATLAB | `.mat` | Full metadata (keys for v7.3 HDF5 and standard mat) |
| R Data | `.rds`, `.rdata` | Unsupported in python, returns readable=False |
| PyTorch | `.pt`, `.pth` | Readability check only (type, keys) |
| Archives | `.tar.gz`, `.tgz`, `.tar.bz2`, `.tar.xz`, `.zip`, `.gz`, `.bz2`, `.7z` | Integrity verification only |

Files with unrecognized extensions return `format: "unknown"` and `readable: false`.

---

## Format Detection

The script detects formats by:
1. File extension mapping (primary)
2. Magic bytes fallback (for files with missing or incorrect extensions): HDF5, NumPy, ZIP, Parquet, gzip, bzip2

---

## Library Dependencies

The following packages must be installed before running the script. Missing packages cause affected files to return `readable: false`, which may lead to setting failures unrelated to data quality.

```bash
pip install h5py pandas pyarrow numpy scipy nibabel tifffile
# torch: install separately per https://pytorch.org if PyTorch files need inspection
```

| Format | Required package |
|--------|-----------------|
| HDF5 | `h5py` |
| CSV/TSV | `pandas` (basic fallback without pandas available) |
| Parquet | `pyarrow` (falls back to `pandas`) |
| NumPy | `numpy` |
| MATLAB | `scipy` (falls back to `h5py` for v7.3 HDF5-based files) |
| NIfTI | `nibabel` |
| TIFF | `tifffile` |
| PyTorch | `torch` |
| Pickle, JSON, FASTA, PDB, SDF | Standard library only |
