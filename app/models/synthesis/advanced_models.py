from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from typing import Optional
from typing import Dict
from typing import List
from typing import Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from pydantic import Field


class SynthesisStrategy(str, Enum):
    """Synthesis strategies"""
    SUMMARY = "summary"
    ANALYSIS = "analysis"
    REPORT = "report"
    TIMELINE = "timeline"
    COMPARISON = "comparison"
    INSIGHT = "insight"


class ExportFormat(str, Enum):
    """Supported export formats for synthesis results"""
    PDF = "pdf"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    DOCX = "docx"


class SynthesisRequest(BaseModel):
    """Request for advanced synthesis"""
    memory_ids: List[UUID]
    strategy: SynthesisStrategy = Field(default=SynthesisStrategy.SUMMARY)
    max_tokens: int = Field(default=1000, gt=0)
    temperature: float = Field(default=0.7, ge=0, le=2)
    include_references: bool = Field(default=True)
    include_metadata: bool = Field(default=True)
    user_id: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)


class SynthesisResult(BaseModel):
    """Result of synthesis operation"""
    id: UUID = Field(default_factory=uuid4)
    synthesis_type: str
    content: str
    source_memory_ids: List[UUID]
    confidence_score: float = Field(ge=0, le=1)
    themes: List[str] = Field(default_factory=list)
    references: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AdvancedSynthesisRequest(BaseModel):
    """Legacy request model for compatibility"""
    memory_ids: List[UUID]
    synthesis_type: str = Field(default="default")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class AdvancedSynthesisResult(BaseModel):
    """Legacy result model for compatibility"""
    id: UUID
    synthesis: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SynthesisOptions(BaseModel):
    """Options for synthesis operations"""
    max_tokens: int = Field(default=1000, gt=0)
    temperature: float = Field(default=0.7, ge=0, le=2)
    include_references: bool = Field(default=True)
    include_sub_themes: bool = Field(default=False)
    depth_level: int = Field(default=2, ge=1, le=5)
    language: str = Field(default="en")


class ThemeAnalysis(BaseModel):
    """Analysis of themes in memories"""
    theme_name: str
    frequency: int = Field(ge=0)
    importance: float = Field(ge=0, le=1)
    related_themes: List[str] = Field(default_factory=list)
    example_memories: List[UUID] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)