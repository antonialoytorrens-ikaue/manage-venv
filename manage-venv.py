#!/usr/bin/env python3
"""
A script to manage a Python virtual environment and its dependencies.

This script automates the following tasks:
1.  Ensures a virtual environment exists, creating it if necessary.
2.  Installs dependencies from a requirements.txt file.
3.  Pins any unpinned dependencies in requirements.txt to the specific versions
    currently installed in the environment, preserving comments and duplicates.
4.  Checks for available upgrades for the pinned packages and prompts the user
    to install them.
"""
from subprocess import run, CalledProcessError
from re import compile
from sys import exit as sys_exit
from pathlib import Path
from subprocess import CompletedProcess

# --- Configuration ---
PYTHON_VERSION = "3.9"     # Specify the Python version to use for the virtual environment, set None for default
# ---------------------

VENV_DIR = "venv"
REQUIREMENTS_FILE = "requirements.txt"
PYTHON_EXECUTABLE = "python3" if not PYTHON_VERSION else f"python{PYTHON_VERSION}"

# Captures the package name, ignores comments and editable installs
PACKAGE_REGEX = compile(r"^\s*([a-zA-Z0-9\-_]+(?:\[[a-zA-Z0-9\-_,]+\])?)\s*")


def run_command(command: list[str], capture: bool = False):
    """Executes a command and handles errors."""
    try:
        print(f">> Running command: {' '.join(command)}")
        result = run(
            command,
            check=True,
            capture_output=capture,
            text=True,
            encoding='utf-8'
        )
        return result
    except FileNotFoundError:
        print(f">> Error: Command not found: {command[0]}. Is it in your PATH?")
        sys_exit(1)
    except CalledProcessError as e:
        print(f">> Error executing command: {' '.join(command)}")
        print(f">> Return code: {e.returncode}")
        if capture:
            print(f">>   Stdout: {e.stdout.strip()}")
            print(f">>   Stderr: {e.stderr.strip()}")
        sys_exit(1)


def source_and_combine_requirements():
    """
    Finds all requirements.txt files in immediate subdirectories
    and combines them into a single root requirements.txt file.
    """
    print("> Searching for 'requirements.txt' in subdirectories...")

    # Find deps at './YYYY/requirements.txt' and sort the list to ensure consistent output.
    found_files = sorted(list(Path('.').glob(f'*/{REQUIREMENTS_FILE}')))
    for f in found_files:
        print(f">> Found: {f}")

    with open(REQUIREMENTS_FILE, 'w', encoding='utf-8') as outfile:
        outfile.write("\n".join([open(f, 'r', encoding='utf-8').read() for f in found_files]))


def setup_virtual_environment():
    """
    Checks for a virtual environment and creates one if it doesn't exist.
    """
    PYTHON_VENV_EXECUTABLE = Path(f"{VENV_DIR}/bin/python")
    if not Path(VENV_DIR).is_dir() or not PYTHON_VENV_EXECUTABLE.is_file():
        print(f">> Creating virtual environment at '{VENV_DIR}'...")
        run_command([PYTHON_EXECUTABLE, "-m", "venv", VENV_DIR])
        print(">> Virtual environment created successfully.")
    else:
        print(f">> Virtual environment found at '{VENV_DIR}'.")

    return PYTHON_VENV_EXECUTABLE


