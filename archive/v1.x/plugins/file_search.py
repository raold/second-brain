import os
import typing

from app.plugins import Plugin, register_plugin

if typing.TYPE_CHECKING:
    pass  # type: ignore
from app.utils.logger import logger

<<<<<<< HEAD
=======

>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01
class FileSearchPlugin(Plugin):
    def __init__(self):
        super().__init__('file_search')
        self.index = {}  # file_path -> text
    def on_memory(self, memory):
        file_path = memory.get('meta', {}).get('file_path')
        if file_path and os.path.exists(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in ('.txt', '.pdf'):
                logger.warning(f"[FileSearchPlugin] Unsupported file type: {ext}")
                return
            text = ''
            if ext == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            elif ext == '.pdf':
                try:
                    import PyPDF2
                except ImportError:
                    logger.warning("[FileSearchPlugin] PyPDF2 not installed; skipping PDF indexing.")
                    return
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = '\n'.join(page.extract_text() or '' for page in reader.pages)
            if text:
                self.index[file_path] = text
                logger.info(f"[FileSearchPlugin] Indexed {file_path}")
    def search_files(self, keyword):
        return [path for path, text in self.index.items() if keyword.lower() in text.lower()]

register_plugin(FileSearchPlugin()) 