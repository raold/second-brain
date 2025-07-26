from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field


class AdvancedSynthesisRequest(BaseModel):
    memory_ids: List[UUID]
    synthesis_type: str = Field(default="default")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class AdvancedSynthesisResult(BaseModel):
    id: UUID
    synthesis: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SynthesisOptions(BaseModel):
    max_tokens: int = Field(default=1000, gt=0)
    temperature: float = Field(default=0.7, ge=0, le=2)
    include_references: bool = Field(default=True)


class ExportFormat(str, Enum):
    """Supported export formats for synthesis results"""
    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    OBSIDIAN = "obsidian"


class ExportRequest(BaseModel):
    """Request to export synthesis results"""
    user_id: str
    format: ExportFormat = Field(default=ExportFormat.MARKDOWN)
    memory_ids: Optional[List[UUID]] = None
    synthesis_ids: Optional[List[UUID]] = None
    include_metadata: bool = Field(default=True)
    include_relationships: bool = Field(default=True)
    options: Dict[str, Any] = Field(default_factory=dict)


class ImportRequest(BaseModel):
    """Request to import content"""
    user_id: str
    format: ExportFormat
    content: str
    merge_strategy: str = Field(default="append")
    validate_schema: bool = Field(default=True)
    options: Dict[str, Any] = Field(default_factory=dict)


class SynthesisStrategy(str, Enum):
    """Synthesis strategies"""
    SUMMARY = "summary"
    ANALYSIS = "analysis"
    REPORT = "report"
    TIMELINE = "timeline"


class GraphLayout(str, Enum):
    """Graph layout algorithms"""
    FORCE_DIRECTED = "force_directed"
    HIERARCHICAL = "hierarchical"
    CIRCULAR = "circular"
    RANDOM = "random"


class WorkflowTrigger(str, Enum):
    """Workflow trigger types"""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT = "event"
    WEBHOOK = "webhook"


class WorkflowAction(str, Enum):
    """Workflow action types"""
    SYNTHESIZE = "synthesize"
    EXPORT = "export"
    NOTIFY = "notify"
    ANALYZE = "analyze"


# Export/Import Models
class ExportRequest(BaseModel):
    """Request to export memories or synthesis results"""
    format: ExportFormat
    memory_ids: Optional[List[UUID]] = None
    synthesis_ids: Optional[List[UUID]] = None
    include_metadata: bool = Field(default=True)
    include_relationships: bool = Field(default=True)
    options: Dict[str, Any] = Field(default_factory=dict)


class ImportRequest(BaseModel):
    """Request to import memories or synthesis results"""
    format: ExportFormat
    content: str
    merge_strategy: str = Field(default="append")
    validate_schema: bool = Field(default=True)
    options: Dict[str, Any] = Field(default_factory=dict)


# Graph Visualization Models
class GraphVisualizationRequest(BaseModel):
    """Request for graph visualization"""
    memory_ids: List[UUID]
    layout: GraphLayout = Field(default=GraphLayout.FORCE_DIRECTED)
    max_nodes: int = Field(default=100, gt=0)
    max_depth: int = Field(default=3, gt=0)
    include_types: Optional[List[str]] = None
    exclude_types: Optional[List[str]] = None
    options: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraph(BaseModel):
    """Knowledge graph representation"""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Synthesis Models
class SynthesisRequest(BaseModel):
    """Request for memory synthesis"""
    memory_ids: List[UUID]
    strategy: SynthesisStrategy = Field(default=SynthesisStrategy.SUMMARY)
    max_tokens: int = Field(default=1000, gt=0)
    temperature: float = Field(default=0.7, ge=0, le=2)
    include_references: bool = Field(default=True)
    options: Dict[str, Any] = Field(default_factory=dict)
    user_id: str


# Workflow Models
class WorkflowStep(BaseModel):
    """Individual step in a workflow"""
    id: str
    action: WorkflowAction
    parameters: Dict[str, Any] = Field(default_factory=dict)
    conditions: Optional[Dict[str, Any]] = None
    next_steps: List[str] = Field(default_factory=list)


class WorkflowDefinition(BaseModel):
    """Complete workflow definition"""
    id: UUID
    name: str
    description: Optional[str] = None
    trigger: WorkflowTrigger
    steps: List[WorkflowStep]
    variables: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SynthesisResult(BaseModel):
    """Result of memory synthesis"""
    id: UUID
    synthesis_type: str
    content: str
    source_memory_ids: List[UUID]
    confidence_score: float = Field(ge=0, le=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)