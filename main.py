from textual.app import App, ComposeResult
from textual.widgets import Label, Input
from textual.containers import VerticalScroll
from src.app import load_tasks, save_tasks, Task

class TdlApp(App):
    BINDINGS = [
        ("i", "add_task", "Add task"),
        ("j", "move_down", "Down"),
        ("k", "move_up", "Up"),
        ("q", "quit", "Quit"),
        ("d", "toggle_done", "Toggle done"),
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
            container.mount(Label(f"{status} {task.title}", markup=False))

    def action_add_task(self) -> None:
        self.query_one("#task-input").focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        title = event.value.strip()
        if title:
            task = Task(id=len(self.tasks) + 1, title=title)
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
                    self.current_index = max(0, len(self.tasks) -1)
            else:
                task.done = True
                self.tasks.pop(self.current_index)
                self.tasks.append(task)
                if self. current_index >= len(self.tasks) -1:
                    self.current_index = len(self.tasks) -2
            save_tasks(self.tasks)
            self.refresh_list()

def main():
        app = TdlApp()
        app.run()

if __name__ == "__main__":
    main()
