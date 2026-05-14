from textual.app import App, ComposeResult
from textual.widgets import ListItem, ListView, Label, Input
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
        yield ListView()

    def on_mount(self) -> None:
        self.current_index = 0
        self.tasks = load_tasks()
        self.refresh_list()
        self.query_one(ListView).focus()

    def refresh_list(self) -> None:
        list_view = self.query_one(ListView)
        list_view.clear()
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
            list_view.append(ListItem(Label(f"{status} {task.title}")))
        self.set_timer(0.05, self._restore_index)

    def _restore_index(self) -> None:
        self.query_one(ListView).index = self.current_index

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
            self.query_one(ListView).focus()

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
            self.tasks[self.current_index].done = not self.tasks[self.current_index].done
            self.notify(f"task {self.current_index} done={self.tasks[self.current_index].done}")
            save_tasks(self.tasks)
            self.refresh_list()

if __name__ == "__main__":
    app = TdlApp()
    app.run()
