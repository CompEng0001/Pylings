# watcher.py
"""
File change watcher for Pylings.

This module wires up a robust, cross-platform watcher using `watchdog` to
monitor the *current exercise file* while scheduling events on its *parent
directory*. This design reliably captures editor "atomic save" operations
(temp file -> move over original) common on Windows and macOS.

Key features:
- Watches the parent directory; filters events to the single target file.
- Handles created/modified/moved/deleted (atomic save, delete→recreate).
- Case-insensitive path matching on Windows.
- Debounce + “settle” wait to avoid partial writes/locks.
- Optional fallback to PollingObserver for UNC/OneDrive/WSL mounts.
"""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from threading import Timer, RLock
from typing import Optional

from watchdog.events import FileSystemEventHandler, FileSystemEvent, FileMovedEvent
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver  # fallback for flaky FS (UNC/OneDrive/WSL)

log = logging.getLogger(__name__)


def _casefold_path(p: Path) -> str:
    """Return a canonical, case-insensitive absolute path string.

    On Windows, paths are case-insensitive; we use Path.resolve()+casefold()
    to ensure consistent comparisons. On non-Windows platforms this is still
    safe and deterministic.

    Args:
        p: Path to canonicalize.

    Returns:
        Canonical absolute path string suitable for equality comparisons.
    """
    try:
        return str(p.resolve()).casefold()
    except Exception:
        # Fall back to absolute() if resolve fails (e.g., temporarily missing).
        return str(p.absolute()).casefold()


def _stable_readable(p: Path, settle_ms: int = 250, timeout_ms: int = 1500) -> bool:
    """Wait until a file appears 'settled' before reading it.

    Some editors/AV/indexers hold a file open or write in chunks. This function
    polls (size, mtime_ns) until the signature stops changing or until timeout.

    Args:
        p: Target file path.
        settle_ms: Delay between successive probes, in milliseconds.
        timeout_ms: Maximum total wait time, in milliseconds.

    Returns:
        True if the file stabilized within the timeout, False otherwise.
    """
    deadline = time.monotonic() + (timeout_ms / 1000.0)
    last_sig = None
    while time.monotonic() < deadline:
        try:
            st = p.stat()
            sig = (st.st_size, st.st_mtime_ns)
        except OSError:
            time.sleep(settle_ms / 1000.0)
            continue
        if sig == last_sig:
            return True
        last_sig = sig
        time.sleep(settle_ms / 1000.0)
    return False


def _hash_with_retries(p: Path, retries: int = 5, delay_ms: int = 120) -> Optional[str]:
    """Compute a BLAKE2b hash of a file, retrying on transient access errors.

    Windows frequently has brief file locks during saves. We retry a few times
    with small delays to avoid spurious failures.

    Args:
        p: File to hash.
        retries: Number of open/read attempts.
        delay_ms: Delay between attempts, in milliseconds.

    Returns:
        Hex digest string (16-byte digest) or None if the file couldn't be read.
    """
    for _ in range(retries):
        try:
            with open(p, "rb") as f:
                return hashlib.blake2b(f.read(), digest_size=16).hexdigest()
        except OSError:
            time.sleep(delay_ms / 1000.0)
    return None


def _choose_observer(root: Path):
    """Select the most reliable watchdog observer for the given directory.

    Prefers the native OS observer, but chooses PollingObserver for locations
    known to be flaky with native events (UNC paths, OneDrive, WSL mounts).

    Args:
        root: Directory to watch.

    Returns:
        An initialized Observer-like instance (native or polling).
    """
    try:
        root_s = str(root.resolve())
    except Exception:
        root_s = str(root)
    if root_s.startswith("\\\\") or "OneDrive" in root_s or root_s.startswith("/mnt/"):
        log.info("Using PollingObserver for %s", root_s)
        return PollingObserver()
    try:
        return Observer()
    except Exception:
        log.warning("Falling back to PollingObserver")
        return PollingObserver()


