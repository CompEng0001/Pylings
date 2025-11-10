"""
utils.py — Core utility functions for the Pylings CLI and UI components.

This module defines the `PylingsUtils` class, a static utility container providing
functionality across the Pylings application for:

- Parsing and handling command-line arguments.
- Validating and inspecting `.pylings.toml` configuration files.
- Detecting Git status for version tracking and user hints.
- Checking version consistency between installed and workspace environments.
- Extracting package metadata via `pip show`.
- Generating Rich-formatted clickable links and output text for the terminal UI.

It is intended for internal use within the CLI and Textual-based interface.

Modules used:
    - argparse: For CLI argument parsing
    - subprocess: For Git and pip metadata access
    - toml: For config parsing
    - rich.text.Text: For stylized terminal output
"""
from argparse import ArgumentParser, RawTextHelpFormatter, Namespace
from collections import defaultdict, Counter
import logging
from pathlib import Path
import shutil
import subprocess
import sys
import importlib.util
from typing import Optional
import toml
from toml import TomlDecodeError
from rich.text import Text

import pylings
from pylings.constants import GREEN, LIGHT_BLUE, MAX_LIST, PYLINGS_TOML, RESET_COLOR

log = logging.getLogger(__name__)

class PylingsUtils:
    """Static utility class for Pylings tooling.

    Handles CLI argument parsing, workspace and environment inspection,
    Git status, version checking, and utility formatting for UI.
    """

    @staticmethod
    def parse_args() -> Namespace:
        """Parse command-line arguments for the Pylings CLI.

        Returns:
            Namespace: Parsed argument object.
        """
        log.debug("PylingsUtils.parse_args: Entered")
        parser = ArgumentParser(
            prog="pylings",
            description=(
                "Pylings is a collection of small exercises to get you used to writing "
                "and reading Python code."
            ),
            formatter_class=RawTextHelpFormatter,
        )

        parser.add_argument(
            "-v",
            "--version",
            action="store_true",
            help="Get version and information about Pylings."
        )
        parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
        subparsers = parser.add_subparsers(dest="command")

        init_parser = subparsers.add_parser("init", help="Initialize a pylings workspace.")
        init_parser.add_argument(
            "--path", type=str, help="Target folder (default: current directory)"
        )
        init_parser.add_argument(
            "--force",
            action="store_true",
            help="Reinitialize workspace (overwrites existing files)"
        )

        update_parser = subparsers.add_parser(
            "update",
            help="Update workspace with current version"
        )
        update_parser.add_argument(
            "--path", type=str, help="Target folder (default: current directory)"
        )

        run_parser = subparsers.add_parser("run", help="Run pylings at the supplied exercise.")
        run_parser.add_argument(
            "file", type=str,
            help="Path to the exercise file, e.g., exercises/00_intro/intro1.py"
        )

        dry_parser = subparsers.add_parser(
            "dry-run", help="Dry-run an exercise non-interactively."
        )
        dry_parser.add_argument(
            "file", type=str,
            help="Path to the exercise file. e.g., exercises/00_intro/intro1.py"
        )
        dry_parser.add_argument(
            "--source", choices=["workspace", "package"], default="workspace",
            help="Select path context: workspace or package"
        )

        solutions_parser = subparsers.add_parser(
            "sol", help="Check solution for supplied exercise non-interactively."
        )
        solutions_parser.add_argument(
            "file", type=str,
            help="Path to the solution file. e.g., [solutions|exercises]/00_intro/intro1.py"
        )
        solutions_parser.add_argument(
            "--source", choices=["workspace", "package"], default="package",
            help="Select path context: workspace or package"
        )
        reset_parser = subparsers.add_parser(
            "reset", help="Reset an exercise non-interactively."
        )
        reset_parser.add_argument(
            "file", type=str,
            help="Path to the exercise file, e.g., exercises/00_intro/intro1.py"
        )

        return parser.parse_args()

    @staticmethod
    def handle_args(args: Namespace, exercise_manager) -> bool:
        """Handle parsed CLI arguments and execute appropriate commands.

        Args:
            args (Namespace): Parsed CLI arguments.
            exercise_manager: Instance managing exercises.

        Returns:
            bool: True if an exercise was selected and should be run interactively, else False.
        """
        log.debug("PylingsUtils.handle_args: Entered")

        if not args.command:
            return False

        if args.command == "sol":
            path = Path(args.file)
            source = getattr(args, "source", "package")
            try:
                exercise_manager.run_and_print(path, source, "s")
            except FileNotFoundError as e:
                log.error("Invalid exercise path: %s (%s)",args.file, e)
                sys.exit(1)

        elif args.command == "dry-run":
            path = Path(args.file)
            source = getattr(args, "source", "workspace")
            try:
                exercise_manager.run_and_print(path, source, "d")
            except FileNotFoundError as e:
                log.error("Invalid exercise path: %s (%s)",args.file, e)
                sys.exit(1)

        elif args.command == "run":
            path = Path(args.file)
            source = getattr(args, "source", "workspace")
            try:
                exercise_manager.arg_exercise = exercise_manager.get_exercise_path(path, source)
                return True
            except FileNotFoundError as e:
                log.error("Invalid exercise path: %s (%s)",args.file, e)
                sys.exit(1)

        elif args.command == "reset":
            path = Path(args.file)
            try:
                exercise_manager.reset_exercise_by_path(path)
            except FileNotFoundError as e:
                log.error("Invalid exercise path: %s (%s)",args.file, e)
                sys.exit(1)
        return False

    @staticmethod
    def is_pylings_toml() -> bool:
        """Check whether `.pylings.toml` exists in the current or parent directories.

        Returns:
            bool: True if a Pylings workspace is detected, False otherwise.
        """
        log.debug("PylingsUtils.is_pylings_toml: Entered")
        for p in [Path.cwd()] + list(Path.cwd().parents):
            if (p / ".pylings.toml").exists():
                log.debug("PylingsUtils.is_pylings_toml: true")
                return True
        print("Not a pylings workspace.")
        print("Change to pylings workspace, if it exists, or")
        print("Run: pylings init [--path /path/to/pylings]")
        print("\t Or pylings --help")
        return False

    @staticmethod
    def check_python_version():
        """Compares earliest supported version of python 3.10.0 to sys.version_info
           Will exit pylings if not supported.
        """
        required_version = (3, 10, 0)
        current_version = sys.version_info[:3]
        if current_version < required_version:
            print(f"Python {required_version[0]}.{required_version[1]}.{required_version[2]}" +
                " or higher is required to run Pylings."
            )
            sys.exit(1)

    @staticmethod
    def get_git_status() -> Optional[list[str]]:
        """Return the list of modified/added files from `git status --short`.

        Returns:
            list[str] | None: List of lines from Git status, or None if Git is unavailable.
        """
        log.debug("PylingsUtils.get_git_status: Entered")
        if not shutil.which("git"):
            return None
        try:
            result = subprocess.run([
                "git", "status", "--short"
            ], capture_output=True, text=True, check=True)
            lines = result.stdout.strip().splitlines()
            return lines if lines else None
        except subprocess.CalledProcessError as e:
            log.error("PylingsUtils.get_git_status error: %s",e)
            return None

    @staticmethod
    def get_local_version() -> str:
        """Get the Pylings version recorded in `.pylings.toml`.

        Returns:
            str: The version string or 'Unknown' on failure.
        """
        log.debug("PylingsUtils.get_local_version: Entered")
        if PYLINGS_TOML.exists():
            try:
                pyproject_data = toml.load(PYLINGS_TOML)
                return pyproject_data.get("workspace", {}).get("version", "Unknown")
            except (OSError, TomlDecodeError) as e:
                log.error("get_local_version error: %s", e)
                return "Unknown"
        return "Not in a local initialised pylings directory"

    @staticmethod
    def get_installed_version() -> str:
        """Get the installed version of the `pylings` Python package.

        Returns:
            str: Installed version string (fallback to '0.1.0' if not found).
        """
        try:
            return pylings.__version__
        except AttributeError:
            return "0.1.0"

    @staticmethod
    def get_package_root() -> Path:
        """Get the root directory of the installed Pylings package.

        Returns:
            Path: Path to the root of the installed package.
        """
        spec = importlib.util.find_spec("pylings")
        if spec is None or spec.origin is None:
            # Handle the error or provide a fallback path
            raise ImportError("Cannot find 'pylings' module or origin path")
        return Path(spec.origin).parent

    @staticmethod
    def get_workspace_version() -> Optional[str]:
        """Read the workspace version from `.pylings.toml`.

        Returns:
            str | None: Workspace version string, or None if not found.
        """
        pylings_toml = Path(".pylings.toml")
        if not pylings_toml.exists():
            return None
        try:
            data = toml.load(pylings_toml)
            return data.get("workspace", {}).get("version")
        except (OSError, TomlDecodeError) as e:
            print("Could not read workspace version: %s",e)
            return None

    @staticmethod
    def check_version_mismatch():
        """Check for mismatches between workspace and installed versions.

        If mismatch is found, print upgrade instructions and sys.exit.
        """
        workspace_version = PylingsUtils.get_workspace_version()
        installed_version = pylings.__version__

        if workspace_version and workspace_version != installed_version:
            print(
                f"\nYour workspace was created with pylings v{workspace_version}, "
                f"but v{installed_version} is now installed."
            )
            print("To update your exercises with new content only, run:")
            print("   pylings update\n")
            sys.exit(1)

    @staticmethod
    def get_pip_package_info():
        """Retrieve detailed pip metadata about the installed `pylings` package.

        Returns:
            tuple[str, str, str, str]: Version, license, GitHub URL, and PyPI info string.
        """
        log.debug("PylingsUtils.get_pip_package_info: Entered")
        try:
            result = subprocess.run([
                "pip", "show", "pylings", "--verbose"
            ], capture_output=True, text=True, check=True)

            version = "Unknown"
            license_text = "Unknown"
            github = "Unknown"
            pypiorg = "Unknown"

            for line in result.stdout.splitlines():
                if line.startswith("Version:"):
                    version = line.split(":", 1)[1].strip()
                elif line.startswith("License:"):
                    license_text = line.split(":", 1)[1].strip()
                elif line.startswith("Home-page:"):
                    pypiorg = line.split(":", 1)[1].strip()
                elif "Repository," in line:
                    github = line.split(",", 1)[1].strip()

            return version, license_text, github, pypiorg
        except subprocess.CalledProcessError:
            log.error("get_pip_package_info: Package not installed")
            return "Not Installed", "N/A", "N/A", "N/A"

    @staticmethod
    def make_link(display: str, target_path: Path, prefix: str, label: str) -> Text:
        """Create a stylized clickable Text link to a given file path.

        Args:
            display (str): Display name for the link.
            target_path (Path): Full file path.
            prefix (str): Display prefix, e.g., 'exercises' or 'solutions'.
            label (str): Label text prepended to the link.

        Returns:
            Text: Rich text object with embedded link.
        """
        uri = target_path.absolute().as_uri()
        fixed_display = display.replace('\\', '/')
        formatted = f"{prefix}/{fixed_display}"
        text = Text(label)
        text.append(f"{GREEN}{formatted}{RESET_COLOR}", style=f" link {uri}")
        return text

    @staticmethod
    def git_suggestion(git_status_lines):
        """Create a Rich Text block with compact, grouped git hints.

        - Shows first MAX_LIST files verbatim, then collapses the rest.
        - Groups by top-level directory for a quick mental model.
        - Offers safe staging options: modified-only, directory-scoped, or
        'everything except' common folders (solutions/ backups/ .venv/).
        - Always suggests interactive staging (`git add -p`) for fine-grained control.
        """
        text = Text()
        if not git_status_lines:
            return text.append("")

        # Parse status lines from `git status --short`
        items = []
        for line in git_status_lines:
            status = line[:2].strip()
            path = line[3:].strip()
            items.append((status, path))

        # Split categories (optional, used for counts)
        cats = Counter(s for s, _ in items)

        # Build a concise file list
        shown = items[:MAX_LIST]
        hidden = items[MAX_LIST:]

        text.append("Use ")
        text.append("git", style="underline")
        text.append(" to keep track of your progress:\n\n")

        if hidden:
            # Show first MAX_LIST, then a summary
            for _, p in shown:
                text.append(f"  • {p}\n")
            text.append(f"\n…and {len(hidden)} more changed path(s)\n")

            # Group hidden by top-level directory
            groups = defaultdict(int)
            for _, p in hidden:
                top = p.split("/", 1)[0] if "/" in p else p
                groups[top] += 1

            if groups:
                text.append("\nBy directory (additional paths):\n")
                for top, count in sorted(groups.items(), key=lambda x: (-x[1], x[0])):
                    text.append(f"  • {top}/  (+{count})\n")
        else:
            # Small set: show all paths
            for _, p in shown:
                text.append(f"  • {p}\n")

        return text
# End-of-file (EOF)
