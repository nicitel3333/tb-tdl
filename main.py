from datetime import date, timedelta
from textual.app import App, ComposeResult
from textual.widgets import Label, Input, TextArea
from textual.containers import VerticalScroll, Horizontal
from pathlib import Path
from src.app import load_tasks, save_tasks, Task, load_state, save_state
from src.config import load_config, create_default_config, to_textual_key
import calendar
from src.sync import sync, push_task, update_task, delete_task, close_task, reopen_task

class TdlApp(App):
    BINDINGS = []
    LAYERS = ["default", "overlay"]

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
    #help-panel {
        display: none;
        width: 100%;
        height: 100%;
        border: solid $accent;
        background: $surface;
        layer: overlay;
        padding: 1 2;
    }
    #help-cols {
        height: auto;
    }
    #help-col-left {
        width: 1fr;
    }
    #help-col-right {
        width: 1fr;
    }
    """

    def __init__(self):
        super().__init__()
        self.config = load_config()
        kb = self.config["keybinds"]
        for key in kb:
            kb[key] = to_textual_key(kb[key])
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
        with VerticalScroll(id="help-panel"):
            pass

    def on_mount(self) -> None:
        self.current_index = 0
        self._panel_open = False
        self._help_open = False
        self._help_rendered = False
        self._setting_date = False
        self._setting_time = False
        self._editing_title = False
        self._editing_description = False
        self._calendar_mode = False
        self._cal_cursor = date.today()
        self._sort_mode = load_state().get("sort_mode", 0)
        self.tasks = load_tasks()
        self.do_sync()
        self.refresh_list()
        self.query_one("#task-list").focus()

    def do_sync(self) -> None:
        api_key = self.config["todoist"]["api_key"]
        if not api_key:
            return
        try:
            self.tasks = sync(api_key, self.tasks)
            save_tasks(self.tasks)
            self.refresh_list()
        except Exception:
            pass

    def _api_key(self) -> str | None:
        key = self.config["todoist"]["api_key"]
        return key if key else None

    def refresh_list(self) -> None:
        container = self.query_one("#task-list", VerticalScroll)
        container.remove_children()
        today = date.today()
        if self._sort_mode == 1:
            self.tasks.sort(key=lambda t: t.due_date or "9999")
        elif self._sort_mode == 2:
            self.tasks.sort(key=lambda t: t.priority)
        tasks = self.tasks
        col_w = max((len(t.title) for t in tasks), default=30)
        col_w = max(col_w, 30)
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
            if task.due_date:
                if "T" in task.due_date:
                    date_part, time_part = task.due_date.split("T")
                    dd_mm = "/".join(reversed(date_part[5:].split("-")))
                    due = f"{dd_mm} {time_part}"
                else:
                    due = "/".join(reversed(task.due_date[5:].split("-")))
            else:
                due = "xxx"
            pri = task.priority if task.priority is not None else "xxx"
            line = f"{status} {task.title:<{col_w}} {due:<18} {pri}"
            if task.due_date:
                task_date = date.fromisoformat(task.due_date[:10])
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

    def action_set_time(self) -> None:
        if self.tasks:
            self.query_one("#task-input").placeholder = "Time (HH:MM)..."
            self.query_one("#task-input").focus()
            self._setting_time = True

    def action_remove_date(self) -> None:
        if self.tasks:
            task = self.tasks[self.current_index]
            task.due_date = None
            save_tasks(self.tasks)
            api_key = self._api_key()
            if api_key and task.todoist_id:
                try:
                    update_task(api_key, task)
                except Exception:
                    pass
            self.refresh_list()

    def action_remove_time(self) -> None:
        if self.tasks:
            task = self.tasks[self.current_index]
            if task.due_date and "T" in task.due_date:
                task.due_date = task.due_date[:10]
                save_tasks(self.tasks)
                api_key = self._api_key()
                if api_key and task.todoist_id:
                    try:
                        update_task(api_key, task)
                    except Exception:
                        pass
                self.refresh_list()

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

    def action_toggle_panel(self) -> None:
        if self._panel_open:
            self._panel_open = False
            self._calendar_mode = False
            self.query_one("#right-panel").styles.display = "none"
        else:
            self._panel_open = True
            self.query_one("#right-panel").styles.display = "block"
            self.refresh_description()
            self.render_calendar()

    def action_toggle_help(self) -> None:
        if self._help_open:
            self._help_open = False
            self.query_one("#help-panel").styles.display = "none"
        else:
            self._help_open = True
            self.query_one("#help-panel").styles.display = "block"
            if not self._help_rendered:
                self.render_help()
                self._help_rendered = True

    def render_calendar(self) -> None:
        panel = self.query_one("#calendar-panel")
        panel.remove_children()
        today = date.today()
        cursor = self._cal_cursor
        year, month = cursor.year, cursor.month
        cal = calendar.monthcalendar(year, month)
        panel.mount(Label(cursor.strftime('%B %Y'), markup=False))
        panel.mount(Label("", markup=False))
        panel.mount(Label("Mo  Tu  We  Th  Fr  Sa  Su", markup=False))
        panel.mount(Label("", markup=False))
        for week in cal:
            parts = []
            for day in week:
                if day == 0:
                    parts.append("    ")
                else:
                    d = date(year, month, day)
                    if self._calendar_mode and d == cursor:
                        parts.append(f"[bold green]{day:2}[/bold green]  ")
                    elif d == today:
                        parts.append(f"[yellow]{day:2}[/yellow]  ")
                    else:
                        parts.append(f"{day:2}  ")
            panel.mount(Label("".join(parts), markup=True))
        if self._calendar_mode:
            panel.mount(Label("", markup=False))
            panel.mount(Label("[dim]enter: select   esc: cancel[/dim]", markup=True))

    def render_help(self) -> None:
        panel = self.query_one("#help-panel")
        k = self.config["keybinds"]
        panel.mount(Label("[bold cyan]KEYBINDS[/bold cyan]", markup=True))
        panel.mount(Label("", markup=True))
        bindings = [
            (k["add_task"], "Add task"),
            (k["move_up"], "Move up"),
            (k["move_down"], "Move down"),
            (k["toggle_done"], "Toggle done"),
            (k["delete_task"], "Delete task"),
            (k["cycle_priority"], "Cycle priority"),
            (k["set_date"], "Set date"),
            (k["remove_date"], "Remove date"),
            (k["set_time"], "Set time"),
            (k["remove_time"], "Remove time"),
            (k["edit_title"], "Edit title"),
            (k["toggle_panel"], "Toggle panel"),
            (k["cycle_sort"], "Cycle sort"),
            (k["sync"], "Sync"),
            (k["toggle_help"], "Toggle help"),
            (k["quit"], "Quit"),
            (k["toggle_calendar"], "Control calendar"),
        ]
        mid = (len(bindings) + 1) // 2
        left_labels = [Label(f"[bold]{key:8}[/bold] {desc}", markup=True) for key, desc in bindings[:mid]]
        right_labels = [Label(f"[bold]{key:8}[/bold] {desc}", markup=True) for key, desc in bindings[mid:]]
        left_col = VerticalScroll(*left_labels, id="help-col-left")
        right_col = VerticalScroll(*right_labels, id="help-col-right")
        panel.mount(Horizontal(left_col, right_col, id="help-cols"))

    def action_toggle_calendar_mode(self) -> None:
        if not self._panel_open:
            return
        self._calendar_mode = not self._calendar_mode
        if self._calendar_mode:
            task = self.tasks[self.current_index] if self.tasks else None
            if task and task.due_date:
                self._cal_cursor = date.fromisoformat(task.due_date[:10])
            else:
                self._cal_cursor = date.today()
        self.render_calendar()

    def action_cal_select(self) -> None:
        if self.tasks:
            task = self.tasks[self.current_index]
            task.due_date = self._cal_cursor.isoformat()
            save_tasks(self.tasks)
            api_key = self._api_key()
            if api_key and task.todoist_id:
                try:
                    update_task(api_key, task)
                except Exception:
                    pass
        self._calendar_mode = False
        self.render_calendar()
        self.refresh_list()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        api_key = self._api_key()
        if self._setting_date:
            self._setting_date = False
            self.query_one("#task-input").placeholder = "New task..."
            if value and self.tasks:
                try:
                    day, month = value.split("/")
                    year = date.today().year
                    self.tasks[self.current_index].due_date = f"{year}-{int(month):02d}-{int(day):02d}"
                    save_tasks(self.tasks)
                    if api_key and self.tasks[self.current_index].todoist_id:
                        try:
                            update_task(api_key, self.tasks[self.current_index])
                        except Exception:
                            pass
                except ValueError:
                    pass
            self.refresh_list()
            self.query_one("#task-list").focus()
        elif self._setting_time:
            self._setting_time = False
            self.query_one("#task-input").placeholder = "New task..."
            if value and self.tasks:
                task = self.tasks[self.current_index]
                parts = value.replace(":", "").ljust(4, "0")
                hh = parts[:2].zfill(2)
                mm = parts[2:4].zfill(2)
                time_str = f"{hh}:{mm}"
                date_part = task.due_date[:10] if task.due_date else date.today().isoformat()
                task.due_date = f"{date_part}T{time_str}"
                save_tasks(self.tasks)
                if api_key and task.todoist_id:
                    try:
                        update_task(api_key, task)
                    except Exception:
                        pass
            self.refresh_list()
            self.query_one("#task-list").focus()
        elif self._editing_title:
            self._editing_title = False
            self.query_one("#task-input").placeholder = "New task..."
            if value and self.tasks:
                self.tasks[self.current_index].title = value
                save_tasks(self.tasks)
                if api_key and self.tasks[self.current_index].todoist_id:
                    try:
                        update_task(api_key, self.tasks[self.current_index])
                    except Exception:
                        pass
            self.refresh_list()
            event.input.value = ""
            self.query_one("#task-list").focus()
        else:
            if value:
                task = Task(id=len(self.tasks) + 1, title=value)
                if api_key:
                    try:
                        task.todoist_id = push_task(api_key, task)
                    except Exception:
                        pass
                self.tasks.append(task)
                self.current_index = len(self.tasks) - 1
                save_tasks(self.tasks)
                self.refresh_list()
                event.input.value = ""
            self.query_one("#task-list").focus()

    def on_key(self, event) -> None:
        k = self.config["keybinds"]
        if event.key == "escape":
            if self._calendar_mode:
                self._calendar_mode = False
                self.render_calendar()
            elif self._help_open:
                self._help_open = False
                self.query_one("#help-panel").styles.display = "none"
            elif self._editing_description:
                self._editing_description = False
                self.query_one("#desc-editor").styles.display = "none"
                self.query_one("#desc-label").styles.display = "block"
            else:
                self._setting_date = False
                self._setting_time = False
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
                api_key = self._api_key()
                if api_key and self.tasks[self.current_index].todoist_id:
                    try:
                        update_task(api_key, self.tasks[self.current_index])
                    except Exception:
                        pass
            self._editing_description = False
            editor.styles.display = "none"
            self.refresh_description()
            self.query_one("#desc-label").styles.display = "block"
            self.query_one("#task-list").focus()
            event.prevent_default()
            event.stop()
        elif self._calendar_mode and event.key in ("h", "l", "j", "k", "enter"):
            if event.key == "h":
                self._cal_cursor -= timedelta(days=1)
            elif event.key == "l":
                self._cal_cursor += timedelta(days=1)
            elif event.key == "k":
                self._cal_cursor -= timedelta(weeks=1)
            elif event.key == "j":
                self._cal_cursor += timedelta(weeks=1)
            elif event.key == "enter":
                self.action_cal_select()
            if event.key != "enter":
                self.render_calendar()
            event.prevent_default()
            event.stop()
        elif event.key == k["toggle_calendar"] and self._panel_open and not self._editing_description:
            self.action_toggle_calendar_mode()
            event.prevent_default()
            event.stop()
        elif event.key == k["toggle_help"]:
            self.action_toggle_help()
            event.prevent_default()
            event.stop()
        elif event.key == k["add_task"] and not self._editing_description and not self._setting_date and not self._setting_time and not self._editing_title:
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
                k["set_time"]: self.action_set_time,
                k["remove_date"]: self.action_remove_date,
                k["remove_time"]: self.action_remove_time,
                k["edit_title"]: self.action_edit_title,
                k["toggle_panel"]: self.action_toggle_panel,
                k["cycle_sort"]: self.action_cycle_sort,
                k["sync"]: self.do_sync,
            }
            if event.key in actions and not self._editing_description and not self._setting_date and not self._setting_time and not self._editing_title and not self._calendar_mode:
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
            api_key = self._api_key()
            if api_key and task.todoist_id:
                try:
                    close_task(api_key, task.todoist_id) if task.done else reopen_task(api_key, task.todoist_id)
                except Exception:
                    pass
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
            api_key = self._api_key()
            if api_key and task.todoist_id:
                try:
                    delete_task(api_key, task.todoist_id)
                except Exception:
                    pass
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
            api_key = self._api_key()
            if api_key and task.todoist_id:
                try:
                    update_task(api_key, task)
                except Exception:
                    pass
            self.refresh_list()

    def action_cycle_sort(self) -> None:
        self._sort_mode = (self._sort_mode + 1) % 3
        save_state({"sort_mode": self._sort_mode})
        self.refresh_list()

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._setting_date:
            val = event.value
            if len(val) == 2 and val.isdigit():
                event.input.value = val + "/"
                event.input.cursor_position = 3
        elif self._setting_time:
            val = event.value.replace(":", "")
            if len(val) >= 2 and ":" not in event.value:
                event.input.value = val[:2] + ":" + val[2:]
                event.input.cursor_position = len(event.input.value)

    def action_quit(self) -> None:
        self.do_sync()
        self.exit()

def main():
    app = TdlApp()
    app.run()

if __name__ == "__main__":
    main()
