from textual.app import App, ComposeResult
from textual.widgets import Label, Input
from textual.containers import VerticalScroll
from datetime import date
from src.app import load_tasks, save_tasks, Task

class TdlApp(App):
    BINDINGS = [
        ("i", "add_task", "Add task"),
        ("j", "move_down", "Down"),
        ("k", "move_up", "Up"),
        ("q", "quit", "Quit"),
        ("d", "toggle_done", "Toggle done"),
        ("s", "cycle_priority", "Priority"),
        ("a", "set_date", "Set date"),
    ]

    def compose(self) -> ComposeResult:
        yield Input(placeholder="New task...", id="task-input")
        yield VerticalScroll(id="task-list")

    def on_mount(self) -> None:
        self.current_index = 0
        self.tasks = load_tasks()
        self.refresh_list()
        self.query_one(VerticalScroll).focus()

    def refresh_list(self) -> None:
        container = self.query_one("#task-list", VerticalScroll)
        container.remove_children()
        for i, task in enumerate(self.tasks):
            selected = self.current_index == i
            if selected and task.done:
                status = "[X]"
            elif selected:
                status = "[*]"
            elif task.done:
                status = "[x]"
            else:
                status = "[ ]"
            due = task.due_date[5:][::-1].replace("-", "/") if task.due_date else "xxx"
            pri = task.priority if task.priority is not None else "xxx"
            container.mount(Label(f"{status} {task.title:<30} {due:<12} {pri}", markup=False))

    def action_add_task(self) -> None:
        self.query_one("#task-input").focus()

    def action_set_date(self) -> None:
        if self.tasks:
            self.query_one("#task-input").placeholder = "Due date (dd/mm)..."
            self.query_one("#task-input").focus()
            self._setting_date = True

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if getattr(self, "_setting_date", False):
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
            self.query_one(VerticalScroll).focus()
        else:
            if value:
                task = Task(id=len(self.tasks) + 1, title=value)
                self.tasks.append(task)
                save_tasks(self.tasks)
                self.refresh_list()
                event.input.value = ""
            self.query_one(VerticalScroll).focus()

    def action_move_down(self) -> None:
        if self.current_index < len(self.tasks) - 1:
            self.current_index += 1
            self.refresh_list()

    def action_move_up(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            self.refresh_list()

    def action_toggle_done(self) -> None:
        if self.tasks:
            task = self.tasks[self.current_index]
            if task.done:
                self.tasks.pop(self.current_index)
                if self.current_index >= len(self.tasks):
                    self.current_index = max(0, len(self.tasks) - 1)
            else:
                task.done = True
                self.tasks.pop(self.current_index)
                self.tasks.append(task)
                if self.current_index >= len(self.tasks) - 1:
                    self.current_index = len(self.tasks) - 2
            save_tasks(self.tasks)
            self.refresh_list()

    def action_cycle_priority(self) -> None:
        if self.tasks:
            task = self.tasks[self.current_index]
            task.priority = (task.priority % 4) + 1
            save_tasks(self.tasks)
            self.refresh_list()


def main():
    app = TdlApp()
    app.run()

if __name__ == "__main__":
    main()
