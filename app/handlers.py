from app.storage.markdown_writer import write_markdown
from app.storage.qdrant_client import store_vector
from app.storage.shell_runner import run_shell_command
from pathlib import Path
import datetime

def dispatch_payload(payload):
    print(f"[Router] Dispatching {payload.type}:{payload.intent} to {payload.target}")

    if payload.intent == "store":
        return handle_store(payload)

    if payload.intent == "execute":
        return handle_execute(payload)

    print(f"[Router] Unknown intent: {payload.intent}")


def handle_store(payload):
    target = payload.target

    if target == "note" or target == "memory":
        write_markdown(payload)
        store_vector(payload)

    elif target == "task":
        store_task(payload)

    elif target == "bookmark":
        store_bookmark(payload)

    elif target == "person":
        store_contact(payload)

    else:
        print(f"[Store] Unknown target: {target}")


def handle_execute(payload):
    command = payload.data.get("command")
    if command:
        run_shell_command(command)
    else:
        print("[Execute] Missing command in payload")


def store_task(payload):
    note = payload.data.get("note", "").strip()
    timestamp = payload.data.get("timestamp", datetime.datetime.now().isoformat())
    task_line = f"- [ ] {note}  \n  – created: {timestamp}\n"

    path = Path("/data/tasks.md")
    with path.open("a") as f:
        f.write(task_line)

    print(f"[Task] Logged: {note}")


def store_bookmark(payload):
    note = payload.data.get("note", "").strip()
    url = payload.data.get("url", "")
    timestamp = payload.data.get("timestamp", datetime.datetime.now().isoformat())

    entry = f"- [{note}]({url})  \n  – saved: {timestamp}\n"

    path = Path("/data/bookmarks.md")
    with path.open("a") as f:
        f.write(entry)

    print(f"[Bookmark] Logged: {note} => {url}")


def store_contact(payload):
    print(f"[Person] Storing contact info")
    # TODO: Implement contact storage

def categorize_payload(payload):
    note = payload.data.get("note", "").lower()

    if "http" in note or "www" in note:
        payload.intent = "store"
        payload.target = "bookmark"
    elif "remind" in note or "todo" in note or "task" in note:
        payload.intent = "store"
        payload.target = "task"
    elif note.startswith("cmd:") or note.startswith("run ") or note.startswith("!"):
        payload.intent = "execute"
        payload.target = "shell"
        payload.data["command"] = note.replace("cmd:", "").strip()
    else:
        payload.intent = "store"
        payload.target = "note"

    return payload
