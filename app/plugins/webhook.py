from app.plugins import Plugin, register_plugin
import requests

class WebhookPlugin(Plugin):
    def __init__(self):
        super().__init__('webhook')
    def on_memory(self, memory):
        url = memory.get('metadata', {}).get('webhook_url')
        if url:
            print(f"[WebhookPlugin] Triggering webhook: {url}")
            try:
                requests.post(url, json=memory)
            except Exception as e:
                print(f"[WebhookPlugin] Webhook failed: {e}")

register_plugin(WebhookPlugin()) 