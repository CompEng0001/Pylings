"""Textual-based UI for Pylings.

Provides a terminal-based interactive application for navigating, viewing, 
and interacting with Python exercises in the Pylings project. This UI is 
powered by the Textual framework and integrates with the ExerciseManager 
for backend state and logic.
"""
import logging
from pylings.constants import (DONE,DONE_MESSAGE, EXERCISES_DIR,EXERCISE_DONE,
                               EXERCISE_ERROR, EXERCISE_OUTPUT, LIST_VIEW,
                               LIST_VIEW_NEXT, MAIN_VIEW, MAIN_VIEW_NEXT, PENDING
)
from pylings.exercises import ExerciseManager
from pylings.utils import PylingsUtils

from rich.text import Text     
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.widgets import  ListView, ListItem, Static

log = logging.getLogger(__name__)

class PylingsUI(App):
    """Textual-based UI for Pylings.

    Manages the interactive terminal interface, including layout, navigation,
    exercise display, sidebar list, and user input handling. It integrates with 
    an ExerciseManager to coordinate updates and actions.
    """

    CSS_PATH = "./styles/ui.tcss"

    def __init__(self, exercise_manager: ExerciseManager):
        log.debug(f"PylingsUI.__init__: Entered")
        super().__init__()
        self.exercise_manager = exercise_manager
        self.current_exercise = self.exercise_manager.current_exercise
        self.list_focused = False
        self.sidebar_visible = False

    def compose(self) -> ComposeResult:
        """Build UI layout."""
        log.debug(f"PylingsUI.compose: Entered")
        yield Horizontal(
            Vertical(
                Static("", id="output"),
                Static("", id="hint"),
                Static("", id="progress-bar"),
                Static("Current exercise: ", id="exercise-path"),
                Static("", disabled=True, id="checking-all-exercises-status"),
                id="main"
            ),
            Vertical(
                Static("Status  Exercise"),
                ListView(*self.get_exercise_list(), id="exercise-list"),
                id="sidebar"
            ),
        )
        
        self.footer_hints = Static(MAIN_VIEW, id="footer-hints")
        self.footer_hints.visible = True
        yield self.footer_hints

    def on_mount(self):
        """Update UI with initial exercise details."""
        log.debug(f"PylingsUI.on_mount: Entered")
        self.update_exercise_content()
        sidebar = self.query_one("#sidebar", Vertical)
        main_content = self.query_one("#main", Vertical)

        sidebar.add_class("hidden")
        main_content.add_class("expanded")

        self.list_focused = False
        self.footer_hints.update(MAIN_VIEW)

    def get_exercise_list(self):
        """Generate exercise list for sidebar with updated status."""
        log.debug(f"PylingsUI.get_exercise_list: Entered")
        items = []
        for name, ex in self.exercise_manager.exercises.items():
            status = DONE if ex["status"] == "DONE" else PENDING
            items.append(ListItem(Static(f"{status} {name}")))
        log.debug(f"PylingsUI.get_exercise_list.items.len:\n\t {len(items)}")
        return items

    def refresh_exercise_output(self):
        """Reloads exercise output when file changes."""
        log.debug(f"PylingsUI.referesh_exercise_output: Entered")
        if not self.current_exercise:
            log.debug(f"PylingsUI.referesh_exercise_output.not.self.current_exercise: {self.current_exercise}")
            return
        output_widget = self.query_one("#output", Static)
        formatted_output = self.build_output()
        output_widget.update(formatted_output)

    def build_output(self):
        """Builds the exercise output for display in the UI."""
        log.debug(f"PylingsUI.build_output: Entered")
        if not self.current_exercise:
            log.debug(f"PylingsUI.build_output.not.self.current_exercise: {self.current_exercise}")
            return "No exercise selected."

        exercise_name = self.current_exercise.name if self.current_exercise.name else None
        if not exercise_name or exercise_name not in self.exercise_manager.exercises:
            log.debug(f"PylingsUI.referesh_exercise_output.not.self.exercise_name: {exercise_name}")
            return "Invalid exercise."

        ex_data = self.exercise_manager.exercises[exercise_name]

        if ex_data["status"] == "DONE":
            full_solution_path, short_path = self.exercise_manager.get_solution()
            git_status = PylingsUtils.get_git_status()
            lines = [
                f"\n{EXERCISE_OUTPUT(ex_data['output'])}",
                f"\n\n{EXERCISE_DONE}",
                f"\n{self.solution_link(full_solution_path,short_path)}",
                f"\n\n{DONE_MESSAGE}",
                f"\n{PylingsUtils.git_suggestion(git_status)}"
            ]
            self.exercise_manager.show_hint = False
            self.query_one("#hint", Static).update("")
            return ''.join(lines)

        else:
            error_message = f"{EXERCISE_ERROR(ex_data['error'])}"
            if self.exercise_manager.show_hint:
                error_message += f"\n{ex_data.get('hint', '')}\n"

        return error_message

    def solution_link(self, full_path, short_path):
        """Generate a rich Text link to the provided solution file path.

        Args:
            full_path (Path): Absolute path to the solution file.
            short_path (Path): Relative path from the solutions directory.

        Returns:
            Text: A formatted clickable Textual-rich link.
        """
        log.debug(f"PylingsUI.solution_link: Entered")
        log.debug(f"PylingsUI.solution_link.full_path: {full_path}")
        log.debug(f"PylingsUI.solution_link.short_path: {short_path}")
        return PylingsUtils.make_link(short_path, full_path, "solutions", "Solution for comparison: ")

    def exercise_link(self, full_path):
        """Generate a rich Text link to the current exercise file.

        Args:
            full_path (Path): Absolute path to the exercise file.

        Returns:
            Text: A formatted clickable Textual-rich link.
        """
        log.debug(f"PylingsUI.exercise_link: Entered")
        short_path = full_path.relative_to(EXERCISES_DIR)
        log.debug(f"PylingsUI.exercise_link.full_path: {full_path}")
        log.debug(f"PylingsUI.solution_link.short_path: {short_path}")
        return PylingsUtils.make_link(str(short_path), full_path, "exercises", "Current exercise: ")

    def update_progress_bar(self):
        """Generate a Rustlings-style text progress bar inside Static.""" 
        log.debug(f"PylingsUI.update_progress_bar: Entered")
        progress_bar_widget = self.query_one("#progress-bar", Static)
        
        total_exercises = len(self.exercise_manager.exercises)
        completed_exercises = self.exercise_manager.completed_count

        bar_length = 55
        progress_fraction = completed_exercises / total_exercises if total_exercises > 0 else 0

        filled = int(progress_fraction * bar_length)
        remaining = bar_length - filled - 1 

        progress_bar = Text("Progress: [", style="bold")
        progress_bar.append("#" * filled, style="green")
        progress_bar.append(">", style="green")
        progress_bar.append("-" * remaining, style="red")
        progress_bar.append(f"]   {completed_exercises}/{total_exercises}", style="bold")
        log.debug(f"PylingsUI.update_progress_bar.progress_bar: {progress_bar}")
        progress_bar_widget.update(progress_bar)

    def update_check_progress(self, exercise_name, completed, total):
        """Update the UI to show checking progress."""
        log.debug(f"PylingsUI.update_check_progress: Entered")
        check_progress_widget = self.query_one("#checking-all-exercises-status", Static)
        check_progress_widget.update("Checking all exercises")
        if exercise_name:
            log.debug(f"PylingsUI.update_update_progress.exercise_name: {exercise_name} {completed}/{total-1}")
            check_progress_widget.update(f"Checking exercise: {completed}/{total-1 } {exercise_name}")
        #self.refresh()

    def finished_check_progress_notice(self, clear=False):
        """Display or clear the 'finished checking all exercises' notice.

        Args:
            clear (bool): Whether to clear the message instead of showing it.
        """
        log.debug(f"PylingsUI.finished_check_progress_notice: Entered")
        check_progress_widget = self.query_one("#checking-all-exercises-status", Static)
        if clear:
            check_progress_widget.update("")
            log.debug(f"PylingsUI.finished_check_progress_notice.clear: true")
        else:
            check_progress_widget.update("Finished checking all exercises")
            log.debug(f"PylingsUI.finished_check_progress_notice: Finished checking all exercises")

    def toggle_list_view(self):
        """Toggle the visibility of the exercise list view while preserving selection."""
        log.debug(f"PylingsUI.toggle_list_view: Entered")
        sidebar = self.query_one("#sidebar", Vertical)
        main_content = self.query_one("#main", Vertical)
        list_view = self.query_one("#exercise-list", ListView)

        selected_index = list_view.index if list_view.index is not None else 0
        if "hidden" in sidebar.classes:
            sidebar.remove_class("hidden")
            main_content.remove_class("expanded")

            if 0 <= selected_index < len(list_view.children):
                list_view.index = selected_index
                list_view.scroll_visible(list_view.children[selected_index])
                
            self.list_focused = True
            self.sidebar_visible = True
            
            self.footer_hints.update(self.view_options())
    
        else:
            sidebar.add_class("hidden")
            main_content.add_class("expanded")
            self.list_focused = False
            self.sidebar_visible = False
            self.footer_hints.update(self.view_options())
        
        log.debug(f"PylingsUI.toggle_list_view.sidebar.classes: {sidebar.classes}")
        log.debug(f"PylingsUI.toggle_list_view.sidebar.selected_index: {selected_index}")

    def update_exercise_content(self):
        """Update displayed exercise details, refresh output, and efficiently update the list."""
        log.debug("PylingsUI.update_exercise_content: Entered")

        exercise_path = self.current_exercise or "No exercise selected"
        self.query_one("#exercise-path", Static).update(f"{self.exercise_link(exercise_path)}")

        self.refresh_exercise_output()
        self.footer_hints.update(self.view_options())
        self.update_progress_bar()

        list_view = self.query_one("#exercise-list", ListView)
        selected_index = list_view.index or 0
        self.update_list_row(selected_index)
        self.restore_list_selection(selected_index)

        # Show completion notice briefly
        self.finished_check_progress_notice(clear=False)
        self.set_timer(2.0, lambda: self.finished_check_progress_notice(clear=True))

    def update_list_row(self, index: int):
        """Update the display text for the exercise at the given index in the list.

        If the exercise status has changed, the line is updated accordingly.

        Args:
            index (int): Index of the exercise to update.
        """
        list_view = self.query_one("#exercise-list", ListView)
        exercise_keys = list(self.exercise_manager.exercises.keys())

        if 0 <= index < len(exercise_keys):
            name = exercise_keys[index]
            new_status = DONE if self.exercise_manager.exercises[name]["status"] == "DONE" else PENDING
            new_display = f"{new_status} {name}"

            list_item = list_view.children[index]
            static_widget = list_item.query_one(Static)
            current_display = static_widget.renderable.plain if hasattr(static_widget.renderable, 'plain') else str(static_widget.renderable)

            if current_display != new_display:
                log.debug(f"Updating line {index}: {current_display} -> {new_display}")
                static_widget.update(new_display)

    def restore_list_selection(self, index: int):
        """Restore focus and visibility for the given list item index.

        Args:
            index (int): The index of the exercise to reselect in the list view.
        """
        list_view = self.query_one("#exercise-list", ListView)
        if 0 <= index < len(list_view.children):
            list_view.index = index
            list_view.scroll_visible(list_view.children[index])
            self.set_focus(list_view)
            list_view.refresh(layout=True)

    def view_options(self):
        """Return appropriate footer hint based on sidebar state and exercise status.

        Returns:
            str: A string constant such as LIST_VIEW, MAIN_VIEW_NEXT, etc.
        """
        log.debug(f"PylingsUI.view_options: Entered")
        log.debug(f"PylingsUI.view_options.self.sidebar_visible: {self.sidebar_visible}")
        log.debug(f"PylingsUI.view_options.self.exercise_manager.current_exercise_state: {self.exercise_manager.current_exercise_state}")

        options = {
            (True, "DONE"): LIST_VIEW_NEXT,
            (True, "PENDING"): LIST_VIEW,
            (False, "DONE"): MAIN_VIEW_NEXT,
            (False, "PENDING"): MAIN_VIEW,
        }
        return options.get((self.sidebar_visible, self.exercise_manager.current_exercise_state), MAIN_VIEW)

    def on_key(self, event: Key) -> None:
        """Handle global key bindings and interactions for the UI.

        Handles commands such as quitting, navigating exercises, showing hints,
        and toggling the sidebar.

        Args:
            event (Key): The key press event triggered by the user.
        """
        log.debug(f"PylingsUI.on_key: Entered")
        log.debug(f"PylingsUI.on_key.event.key: {event.key}")
        if event.key == "q":
            self.exit()

        elif event.key == "n":
            if self.exercise_manager.current_exercise_state == "DONE":
                self.exercise_manager.next_exercise()
                self.current_exercise = self.exercise_manager.current_exercise
                self.exercise_manager.show_hint = False
                self.query_one("#hint", Static).update("")
                self.update_exercise_content()

        elif event.key == "r":
            self.exercise_manager.reset_exercise()
            self.update_exercise_content()

        elif event.key == "h":
            self.exercise_manager.toggle_hint()
            hint = self.exercise_manager.exercises[self.current_exercise.name]["hint"] if self.exercise_manager.show_hint else ""
            self.query_one("#hint", Static).update(hint)

        elif event.key == "l":
            self.toggle_list_view()
            self.finished_check_progress_notice(True)
            event.key = "tab"

        elif self.list_focused and event.key in ("up", "down", "end", "home", "c", "s"):
            list_view = self.query_one("#exercise-list", ListView)
            if event.key == "end":
                list_view.index = len(list_view.children) - 1
            elif event.key == "home":
                list_view.index = 0

            elif event.key == "s":
                selected_index = list_view.index
                if selected_index is not None:
                    exercise_keys = list(self.exercise_manager.exercises.keys())
                    new_exercise_name = exercise_keys[selected_index]
                    new_exercise = self.exercise_manager.exercises[new_exercise_name]["path"]
                    self.exercise_manager.current_exercise = new_exercise
                    self.current_exercise = new_exercise
                    self.exercise_manager.config_manager.set_lasttime_exercise(new_exercise)
                    self.exercise_manager.current_exercise_state = self.exercise_manager.exercises[new_exercise_name]["status"]
                    self.exercise_manager.show_hint = False
                    self.query_one("#hint", Static).update("")
                    self.update_exercise_content()
                    self.update_list_row(selected_index)
                    self.restore_list_selection(selected_index)


                    if self.exercise_manager.watcher:
                        self.exercise_manager.watcher.restart(str(new_exercise.parent))

            elif event.key == "c":
                self.exercise_manager.check_all_exercises(progress_callback=self.update_check_progress)
                self.finished_check_progress_notice(False)
                self.update_exercise_content()


if __name__ == "__main__":
    exercise_manager = ExerciseManager()
    app = PylingsUI(exercise_manager)
    app.run()