class Watcher:
    """Manages file watching for Pylings exercises.

    Design:
        - We watch the *parent directory* of the current exercise, because many
          editors perform 'atomic saves' (write to temp -> move over target),
          which generate directory-level move/create events.
        - The handler filters incoming events so only the *current exercise file*
          triggers debounced updates.

    Attributes:
        exercise_manager: Backend manager coordinating exercise execution/state.
        ui_manager: UI controller (Textual) to request redraws (may be None).
        observer: Underlying watchdog observer instance.
        handler: Active ChangeHandler instance filtering events to the target file.
    """

    def __init__(self, exercise_manager, ui_manager):
        """Initialize the Watcher.

        Args:
            exercise_manager: The ExerciseManager instance.
            ui_manager: The UI manager (Textual App) or None in headless mode.
        """
        log.debug("Watcher.__init__: Entered")
        self.exercise_manager = exercise_manager
        self.ui_manager = ui_manager
        self.observer = None
        self.handler = None

    def start(self, exercise_path: str | Path = None):
        """Start watching the parent directory of the current exercise.

        The main entry in pylings passes `current_exercise.parent` here, but this
        method also resolves the current exercise from the manager as a fallback.

        Args:
            exercise_path: Directory path to watch. If omitted, uses the parent
                directory of the manager's current exercise.

        Side Effects:
            Creates and starts an underlying watchdog observer thread.
        """
        log.debug("Watcher.start: Entered")

        # Resolve current target file and its parent dir
        target_file = (Path(self.exercise_manager.current_exercise)
                       if self.exercise_manager.current_exercise else None)
        if exercise_path:
            p = Path(exercise_path).resolve()
            dir_to_watch = p if p.is_dir() else p.parent
        else:
            dir_to_watch = target_file.parent.resolve() if target_file else Path.cwd()

        if self.observer:
            self.stop()

        self.observer = _choose_observer(dir_to_watch)
        self.handler = self.ChangeHandler(self.exercise_manager, self.ui_manager)

        # Seed the handler with the current exercise file to track.
        if target_file:
            self.handler.set_target(target_file.resolve())

        log.debug("Watcher.start.dir_to_watch: %s", dir_to_watch)
        self.observer.schedule(self.handler, str(dir_to_watch), recursive=False)
        self.observer.start()

    def stop(self):
        """Stop and join the underlying observer thread, if running."""
        log.debug("Watcher.stop: Entered")
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            self.handler = None

    def restart(self, new_exercise_path: str | Path):
        """Restart watching when the user selects a different exercise.

        Args:
            new_exercise_path: Path to the *directory* containing the new exercise.

        Side Effects:
            Stops the current observer (if any) and starts a new one on the given path.
        """
        log.debug("Watcher.restart: stopping")
        self.stop()
        log.debug("Watcher.restart.new_exercise_path: %s", new_exercise_path)
        self.start(new_exercise_path)
        log.debug("Watcher.restart: started")

    class ChangeHandler(FileSystemEventHandler):
        """Directory-scoped handler that filters events to a single target file.

        Responsibilities:
            - Track the current exercise file path from the ExerciseManager.
            - React to created/modified/moved/deleted events that touch that file.
            - Debounce event bursts and wait for the file to settle.
            - Hash file contents and trigger UI/backend updates only on real changes.

        Threading:
            - Watchdog calls handlers from the observer thread.
            - A Timer is used for debouncing; updates are scheduled safely into the UI.
        """

        def __init__(self, exercise_manager, ui_manager):
            """Construct a ChangeHandler.

            Args:
                exercise_manager: ExerciseManager providing current_exercise and update hooks.
                ui_manager: UI object exposing call_from_thread(update_exercise_content), or None.
            """
            log.debug("ChangeHandler.__init__: Entered")
            self.exercise_manager = exercise_manager
            self.ui_manager = ui_manager

            self._target_path: Optional[Path] = None
            self._target_cf: Optional[str] = None
            self._last_hash: Optional[str] = None
            self.debounce_timer = None
            self._debounce_ms = 350
            self._timer: Optional[Timer] = None
            self._lock = RLock()

        # ----- target management -----
        def set_target(self, p: Path):
            """Set (or reset) the file we consider the 'current exercise' target.

            Seeds the baseline content hash so we only fire updates on real changes.

            Args:
                p: Absolute path to the exercise file to track.
            """
            self._target_path = p
            self._target_cf = _casefold_path(p)
            self._last_hash = _hash_with_retries(p)
            log.debug("ChangeHandler.set_target: %s", p)

        def _refresh_target_from_manager(self):
            """Update the target if the ExerciseManager switched exercises.

            This allows the watcher to adapt even if the observer wasn't restarted
            (we still restart in Pylings, but this keeps behavior robust).
            """
            try:
                cur = Path(self.exercise_manager.current_exercise).resolve()
            except Exception:
                return
            if self._target_path is None or _casefold_path(cur) != self._target_cf:
                self.set_target(cur)

        # ----- core helpers -----
        def _touches_target(self, src: str | None, dest: str | None) -> bool:
            """Check whether an event's src/dest path refers to the target file.

            Args:
                src: Source path from the event (may be None).
                dest: Destination path from the event (for moves; may be None).

            Returns:
                True if either path matches the target file; False otherwise.
            """
            if not self._target_path or not self._target_cf:
                return False
            if src and _casefold_path(Path(src)) == self._target_cf:
                return True
            if dest and _casefold_path(Path(dest)) == self._target_cf:
                return True
            return False

        def _schedule_debounced(self):
            """Schedule a debounced refresh after the last event in a burst."""
            with self._lock:
                if self._timer:
                    self._timer.cancel()
                self._timer = Timer(self._debounce_ms / 1000.0, self._on_debounced)
                self._timer.start()

        def _on_debounced(self):
            """After debounce delay, verify real content change and trigger updates.

            Steps:
                1) Ensure we are still targeting the current exercise.
                2) Wait for the file to 'settle' (size/mtime stable) to avoid partial reads.
                3) Re-hash contents; if the digest changed, re-run the exercise and refresh UI.
            """
            with self._lock:
                self._timer = None

            self._refresh_target_from_manager()
            if not self._target_path:
                return

            if not _stable_readable(self._target_path):
                log.debug("File did not settle in time; proceeding anyway")

            new_hash = _hash_with_retries(self._target_path)
            if not new_hash or new_hash == self._last_hash:
                return
            self._last_hash = new_hash

            # Trigger updates outside the lock.
            try:
                self.exercise_manager.update_exercise_output()
                if self.ui_manager:
                    # Textual-safe: schedule into the UI thread
                    self.ui_manager.call_from_thread(self.ui_manager.update_exercise_content)
            except Exception as e:
                log.exception("Update failed: %s", e)

        def _handle_file_change(self):
            """Performs the actual refresh of exercise output and UI content.
            Never raise out of this thread; log instead."""
            log.debug("ChangeHandler._handle_file_change: Triggered")
            try:
                self.exercise_manager.update_exercise_output()
            except (FileNotFoundError, PermissionError, OSError, RuntimeError, ValueError) as err:
                log.warning("update_exercise_output failed: %s", err, exc_info=True)
            # Guard UI scheduling separately so one failure doesn't mask the other
            try:
                if self.ui_manager:
                    self.ui_manager.call_from_thread(self.ui_manager.update_exercise_content)
            except (RuntimeError, AttributeError) as err:
                # Textual raises RuntimeError if app isn't ready
                log.warning("UI update scheduling failed: %s", err, exc_info=True)
            finally:
                self.state.timer = None

        # ----- event handlers -----
        def on_modified(self, event: FileSystemEvent):
            """Handle file content/metadata modifications.

            Args:
                event: Watchdog event describing the change.
            """
            if event.is_directory:
                return
            self._refresh_target_from_manager()
            if self._touches_target(getattr(event, "src_path", None),
                                    getattr(event, "dest_path", None)):
                self._schedule_debounced()

        def on_created(self, event: FileSystemEvent):
            """Handle file creations (e.g., delete→recreate sequences).

            Args:
                event: Watchdog event describing the creation.
            """
            if event.is_directory:
                return
            self._refresh_target_from_manager()
            if self._touches_target(getattr(event, "src_path", None), None):
                self._schedule_debounced()

        def on_moved(self, event: FileMovedEvent):
            """Handle file moves/renames (including atomic save temp→target).

            Args:
                event: Watchdog FileMovedEvent with src and dest paths.
            """
            if event.is_directory:
                return
            self._refresh_target_from_manager()
            if self._touches_target(getattr(event, "src_path", None),
                                    getattr(event, "dest_path", None)):
                self._schedule_debounced()

        def on_deleted(self, event: FileSystemEvent):
            """Handle file deletions.

            Some editors delete the old file and then create a new one with the
            same name/path. We treat deletion as a change trigger as well.

            Args:
                event: Watchdog event describing the deletion.
            """
            if event.is_directory:
                return
            self._refresh_target_from_manager()
            if self._touches_target(getattr(event, "src_path", None), None):
                self._schedule_debounced()
# End-of-file (EOF)
