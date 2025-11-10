"""
Initializes and updates a Pylings workspace.

Handles tasks such as setting up exercises, syncing solutions,
managing `.pylings.toml`, and cleaning obsolete files.
"""

import filecmp
import logging
from pathlib import Path
import shutil
import subprocess
import textwrap
import toml

from pylings.constants import IGNORED_DIRS, IGNORED_FILES
from pylings.utils import PylingsUtils

log = logging.getLogger(__name__)


def init_workspace(path: str = None, force: bool = False):
    """Initialize a new Pylings workspace.

    Creates a target directory with exercises and configuration.
    If a workspace already exists, skips or overwrites based on `force`.

    Args:
        path (str, optional): Target path for the workspace. Defaults to current directory.
        force (bool): Overwrite existing workspace if True.
    """
    cwd = Path.cwd()
    if path:
        path = path.strip()

    target_dir = (
        Path(path).expanduser().absolute()
        if path else (cwd if force or (cwd / ".pylings.toml").exists() else cwd / "pylings")
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    exercises_src = Path(__file__).parent / "exercises"
    exercises_dst = target_dir / "exercises"

    if exercises_dst.exists():
        if force:
            shutil.rmtree(exercises_dst)
        else:
            print(
                f"Found existing exercises at {exercises_dst}, skipping copy. "
                "Use --force to overwrite."
            )
            exercises_dst = None

    if exercises_dst is not None:
        shutil.copytree(exercises_src, exercises_dst)

    version = PylingsUtils.get_installed_version()
    (target_dir / ".pylings.toml").write_text(
        textwrap.dedent(f'''\
            [workspace]
            version = "{version}"
            firsttime = true
            current_exercise = "00_intro/intro1.py"

            [theme]
            name = "default"
            GREEN = "bold green"
            RED = "bold red"
            ORANGE = "bold orange"
            LIGHT_BLUE = "bold lightblue"
            BACKGROUND = "#1e1e2e"
        ''')
    )
    initialise_git(target_dir)
    print("Pylings initialised at:", target_dir)


def update_workspace(path: str = None):
    """Update an existing Pylings workspace with the latest exercises and solutions.

    Synchronizes content with the package source and sets the current version in `.pylings.toml`.
 
    Args:
        path (str, optional): Target workspace path. Defaults to current directory.
    """
    cwd = Path.cwd()
    target_dir = Path(path).resolve() if path else cwd
    root_dir = PylingsUtils.get_package_root()

    print(f"Updating workspace at: {target_dir}")

    for folder_name in ["exercises", "solutions"]:
        update_folder(root_dir, target_dir, folder_name)

    cleanup_backups(root_dir, target_dir)
    set_workspace_version(PylingsUtils.get_installed_version())
    print("\nSee changelog: https://github.com/CompEng0001/pylings/blob/main/CHANGELOG.md")


def update_folder(root_dir, target_dir, folder_name):
    """Update a specific folder (exercises or solutions) in the workspace.

    Compares files between source and destination, updates changed ones,
    skips existing ones, and flags modified files for manual review.

    Args:
        root_dir (Path): Root path of the package source.
        target_dir (Path): Workspace path to update.
        folder_name (str): Folder to update ('exercises' or 'solutions').
    """
    src_dir = root_dir / folder_name
    dst_dir = target_dir / folder_name

    if not src_dir.exists():
        print(f"Source folder {src_dir} does not exist. Skipping.")
        return

    new_files, removed_files, skipped_files, notify_files = [], [], [], []

    # Cleanup removed files
    for dst_file in dst_dir.rglob("*"):
        if dst_file.is_file() and not (
            dst_file.name in IGNORED_FILES or any(part in IGNORED_DIRS for part in dst_file.parts)
        ):
            rel_path = dst_file.relative_to(dst_dir)
            src_file = src_dir / rel_path
            if not src_file.exists():
                try:
                    dst_file.unlink()
                    removed_files.append(str(rel_path))
                except (PermissionError, FileNotFoundError, OSError) as e:
                    print(f"Could not remove {dst_file}: {e}")

    # Cleanup empty directories
    for dirpath in sorted(dst_dir.rglob("*"), reverse=True):
        if dirpath.is_dir() and not any(dirpath.iterdir()):
            try:
                dirpath.rmdir()
            except OSError:
                pass

    # Copy and update files
    for src_file in src_dir.rglob("*"):
        if src_file.is_file() and not (
            src_file.name in IGNORED_FILES or any(part in IGNORED_DIRS for part in src_file.parts)
        ):
            rel_path = src_file.relative_to(src_dir)
            dest_file = dst_dir / rel_path
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            if not dest_file.exists():
                if folder_name == "solutions":
                    # Only copy if the destination already had this file
                    # (i.e., skip adding new solutions)
                    continue
                shutil.copy2(src_file, dest_file)
                new_files.append(str(rel_path))
            elif not filecmp.cmp(src_file, dest_file, shallow=False):
                if folder_name == "solutions":
                    shutil.copy2(src_file, dest_file)
                    new_files.append(str(rel_path))
                elif folder_name == "exercises":
                    notify_files.append(str(rel_path))
            else:
                skipped_files.append(str(rel_path))

    for label, files in [
        ("\nUpdated or added:", new_files),
        ("\nRemoved:", removed_files),
    ]:
        if files:
            print(label)
            for f in files:
                symbol = ''
                if label.startswith('Updated'):
                    symbol = '+'
                elif label.startswith('Removed'):
                    symbol = '-'
                print(f"\t{symbol} {f}")

    if notify_files:
        print("\nThe following exercise files have been modified by the user " +
               "and were NOT overwritten:\n"
        )

        for file in notify_files:
            print(f"\t{file}")

        print("\nIf you want to manually reset them, use: pylings reset <exercise_path>")
        print("or invoke the reset within pylings using 'r':")

def cleanup_backups(root_dir, target_dir):
    """Remove outdated 'backups/' directory from the workspace if not present in source.

    Args:
        root_dir (Path): Source path of the Pylings package.
        target_dir (Path): Path of the user's workspace.
    """
    src_backups = root_dir / "backups"
    dst_backups = target_dir / "backups"
    if dst_backups.exists() and not src_backups.exists():
        shutil.rmtree(dst_backups)
        print("Removed stale backups/ directory")


def set_workspace_version(version: str):
    """Update the workspace version in the `.pylings.toml` file.

    Args:
        version (str): The version string to set.
    """
    pylings_toml = Path(".pylings.toml")
    try:
        data = toml.load(pylings_toml) if pylings_toml.exists() else {}
    except OSError as e:
        print(f"\nCould not read .pylings.toml: {e}")
        data = {}

    data.setdefault("workspace", {})["version"] = version

    try:
        with pylings_toml.open("w", encoding="utf-8") as f:
            toml.dump(data, f)
        print(f"\nUpdated .pylings.toml workspace version to {version}")
    except OSError as e:
        print(f"\nFailed to write .pylings.toml: {e}")

def initialise_git(target_dir):
    """Initialize a Git repository in the workspace.

    Creates a `.git` directory and adds a default `.gitignore`.

    Args:
        target_dir (Path): Path to initialize Git in.
    """
    git_dir = target_dir / ".git"
    if not git_dir.exists():
        try:
            subprocess.run(
                ["git", "init"],
                cwd=target_dir,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            (target_dir / ".gitignore").write_text(
                "__pycache__/\n*.pyc\n.venv/\n.pylings_debug.log\n"
            )
        except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
            print(f"Failed to initialize git repository: {e}")
# End-of-file (EOF)
