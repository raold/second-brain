class Plugin:
    def __init__(self, name):
        self.name = name
    def on_memory(self, memory):
        pass  # To be implemented by plugin

plugin_registry = {}

def register_plugin(plugin: Plugin):
    plugin_registry[plugin.name] = plugin

# Example usage:
# from .reminder import ReminderPlugin
# register_plugin(ReminderPlugin()) 