def pin_dependencies(venv_python_path):
    """
    Checks requirements.txt for unpinned dependencies and pins them.

    If a package like 'requests' is found, it determines the installed version
    and replaces the line with 'requests==x.y.z', preserving comments.
    """
    print("> Checking for unpinned dependencies in requirements.txt...")
    try:
        with open(REQUIREMENTS_FILE, "r", encoding='utf-8') as f:
            original_lines = f.readlines()
    except FileNotFoundError:
        print(f">> WARNING: '{REQUIREMENTS_FILE}' not found. Skipping dependency pinning.")
        return

    needs_pinning = False
    for line in original_lines:
        # A line is considered unpinned if it's a package and doesn't have '=='
        if PACKAGE_REGEX.match(line) and "==" not in line:
            needs_pinning = True
            break

    if not needs_pinning:
        print("> NOTE: All dependencies are already pinned.")
        return

    print("> Unpinned dependencies found. Generating pinned versions...")

    # Get a map of installed packages to their pinned versions
    freeze_result = run_command([str(venv_python_path), "-m", "pip", "freeze"], capture=True)
    installed_packages = {
        name.lower(): full_spec
        for line in freeze_result.stdout.strip().split("\n")
        if "==" in (full_spec := line.strip()) and (name := full_spec.split("==")[0])
    }

    new_lines = []
    for line in original_lines:
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("#"):
            new_lines.append(line)
            continue

        match = PACKAGE_REGEX.match(line)
        # Check if it's a requirement line and is not pinned
        if match and "==" not in line:
            package_name = match.group(1).lower().split('[')[0]  # Normalize name
            if package_name in installed_packages:
                pinned_version = installed_packages[package_name]
                # Preserve inline comments
                if '#' in line:
                    parts = line.split('#', 1)
                    new_line = f"{pinned_version}  # {parts[1].strip()}\n"
                else:
                    new_line = f"{pinned_version}\n"
                new_lines.append(new_line)
                print(f">> Pinned '{package_name}' to '{pinned_version.strip()}'")
            else:
                # Keep line as is if package not found (might be a URL, etc.)
                new_lines.append(line)
        else:
            # Line is already pinned, a comment, or something else
            new_lines.append(line)

    # Write the updated, pinned requirements back to the file
    with open(REQUIREMENTS_FILE, "w", encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"> Successfully updated '{REQUIREMENTS_FILE}' with pinned versions.")


def check_for_upgrades(venv_python_path):
    """
    Checks for outdated packages listed in requirements.txt and prompts the user to upgrade them.
    """
    print("> Checking for package upgrades...")

    # Read requirements.txt to get a set of packages to track.
    try:
        with open(REQUIREMENTS_FILE, "r", encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"> WARNING: '{REQUIREMENTS_FILE}' not found. Cannot check for targeted upgrades.")
        return

    requirements_packages = set()
    for line in lines:
        match = PACKAGE_REGEX.match(line)
        if match:
            # Normalize to lowercase and remove extras like [all] to match pip's output
            package_name = match.group(1).lower().split('[')[0]
            requirements_packages.add(package_name)

    # Get all outdated packages from pip.
    try:
        result = run_command(
            [str(venv_python_path), "-m", "pip", "list", "--outdated"],
            capture=True
        )
    except CalledProcessError as e:
        # pip list --outdated exits with status 0 even if packages are outdated.
        # This error is for actual command failures.
        print(f"> Could not check for outdated packages. Error: {e.stderr}")
        return

    outdated_lines = result.stdout.strip().split("\n")
    if len(outdated_lines) <= 2:
        print("> All packages are up to date.")
        return

    # Filter the outdated list to only include packages from requirements.txt.
    targeted_upgrades = []
    for line in outdated_lines[2:]:
        try:
            # Format is: Package Version Latest Type
            package, current_v, latest_v, _ = line.split()
            if package.lower() in requirements_packages:
                targeted_upgrades.append((package, current_v, latest_v))
        except ValueError:
            # Skip any lines that don't parse correctly
            continue

    if not targeted_upgrades:
        print("> All packages listed in requirements.txt are up to date.")
        return

    print("> Upgrades available for the following packages:")
    for pkg, current, latest in targeted_upgrades:
        print(f">>   - {pkg}: {current} -> {latest}")

    try:
        answer = input("> Would you like to upgrade these packages? (y/n): ").lower().strip()
    except EOFError:
        answer = 'n'    # Default to no on non-interactive environments

    if answer == "y":
        packages_to_upgrade = [pkg[0] for pkg in targeted_upgrades]
        run_command(
            [str(venv_python_path), "-m", "pip", "install", "--upgrade", *packages_to_upgrade]
        )
        print("> Packages upgraded successfully.")
    else:
        print("> No packages were upgraded.")


def main():
    """Main execution flow."""
    # Source requirements.txt
    source_and_combine_requirements()

    if not Path(REQUIREMENTS_FILE).is_file():
        raise FileNotFoundError(
            f"The '{REQUIREMENTS_FILE}' file was not generated. Please create a requirements.txt file with your project's dependencies."
        )
        sys_exit(1)

    # Create venv if not created
    venv_python_path = setup_virtual_environment()

    # Install dependencies
    print(f"Installing dependencies from '{REQUIREMENTS_FILE}'...")
    run_command([str(venv_python_path), "-m", "pip", "install", "-r", REQUIREMENTS_FILE])
    print("Dependencies installed.")

    # Pin unpinned dependencies
    pin_dependencies(venv_python_path)

    # Check for upgrades
    check_for_upgrades(venv_python_path)


if __name__ == "__main__":
    main()
