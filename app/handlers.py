from app.storage.markdown_writer import write_markdown
from app.storage.qdrant_client import qdrant_upsert
from app.storage.shell_runner import run_shell_command
from pathlib import Path
import datetime
from app.models import Payload  # Assuming you have a Payload model

def dispatch_payload(payload: Payload):
    print(f"[Router] Dispatching {payload.type}:{payload.intent} to {payload.target}")

    if payload.intent == "store":
        return handle_store(payload)

    if payload.intent == "execute":
        return handle_execute(payload)

    print(f"[Router] Unknown intent: {payload.intent}")
    return None


def handle_store(payload: Payload):
    target = payload.target

    if target in ("note", "memory"):
        write_markdown(payload)
        qdrant_upsert(payload.dict())

    elif target == "task":
        store_task(payload)

    elif target == "bookmark":
        store_bookmark(payload)

    elif target == "person":
        store_contact(payload)

    else:
        print(f"[Store] Unknown target: {target}")
    return None


def handle_execute(payload: Payload):
    command = payload.data.get("command")
    if command:
        run_shell_command(command)
    else:
        print("[Execute] Missing command in payload")
    return None


def store_task(payload: Payload):
    note = payload.data.get("note", "").strip()
    timestamp = payload.data.get("timestamp", datetime.datetime.now().isoformat())
    task_line = f"- [ ] {note}  \n  – created: {timestamp}\n"

    path = Path("/data/tasks.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(task_line)

    print(f"[Task] Logged: {note}")


def store_bookmark(payload: Payload):
    note = payload.data.get("note", "").strip()
    url = payload.data.get("url", "")
    timestamp = payload.data.get("timestamp", datetime.datetime.now().isoformat())

    entry = f"- [{note}]({url})  \n  – saved: {timestamp}\n"

    path = Path("/data/bookmarks.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(entry)

    print(f"[Bookmark] Logged: {note} => {url}")


def store_contact(payload: Payload):
    print(f"[Person] Storing contact info")
    contact_info = payload.data.get("contact_info", "Unknown Contact")
    print(f"[Person] Contact Info: {contact_info}")


def categorize_payload(payload: Payload) -> Payload:
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
