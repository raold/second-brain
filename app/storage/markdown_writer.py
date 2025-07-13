from pathlib import Path
import datetime

def write_markdown(payload):
    path = Path("/data/memories")
    path.mkdir(parents=True, exist_ok=True)
    file = path / f"{payload.id}.md"
    content = f"""
# {payload.target.title()} Entry

**ID**: {payload.id}  
**Timestamp**: {datetime.datetime.now().isoformat()}  
**Tags**: {', '.join(payload.data.get('tags', []))}  

## Note:
{payload.data.get('note')}
"""
    file.write_text(content)
