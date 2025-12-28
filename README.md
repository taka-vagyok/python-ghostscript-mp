# GhostscriptWrapMP

GhostscriptWrapMP is a Python wrapper for [Ghostscript](https://www.ghostscript.com/) that allows for parallel processing of file conversions. It leverages Python's `multiprocessing` module to run Ghostscript commands in the background, enabling non-blocking execution and efficient utilization of system resources.

## Features

- **Parallel Processing**: Execute Ghostscript commands in a separate process.
- **Python 3 Support**: Fully compatible with Python 3.
- **Customizable**: Set resolution, output device, and Ghostscript executable path.
- **Error Handling**: Robust handling of subprocess errors and missing executables.
- **Status Reporting**: detailed result objects containing execution time, output messages, and error details.

## Requirements

- Python 3.x
- Ghostscript installed and available in the system PATH (or provided via `gs_path`).
  - Linux: `gs`
  - Windows: `gswin32c.exe` or `gswin64c.exe`

## Usage

### Basic Example

```python
from ghostscriptmp import GhostscriptWrapMP

# Initialize the wrapper
# Default resolution: 200 dpi, Default device: tiffg4
gs = GhostscriptWrapMP(resolution=300, device="tiffg4")

# Define input files and output path
source_files = ["input.ps"]
output_path = "output.tiff"

# Start decomposition (conversion) in a background process
gs.decompose(source_files, output_path)

# Wait for the result
result = gs.result()

if result.is_success():
    print("Conversion successful!")
    print(f"Time taken: {result.proc_time()} seconds")
else:
    print("Conversion failed.")
    print(f"Error: {result.message}")
    print(f"Stderr: {result.emessage}")
```

### Specifying Ghostscript Path

If Ghostscript is not in your PATH, you can specify it directly:

```python
gs = GhostscriptWrapMP(gs_path="/usr/local/bin/gs")
```

## API Reference

### `GhostscriptWrapMP`

The main class for handling Ghostscript operations.

#### `__init__(resolution=200, device="tiffg4", gs_path=None)`

- `resolution` (int): Output resolution in DPI. Default is 200.
- `device` (str): Ghostscript output device (e.g., `tiffg4`, `png16m`, `pdfwrite`). Default is `tiffg4`.
- `gs_path` (str, optional): Path to the Ghostscript executable. If `None`, the script searches for standard executables in the system PATH.

#### `decompose(srcfiles, destpath)`

Starts the conversion process in a separate process.

- `srcfiles` (list): List of paths to source files (e.g., `['file1.ps', 'file2.ps']`).
- `destpath` (str): Path for the output file.

#### `result()`

Waits for the process to complete and returns a `DecompResult` object.

### `DecompResult`

A named tuple-like object containing the result of the operation.

- `error` (int or None): Return code of the process. `None` indicates success.
- `destfile` (str or None): Path to the created destination file.
- `message` (str): Stdout/Stderr output from Ghostscript.
- `emessage` (str): Error message string (if any specific error occurred).
- `proc_time()`: Returns the duration of the process in seconds.
- `is_success()`: Returns `True` if the operation was successful.
