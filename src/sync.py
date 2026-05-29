import requests
from src.app import Task

API_URL = "https://api.todoist.com/api/v1"

def get_headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}

def fetch_todoist_tasks(api_key: str) -> list[dict]:
    response = requests.get(f"{API_URL}/tasks", headers=get_headers(api_key))
    response.raise_for_status()
    return response.json()["results"]

def push_task(api_key: str, task: Task) -> str:
    payload = {
        "content": task.title,
        "priority": task.priority,
    }
    if task.due_date:
        payload["due_date"] = task.due_date
    if task.description:
        payload["description"] = task.description
    response = requests.post(f"{API_URL}/tasks", headers=get_headers(api_key), json=payload)
    response.raise_for_status()
    return response.json()["id"]

def update_task(api_key: str, task: Task) -> None:
    payload = {
        "content": task.title,
        "priority": task.priority,
        "description": task.description or "",
    }
    if task.due_date:
        payload["due_date"] = task.due_date
    requests.post(f"{API_URL}/tasks/{task.todoist_id}", headers=get_headers(api_key), json=payload)

def sync(api_key: str, local_tasks: list[Task]) -> list[Task]:
    remote_tasks = fetch_todoist_tasks(api_key)
    remote_by_id = {t["id"]: t for t in remote_tasks}
    local_by_todoist_id = {t.todoist_id: t for t in local_tasks if t.todoist_id}
    result = []
    next_local_id = max((t.id for t in local_tasks), default=0) + 1
    for task in local_tasks:
        if not task.todoist_id:
            task.todoist_id = push_task(api_key, task)
            result.append(task)
        elif task.todoist_id in remote_by_id:
            remote = remote_by_id[task.todoist_id]
            task.title = remote["content"]
            task.description = remote.get("description") or None
            task.priority = remote["priority"]
            due_raw = remote.get("due", {}).get("date") if remote.get("due") else None
            task.due_date = due_raw[:10] if due_raw else None
            task.done = remote.get("checked", False)
            result.append(task)
        else:
            pass
    for remote in remote_tasks:
        rid = remote["id"]
        if rid not in local_by_todoist_id:
            task = Task(
                id=next_local_id,
                title=remote["content"],
                description=remote.get("description") or None,
                priority=remote["priority"],
                due_date=remote.get("due", {}).get("date")[:10] if remote.get("due") and remote["due"].get("date") else None,
                done=remote.get("checked", False),
                todoist_id=rid,
            )
            next_local_id += 1
            result.append(task)
    return result

def delete_task(api_key: str, todoist_id: str) -> None:
    requests.delete(f"{API_URL}/tasks/{todoist_id}", headers=get_headers(api_key))
