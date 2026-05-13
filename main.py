from textual.app import App, ComposeResult
from textual.widgets import ListItem, ListView, Label, Input

from src.app import load_tasks, save_tasks, Task

class TdlApp(App):
    BINDINGS = [("i", "add_task", "Add task")]

    def compose(self) -> ComposeResult:
        yield Input(placeholder="New task...", id="task-input") 
        yield ListView()
    
    def on_mount(self) -> None:
        self.tasks = load_tasks()
        self.refresh_list()
   
    def refresh_list(self) -> None:
        list_view = self.query_one(ListView)
        list_view.clear()
        for task in self.tasks:
            list_view.append(ListItem(Label(task.title)))
    
    def action_add_task(self) -> None:
        self.query_one("#task-input").focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        title = event.value.strip()
        if title:
            task = Task(
                    id=len(self.tasks) +1,
                    title=title
            )
            self.tasks.append(task)
            save_tasks(self.tasks)
            self.refresh_list()
            event.input.value = ""
            self.query_one(ListView).focus()

if __name__ == "__main__":
    app = TdlApp()
    app.run()
