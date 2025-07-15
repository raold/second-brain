from app.plugins import Plugin, register_plugin
from plyer import notification
import threading, time, datetime

class ReminderPlugin(Plugin):
    def __init__(self):
        super().__init__('reminder')
    def on_memory(self, memory):
        if memory.get('intent') == 'reminder':
            note = memory.get('note')
            remind_at = memory.get('metadata', {}).get('remind_at')
            if remind_at:
                # Schedule for future
                dt = datetime.datetime.fromisoformat(remind_at)
                delay = (dt - datetime.datetime.now()).total_seconds()
                if delay > 0:
                    threading.Timer(delay, lambda: notification.notify(title='Reminder', message=note)).start()
                    print(f"[ReminderPlugin] Scheduled reminder at {remind_at}: {note}")
                    return
            # Immediate notification
            notification.notify(title='Reminder', message=note)
            print(f"[ReminderPlugin] Immediate reminder: {note}")

register_plugin(ReminderPlugin()) 