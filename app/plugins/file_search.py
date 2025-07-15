from app.plugins import Plugin, register_plugin
import os
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

class FileSearchPlugin(Plugin):
    def __init__(self):
        super().__init__('file_search')
        self.index = {}  # file_path -> text
    def on_memory(self, memory):
        file_path = memory.get('metadata', {}).get('file_path')
        if file_path and os.path.exists(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            text = ''
            if ext == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            elif ext == '.pdf' and PyPDF2:
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = '\n'.join(page.extract_text() or '' for page in reader.pages)
            if text:
                self.index[file_path] = text
                print(f"[FileSearchPlugin] Indexed {file_path}")
    def search_files(self, keyword):
        return [path for path, text in self.index.items() if keyword.lower() in text.lower()]

register_plugin(FileSearchPlugin()) 