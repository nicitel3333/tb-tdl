from datetime import date, timedelta
from textual.app import App, ComposeResult
from textual.widgets import Label, Input, TextArea
from textual.containers import VerticalScroll, Horizontal
from pathlib import Path
from src.app import load_tasks, save_tasks, Task
from src.config import load_config, create_default_config
import calendar
from src.sync import sync

class TdlApp(App):
    BINDINGS = []

    CSS = """
    #main {
        height: 1fr;
    }
    #task-list {
        width: 1fr;
        border-right: solid $primary;
    }
    #right-panel {
        width: 1fr;
        display: none;
    }
    #description-panel {
        height: 1fr;
        border-bottom: solid $primary;
    }
    #calendar-panel {
        height: 1fr;
    }
    #desc-editor {
        display: none;
        height: 1fr;
    }
    """

    def __init__(self):
        super().__init__()
        self.config = load_config()
        if not (Path.home() / ".config" / "tb-tdl" / "config.ini").exists():
            create_default_config()

    def compose(self) -> ComposeResult:
        yield Input(placeholder="New task...", id="task-input")
        with Horizontal(id="main"):
            yield VerticalScroll(id="task-list")
            with VerticalScroll(id="right-panel"):
                with VerticalScroll(id="description-panel"):
                    yield Label("Add description here...", id="desc-label", markup=True)
                    yield TextArea(id="desc-editor")
                yield VerticalScroll(id="calendar-panel")

    def on_mount(self) -> None:
        self.current_index = 0
        self._panel_open = False
        self._setting_date = False
        self._editing_title = False
        self._editing_description = False
        self._sort_mode = 0
        self.tasks = load_tasks()
        api_key = self.config["todoist"]["api_key"]
        if api_key:
            try:
                self.tasks = sync(api_key, self.tasks)
                save_tasks(self.tasks)
            except Exception:
                pass
        self.refresh_list()
        self.query_one("#task-list").focus()

    def refresh_list(self) -> None:
        container = self.query_one("#task-list", VerticalScroll)
        container.remove_children()
        today = date.today()
        tasks = self.tasks[:]
        if self._sort_mode == 1:
            tasks.sort(key=lambda t: t.due_date or "9999")
        elif self._sort_mode == 2:
            tasks.sort(key=lambda t: t.priority)
        for i, task in enumerate(tasks):
            selected = self.current_index == i
            if selected and task.done:
                status = "\\[X]"
            elif selected:
                status = "\\[*]"
            elif task.done:
                status = "\\[x]"
            else:
                status = "\\[ ]"
            due = "/".join(reversed(task.due_date[5:].split("-"))) if task.due_date else "xxx"
            pri = task.priority if task.priority is not None else "xxx"
            line = f"{status} {task.title:<30} {due:<12} {pri}"
            if task.due_date:
                task_date = date.fromisoformat(task.due_date)
                if task_date < today:
                    color = self.config["colors"]["overdue"]
                    line = f"[{color}]{line}[/{color}]"
                elif task_date == today:
                    color = self.config["colors"]["today"]
                    line = f"[{color}]{line}[/{color}]"
                elif task_date == today + timedelta(days=1):
                    color = self.config["colors"]["tomorrow"]
                    line = f"[{color}]{line}[/{color}]"
            container.mount(Label(line, markup=True))

    def refresh_description(self) -> None:
        label = self.query_one("#desc-label")
        if self.tasks:
            desc = self.tasks[self.current_index].description or "Add description here..."
        else:
            desc = "Add description here..."
        label.update(desc)

    def action_add_task(self) -> None:
        self.query_one("#task-input").focus()

    def action_set_date(self) -> None:
        if self.tasks:
            self.query_one("#task-input").placeholder = "Due date (dd/mm)..."
            self.query_one("#task-input").focus()
            self._setting_date = True

    def action_edit_title(self) -> None:
        if self.tasks:
            inp = self.query_one("#task-input")
            inp.placeholder = "Edit title..."
            inp.value = self.tasks[self.current_index].title
            inp.focus()
            inp.cursor_position = len(inp.value)
            self._editing_title = True

    def action_edit_description(self) -> None:
        if self.tasks:
            editor = self.query_one("#desc-editor", TextArea)
            desc = self.tasks[self.current_index].description or ""
            editor.load_text(desc)
            editor.styles.display = "block"
            self.query_one("#desc-label").styles.display = "none"
            editor.focus()
            editor.move_cursor(editor.document.end)
            self._editing_description = True

    def action_open_panel(self) -> None:
        self._panel_open = True
        self.query_one("#right-panel").styles.display = "block"
        self.refresh_description()
        self.render_calendar()

    def action_close_panel(self) -> None:
        self._panel_open = False
        self.query_one("#right-panel").styles.display = "none"

    def render_calendar(self) -> None:
        panel = self.query_one("#calendar-panel")
        panel.remove_children()
        today = date.today()
        cal = calendar.monthcalendar(today.year, today.month)
        panel.mount(Label(f"{today.strftime('%B %Y'):^41}", markup=True))
        panel.mount(Label("", markup=True))
        panel.mount(Label(f"{'Mo   Tu   We   Th   Fr   Sa   Su':^41}", markup=True))
        panel.mount(Label("", markup=True))
        for week in cal:
            row = ""
            for day in week:
                if day == 0:
                    row += "      "
                elif day == today.day:
                    row += f"[{day:2}]  "
                else:
                    row += f" {day:2}   "
            panel.mount(Label(f"{row:^35}", markup=False))
            panel.mount(Label("", markup=False))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if self._setting_date:
            self._setting_date = False
            self.query_one("#task-input").placeholder = "New task..."
            if value and self.tasks:
                try:
                    day, month = value.split("/")
                    year = date.today().year
                    self.tasks[self.current_index].due_date = f"{year}-{int(month):02d}-{int(day):02d}"
                    save_tasks(self.tasks)
                except ValueError:
                    pass
            self.refresh_list()
            self.query_one("#task-list").focus()
        elif self._editing_title:
            self._editing_title = False
            self.query_one("#task-input").placeholder = "New task..."
            if value and self.tasks:
                self.tasks[self.current_index].title = value
                save_tasks(self.tasks)
            self.refresh_list()
            event.input.value = ""
            self.query_one("#task-list").focus()
        else:
            if value:
                task = Task(id=len(self.tasks) + 1, title=value)
                self.tasks.append(task)
                self.current_index = len(self.tasks) - 1
                save_tasks(self.tasks)
                self.refresh_list()
                event.input.value = ""
            self.query_one("#task-list").focus()

    def on_key(self, event) -> None:
        k = self.config["keybinds"]
        if event.key == "escape":
            if self._editing_description:
                self._editing_description = False
                self.query_one("#desc-editor").styles.display = "none"
                self.query_one("#desc-label").styles.display = "block"
            else:
                self._setting_date = False
                self._editing_title = False
                inp = self.query_one("#task-input")
                inp.value = ""
                inp.placeholder = "New task..."
            self.query_one("#task-list").focus()
            event.prevent_default()
            event.stop()
        elif event.key == "ctrl+s" and self._editing_description:
            editor = self.query_one("#desc-editor", TextArea)
            desc = editor.text.strip() or None
            if self.tasks:
                self.tasks[self.current_index].description = desc
                save_tasks(self.tasks)
            self._editing_description = False
            editor.styles.display = "none"
            self.refresh_description()
            self.query_one("#desc-label").styles.display = "block"
            self.query_one("#task-list").focus()
            event.prevent_default()
            event.stop()
        elif event.key == k["add_task"] and not self._editing_description and not self._setting_date and not self._editing_title:
            if self._panel_open:
                self.action_edit_description()
            else:
                self.action_add_task()
            event.prevent_default()
            event.stop()
        else:
            actions = {
                k["move_down"]: self.action_move_down,
                k["move_up"]: self.action_move_up,
                k["quit"]: self.app.exit,
                k["toggle_done"]: self.action_toggle_done,
                k["delete_task"]: self.action_delete_task,
                k["cycle_priority"]: self.action_cycle_priority,
                k["set_date"]: self.action_set_date,
                k["edit_title"]: self.action_edit_title,
                k["open_panel"]: self.action_open_panel,
                k["close_panel"]: self.action_close_panel,
                k["cycle_sort"]: self.action_cycle_sort,
            }
            if event.key in actions and not self._editing_description and not self._setting_date and not self._editing_title:
                actions[event.key]()
                event.prevent_default()
                event.stop()

    def action_move_down(self) -> None:
        if self.current_index < len(self.tasks) - 1:
            self.current_index += 1
            self.refresh_list()
            if self._panel_open:
                self.refresh_description()

    def action_move_up(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            self.refresh_list()
            if self._panel_open:
                self.refresh_description()

    def action_toggle_done(self) -> None:
        if self.tasks:
            task = self.tasks[self.current_index]
            task.done = not task.done
            self.tasks.pop(self.current_index)
            if task.done:
                self.tasks.append(task)
                self.current_index = min(self.current_index, len(self.tasks) - 1)
            else:
                self.tasks.insert(self.current_index, task)
            save_tasks(self.tasks)
            self.refresh_list()

    def action_delete_task(self) -> None:
        if self.tasks:
            task = self.tasks[self.current_index]
            if not task.done:
                return
            self.tasks.pop(self.current_index)
            if self.current_index >= len(self.tasks):
                self.current_index = max(0, len(self.tasks) - 1)
            save_tasks(self.tasks)
            self.refresh_list()

    def action_cycle_priority(self) -> None:
        if self.tasks:
            task = self.tasks[self.current_index]
            task.priority = (task.priority % 4) + 1
            save_tasks(self.tasks)
            self.refresh_list()

    def action_cycle_sort(self) -> None:
        self._sort_mode = (self._sort_mode + 1) % 3
        self.refresh_list()

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._setting_date:
            val = event.value
            if len(val) == 2 and val.isdigit():
                event.input.value = val + "/"
                event.input.cursor_position = 3

    def action_quit(self) -> None:
        api_key = self.config["todoist"]["api_key"]
        if api_key:
            try:
                sync(api_key, self.tasks)
                save_tasks(self.tasks)
            except Exception:
                pass
            self.exit()

def main():
    app = TdlApp()
    app.run()

if __name__ == "__main__":
    main()
