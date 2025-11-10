"""
Provides the ExerciseManager class for managing the lifecycle of Pylings exercises.

Handles loading, checking, resetting, and running exercises, as well as tracking completion
and progress state for UI and CLI tools.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
from pathlib import Path
from shutil import copy, copy2
import subprocess

import pylings
from pylings.config import ConfigManager
from pylings.constants import (BACKUP_DIR, EXERCISES_DIR,FINISHED, SOLUTIONS_DIR)

log = logging.getLogger(__name__)

class ExerciseManager:
    """Manages the lifecycle of exercises in Pylings.

    Responsibilities include:
    - Initializing exercise metadata and tracking state.
    - Executing exercises and retrieving output.
    - Resetting exercises to their original form.
    - Moving to the next exercise.
    - Checking completion status and tracking progress.
    - Providing access to matching solutions.
    """

    def __init__(self):
        """Initializes the exercise manager and loads exercises.

        Also checks if this is the first time running the workspace.
        """
        log.debug("ExerciseManager.__init__")
        self.exercises = {}
        self.current_exercise = None
        self.current_exercise_state = ""
        self.arg_exercise = None
        self.completed_count = 0
        self.completed_flag = False
        self.config_manager = ConfigManager()
        self.watcher = None
        self.show_hint = False

        self._initialize_exercises()
        self.config_manager.check_first_time()

    def _initialize_exercises(self):
        """Loads and evaluates all exercises from the workspace into memory."""
        exercises = sorted(EXERCISES_DIR.rglob("*.py"))
        results = self._evaluate_exercises_ordered(exercises)

        for path, result in results:
            self._store_result(path, result)

        self.current_exercise = EXERCISES_DIR / self.config_manager.get_lasttime_exercise()
        self.current_exercise_state = self.exercises[self.current_exercise.name]["status"]
        self.completed_count = sum(1 for ex in self.exercises.values() if ex["status"] == "DONE")

    def _evaluate_exercises_ordered(self, exercise_paths):
        """Runs each exercise and returns results in original order.

        Args:
            exercise_paths (list[Path]): Paths to all exercises.

        Returns:
            list[tuple[Path, subprocess.CompletedProcess]]: Paths and their results.
        """
        results = [None] * len(exercise_paths)
        with ThreadPoolExecutor() as executor:
            future_to_index = {executor.submit(self.run_exercise, ex): i for i, ex in enumerate(exercise_paths)}
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results[index] = (exercise_paths[index], result)
                except Exception as e:
                    log.error(f"Error processing exercise {exercise_paths[index]}: {e}")
        return results

    def _store_result(self, path, result):
        """Stores the result of an exercise run in the internal tracking dictionary."""
        name = path.name
        status = "DONE" if result.returncode == 0 else "PENDING"
        self.exercises[name] = {
            "path": path,
            "status": status,
            "output": self._format_output(result.stdout) if result.returncode == 0 else "",
            "error": self._format_output(result.stderr) if result.returncode != 0 else None,
            "hint": self.config_manager.get_hint(path),
        }

    def _update_exercise_status(self, name, result):
        """Updates the status and output of a given exercise.

        Args:
            name (str): Exercise filename.
            result (CompletedProcess): The result of executing the file.

        Returns:
            str: new status values.
        """
        new_status = "DONE" if result.returncode == 0 else "PENDING"
        self.exercises[name].update({
            "status": new_status,
            "output": self._format_output(result.stdout) if result.returncode == 0 else "",
            "error": self._format_output(result.stderr) if result.returncode != 0 else None
        })
        return new_status

    def run_exercise(self, path: Path, source: str = "workspace"):
        """Runs a Python exercise file and returns the result.

        Args:
            path (Path): Path to the exercise file.
            source (str): Where to run from: "workspace" or "package".

        Returns:
            subprocess.CompletedProcess: Contains returncode, stdout, stderr.
        """
        log.debug(f"ExerciseManager.run_exercise: path={path}, source={source}")

        # Normalize path
        path_parts = list(path.parts)
        if path_parts[0] == "exercises":
            path_parts = path_parts[1:]
        relative_path = Path(*path_parts)

        if source == "package":
            resolved_path = Path(pylings.__file__).parent / "exercises" / relative_path
        else:
            resolved_path = Path("exercises") / relative_path

        log.debug(f"Resolved path for execution: {resolved_path}")

        try:
            process = subprocess.Popen(
                [sys.executable, str(resolved_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=10)
            return subprocess.CompletedProcess(
                args=[resolved_path],
                returncode=process.returncode,
                stdout=stdout,
                stderr=stderr
            )
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return subprocess.CompletedProcess(
                args=[resolved_path],
                returncode=1,
                stdout=stdout,
                stderr="Exercise timed out."
            )
        except Exception as e:
            return subprocess.CompletedProcess(
                args=[resolved_path],
                returncode=1,
                stdout="",
                stderr=str(e)
            )

    def _format_output(self, output):
        """Sanitizes output for display, especially in Rich/Textual components."""
        return output.replace("[", "\\[")

    def update_exercise_output(self):
        """Re-runs the current exercise and updates its status and progress tracking."""
        log.debug("ExerciseManager.update_exercise_output")
        try:
            if self.arg_exercise:
                self.current_exercise = self.arg_exercise
                self.arg_exercise = None

            if not self.current_exercise:
                return

            result = self.run_exercise(self.current_exercise)
            name = self.current_exercise.name
            new_status = self._update_exercise_status(name, result)
            self.current_exercise_state = new_status

            self.completed_count = sum(1 for ex in self.exercises.values() if ex["status"] == "DONE")

            log.debug(f"ExerciseManager.update_exercise_output.self.completed_count: ${self.completed_count}")
            if self.completed_count == len(self.exercises) and not self.completed_flag:
                self.completed_flag = True
            else:
                self.completed_flag = False

        except Exception as e:
            log.exception("update_exercise_output crashed: %s", e)


    def check_all_exercises(self, progress_callback=None):
        """Checks all exercises for completion status.

        Args:
            progress_callback (Callable): Optional callback to update UI progress.
        """
        log.debug("ExerciseManager.check_all_exercises")
        current_exercise_path = self.current_exercise
        exercises = list(self.exercises.values())
        paths = [ex["path"] for ex in exercises]
        results = self._evaluate_exercises_ordered(paths)

        for i, (path, result) in enumerate(results):
            name = path.name
            self._update_exercise_status(name, result)
            if progress_callback:
                progress_callback(path.name, i, len(results))

        self.completed_count = sum(1 for ex in self.exercises.values() if ex["status"] == "DONE")
        log.debug(f"ExerciseManager.check_all_exercises.self.completed_count: ${self.completed_count}")
        self.current_exercise = current_exercise_path

    def next_exercise(self):
        """Moves to the next exercise in order.

        Updates current exercise state and triggers output update.
        """
        log.debug("ExerciseManager.next_exercise")
        exercises = list(self.exercises.values())
        current_index = next((i for i, ex in enumerate(exercises) if ex["path"] == self.current_exercise), None)

        if current_index is not None and current_index + 1 < len(exercises):
            new_exercise = exercises[current_index + 1]["path"]
            self.current_exercise = new_exercise
            self.show_hint = False
            self.update_exercise_output()
            self.current_exercise_state = self.exercises[self.current_exercise.name]["status"]
            self.config_manager.set_lasttime_exercise(new_exercise)
            if self.watcher:
                self.watcher.restart(str(self.current_exercise.parent))
                log.debug(f"ExerciseManager.next_exercises.self.current_exercise.parent: ${self.current_exercise.parent}")
        else:
            print("All exercises completed!")

    def reset_exercise(self):
        """Restores the current exercise from its backup version, if available."""
        log.debug("ExerciseManager.reset_exercise")
        if not self.current_exercise:
            print("No current exercise to reset.")
            return

        backup_path = self.current_exercise.relative_to(EXERCISES_DIR)
        root_backup = BACKUP_DIR / backup_path

        if root_backup.exists():
            root_backup.parent.mkdir(parents=True, exist_ok=True)
            copy(root_backup, self.current_exercise)
            prev_status = self.exercises[self.current_exercise.name]["status"]
            self.update_exercise_output()
            if prev_status == "DONE":
                self.completed_flag = False
                self.completed_count -= 1
        else:
            print(f"No backup found for {self.current_exercise}.")

    def get_solution(self):
        """Resolves and copies the solution file for the current exercise.

        Returns:
            tuple[Path, str] | None: Local solution path and short form, or None on failure.
        """
        log.debug("ExerciseManager.get_solution")
        if not self.current_exercise:
            return None

        try:
            SOLUTIONS_DIR.mkdir(parents=True, exist_ok=True)
            relative_path = self.current_exercise.relative_to(EXERCISES_DIR)
            solution_path = SOLUTIONS_DIR / relative_path
            root_solution = Path(pylings.__file__).parent / "solutions" / relative_path

            if root_solution.exists():
                solution_path.parent.mkdir(parents=True, exist_ok=True)
                copy2(root_solution, solution_path)
                local_path = self.config_manager.get_local_solution_path(solution_path)
                return solution_path, local_path

            return None
        except Exception as e:
            log.error(f"Error resolving solution path: {e}")
            return None

    def get_exercise_path(self, path: Path, source: str = "workspace") -> Path:
        """Returns the absolute exercise path, resolving relative to workspace or package.

        Args:
            path (Path): A path that may or may not include 'exercises/' prefix.
            source (str): 'workspace' or 'package'.

        Returns:
            Path: Resolved absolute path to the exercise.

        Raises:
            FileNotFoundError: If the resolved file doesn't exist.
        """
        log.debug(f"ExerciseManager.get_exercise_path: path={path}, source={source}")
        try:            
            path_parts = list(path.parts)
            if path_parts[0] == "exercises":
                rel_parts = path_parts[path_parts.index('exercises') + 1:]
            else:
                rel_parts = path_parts

            rel_path = Path(*rel_parts)

            if source == "workspace":
                root = Path.cwd() / "exercises" / rel_path
                log.debug(f"ExerciseManager.get_exercise_path: root={root}")
            else:
                root = Path(pylings.__file__).parent / "exercises" / rel_path
                log.debug(f"ExerciseManager.get_exercise_path: root={root}")
            if not root.exists():
                log.error(f"ExerciseManager.get_exercise_path.fileNotFound: {path}")
                exit(1)
                #raise FileNotFoundError(f"Exercise not found: {path}")

            return root
        except Exception as e:
            log.error(f"get_exercise_path error: {e}")
            raise


    def run_and_print(self, path: Path, source: str = "workspace", type: str = "d"):
        """Runs or shows a solution for a specified path in CLI mode.

        Args:
            path (Path): Path to the exercise or solution.
            source (str): Context ("workspace" or "package").
            type (str): Mode - "d" for dry-run, "s" for solution.
        """
        if type == "d":
            path = self.get_exercise_path(path, source)
            result = self.run_exercise(path, source)
        elif type == "s":
            result = self.print_root_solution(path, source)

        output = result.stdout if result.returncode == 0 else result.stderr
        print(output)
        exit(0 if result.returncode == 0 else 1)


    def print_root_solution(self, path: Path, source: str = "package"):
        """Runs a solution file for a given exercise from the specified context.

        Args:
            path (Path): Path to the solution.
            source (str): "workspace" or "package"

        Returns:
            CompletedProcess: Execution result
        """
        log.debug(f"ExerciseManager.print_root_solution: path={path}, source={source}")


        path_parts = list(path.parts)
        if path_parts[0] == "exercises":
            path_parts[0] = "solutions"
        elif "solutions" not in path_parts:
            path_parts.insert(0, "solutions")

        if source == "workspace":
            root = Path.cwd().joinpath(*path_parts)
        else:
            root = Path(pylings.__file__).parent.joinpath(*path_parts)

        if not root.exists():
            log.error(f"Solution file not found: {root}")
            
            #raise FileNotFoundError(f"Solution not found: {path}")
            exit (1)
        return self.run_exercise(root, source)

    def reset_exercise_by_path(self, path: Path):
        """Reset a specific exercise given its path.

        Args:
            path (Path): Path to the exercise file to reset.
        """
        log.debug("ExerciseManager.reset_exercise_by_path: %s", path)
        path = path.resolve()
        exercises_dir = EXERCISES_DIR.resolve()

        if not path.exists():
            print(f"Exercise path not found: {path}")
            exit(1)

        if exercises_dir not in path.parents:
            print("Path must be under exercises/")
            exit(1)

        try:
            rel_path = path.relative_to(exercises_dir)
            log.debug("ExerciseManager.reset_exercise_by_path.rel_path: %s", rel_path)
        except ValueError:
            print("Path must be under exercises/")
            exit(1)

        backup_path = BACKUP_DIR / rel_path
        log.debug("ExerciseManager.reset_exercise_by_path.backup_path: %s", backup_path)
        if not backup_path.exists():
            print(f"No backup found for {rel_path}")
            exit(1)

        copy(backup_path, path)
        print(f"Reset exercise: {rel_path}")
        exit(0)


    def toggle_hint(self):
        """Toggles whether the hint for the current exercise should be displayed."""
        log.debug("ExerciseManager.toggle_hint")
        self.show_hint = not self.show_hint
# End-of-file (EOF)
