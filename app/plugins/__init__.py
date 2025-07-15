import importlib
import os
from pathlib import Path


class Plugin:
    def __init__(self, name):
        self.name = name
    def on_memory(self, memory):
        pass  # To be implemented by plugin

plugin_registry = {}

def register_plugin(plugin: Plugin):
    plugin_registry[plugin.name] = plugin

def get_registered_plugins():
    return list(plugin_registry.keys())

# Dynamic plugin discovery and registration
_plugins_dir = Path(__file__).parent
for file in os.listdir(_plugins_dir):
    if file.endswith('.py') and file != '__init__.py':
        module_name = f"app.plugins.{file[:-3]}"
        try:
            importlib.import_module(module_name)
        except Exception as e:
            # Log or print error if plugin fails to import
            print(f"[PluginLoader] Failed to import {module_name}: {e}") 