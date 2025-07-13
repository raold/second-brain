from pydantic import BaseModel
from typing import Optional, Dict, Any

class Payload(BaseModel):
    id: str
    type: str
    intent: Optional[str] = None
    target: Optional[str] = None
    context: str
    priority: str
    ttl: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
