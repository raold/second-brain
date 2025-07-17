from urllib.parse import urlparse

import requests

from app.plugins import Plugin, register_plugin
from app.utils.logger import logger

<<<<<<< HEAD
=======

>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01
class WebhookPlugin(Plugin):
    def __init__(self):
        super().__init__('webhook')
    def on_memory(self, memory):
        url = memory.get('meta', {}).get('webhook_url')
        if url:
            parsed = urlparse(url)
            if parsed.scheme not in ('http', 'https'):
                logger.warning(f"[WebhookPlugin] Invalid webhook URL: {url}")
                return
            logger.info(f"[WebhookPlugin] Triggering webhook: {url}")
            try:
                requests.post(url, json=memory)
            except Exception as e:
                logger.error(f"[WebhookPlugin] Webhook failed: {e}")

register_plugin(WebhookPlugin()) 