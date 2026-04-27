# manage-venv

A single-file Python script that automates virtual environment setup and dependency management.

## What it does

1. **Combines requirements**: scans immediate subdirectories for `requirements.txt` files and merges them into a root `requirements.txt`.
2. **Creates the venv**: creates a `venv/` directory if one doesn't already exist.
3. **Installs dependencies**: runs `pip install -r requirements.txt` inside the venv.
4. **Pins unpinned packages**: replaces bare package names (e.g. `requests`) with the exact installed version (e.g. `requests==2.32.3`), preserving inline comments.
5. **Checks for upgrades**: lists outdated packages from `requirements.txt` and interactively prompts to upgrade them.

## Usage

Copy `manage-venv.py` into the root of your project and run it:

```bash
python3 manage-venv.py
```

The script expects your project to have one or more `requirements.txt` files in immediate subdirectories (e.g. `2024/requirements.txt`, `2025/requirements.txt`), which it combines before proceeding. This is ideal for monorepos.

## Configuration

At the top of `manage-venv.py`:

```python
PYTHON_VERSION = "3.9"  # Set to None to use the system default python3
```

Change `PYTHON_VERSION` to match the Python interpreter you want the venv to use.

## Requirements

- Python 3.9+
- `pip` available in the target Python interpreter
- No third-party dependencies; uses only the standard library

## License

Public domain. See [The Unlicense](LICENSE).
