"""
Advanced synthesis models for v2.8.2 Week 4 features.

This module defines data models for advanced memory synthesis,
knowledge graph visualization, and automated workflows.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class SynthesisStrategy(str, Enum):
    """Strategies for memory synthesis."""
    HIERARCHICAL = "hierarchical"
    TEMPORAL = "temporal"
    SEMANTIC = "semantic"
    CAUSAL = "causal"
    COMPARATIVE = "comparative"
    ABSTRACTIVE = "abstractive"


class GraphLayout(str, Enum):
    """Layout algorithms for knowledge graph visualization."""
    FORCE_DIRECTED = "force_directed"
    HIERARCHICAL = "hierarchical"
    CIRCULAR = "circular"
    RADIAL = "radial"
    TIMELINE = "timeline"
    CLUSTERED = "clustered"


class WorkflowTrigger(str, Enum):
    """Triggers for automated workflows."""
    SCHEDULE = "schedule"
    EVENT = "event"
    THRESHOLD = "threshold"
    MANUAL = "manual"
    CHAIN = "chain"


class WorkflowAction(str, Enum):
    """Actions that can be performed in workflows."""
    SYNTHESIZE = "synthesize"
    ANALYZE = "analyze"
    EXPORT = "export"
    NOTIFY = "notify"
    ARCHIVE = "archive"
    CONSOLIDATE = "consolidate"
    GENERATE_REPORT = "generate_report"
    UPDATE_GRAPH = "update_graph"


class ExportFormat(str, Enum):
    """Export formats for knowledge base."""
    MARKDOWN = "markdown"
    JSON = "json"
    GRAPHML = "graphml"
    PDF = "pdf"
    OBSIDIAN = "obsidian"
    ROAM = "roam"
    ANKI = "anki"
    CSV = "csv"


class SynthesisRequest(BaseModel):
    """Request for memory synthesis."""
    model_config = ConfigDict(from_attributes=True)

    memory_ids: list[UUID]
    strategy: SynthesisStrategy
    parameters: Optional[dict[str, Any]] = Field(default_factory=dict)
    user_id: str

    # Synthesis options
    preserve_sources: bool = True
    generate_citations: bool = True
    create_relationships: bool = True
    min_confidence: float = Field(0.7, ge=0.0, le=1.0)


class SynthesizedMemory(BaseModel):
    """Result of memory synthesis."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    title: str
    content: str
    synthesis_type: SynthesisStrategy
    source_memories: list[UUID]
    confidence_score: float = Field(ge=0.0, le=1.0)

    # Metadata
    key_concepts: list[str]
    relationships: dict[str, list[str]]  # relationship_type -> [entity_ids]
    citations: Optional[list[str]] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    synthesis_metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphNode(BaseModel):
    """Node in the knowledge graph."""
    model_config = ConfigDict(from_attributes=True)

    id: str  # Can be memory_id or entity_id
    label: str
    type: str  # memory, concept, entity, tag
    properties: dict[str, Any] = Field(default_factory=dict)

    # Visual properties
    size: float = 1.0
    color: Optional[str] = None
    icon: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None


class KnowledgeGraphEdge(BaseModel):
    """Edge in the knowledge graph."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    source: str
    target: str
    type: str  # relationship type
    weight: float = 1.0
    properties: dict[str, Any] = Field(default_factory=dict)

    # Visual properties
    color: Optional[str] = None
    style: Optional[str] = None  # solid, dashed, dotted


class KnowledgeGraph(BaseModel):
    """Complete knowledge graph structure."""
    model_config = ConfigDict(from_attributes=True)

    nodes: list[KnowledgeGraphNode]
    edges: list[KnowledgeGraphEdge]
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Graph statistics
    node_count: int = 0
    edge_count: int = 0
    density: float = 0.0
    clusters: Optional[list[list[str]]] = None

    generated_at: datetime = Field(default_factory=datetime.utcnow)

    def calculate_stats(self):
        """Calculate graph statistics."""
        self.node_count = len(self.nodes)
        self.edge_count = len(self.edges)

        if self.node_count > 1:
            max_edges = self.node_count * (self.node_count - 1) / 2
            self.density = self.edge_count / max_edges if max_edges > 0 else 0
        else:
            self.density = 0


class GraphVisualizationRequest(BaseModel):
    """Request for graph visualization."""
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    layout: GraphLayout = GraphLayout.FORCE_DIRECTED
    filters: Optional[dict[str, Any]] = Field(default_factory=dict)

    # Visualization options
    max_nodes: int = Field(500, ge=1, le=10000)
    include_orphans: bool = False
    cluster_by: Optional[str] = None  # tag, type, community
    time_range: Optional[dict[str, datetime]] = None

    # Styling
    node_size_by: Optional[str] = None  # importance, connections, age
    edge_weight_by: Optional[str] = None  # strength, frequency
    color_scheme: Optional[str] = "default"


class WorkflowStep(BaseModel):
    """Individual step in a workflow."""
    model_config = ConfigDict(from_attributes=True)

    action: WorkflowAction
    parameters: dict[str, Any] = Field(default_factory=dict)

    # Step configuration
    condition: Optional[str] = None  # Python expression
    on_success: Optional[list[str]] = None  # Next step IDs
    on_failure: Optional[list[str]] = None
    retry_on_failure: bool = True


class WorkflowDefinition(BaseModel):
    """Definition of an automated workflow."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    trigger: WorkflowTrigger
    actions: list[WorkflowStep]

    # Trigger configuration
    schedule: Optional[str] = None  # cron expression
    event_type: Optional[str] = None
    threshold_config: Optional[dict[str, Any]] = None

    # Workflow settings
    enabled: bool = True
    max_retries: int = 3
    timeout_seconds: int = 3600

    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class WorkflowExecution(BaseModel):
    """Execution record of a workflow."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID
    status: str  # running, completed, failed, cancelled

    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Execution details
    current_step: Optional[int] = None
    step_results: list[dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None

    # Metrics
    memories_processed: int = 0
    actions_completed: int = 0
    execution_time_ms: Optional[int] = None


class ExportRequest(BaseModel):
    """Request for knowledge export."""
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    format: ExportFormat

    # Export scope
    memory_ids: Optional[list[UUID]] = None  # None = all memories
    include_relationships: bool = True
    include_metadata: bool = True

    # Format-specific options
    format_options: dict[str, Any] = Field(default_factory=dict)

    # Filters
    tags: Optional[list[str]] = None
    date_range: Optional[dict[str, datetime]] = None
    importance_threshold: Optional[int] = None


class ExportResult(BaseModel):
    """Result of knowledge export."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    format: ExportFormat

    # Export data
    content: Optional[str] = None  # For text formats
    file_path: Optional[str] = None  # For file exports
    download_url: Optional[str] = None

    # Metadata
    memory_count: int
    relationship_count: int
    file_size_bytes: Optional[int] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class ImportRequest(BaseModel):
    """Request for knowledge import."""
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    format: ExportFormat
    source: str  # file path, URL, or raw content

    # Import options
    merge_strategy: str = "append"  # append, merge, replace
    detect_duplicates: bool = True
    preserve_timestamps: bool = False

    # Mapping configuration
    field_mapping: Optional[dict[str, str]] = None
    default_tags: Optional[list[str]] = None


class ImportResult(BaseModel):
    """Result of knowledge import."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)

    # Import statistics
    total_items: int
    imported_count: int
    skipped_count: int
    error_count: int

    # Details
    imported_memory_ids: list[UUID]
    errors: list[dict[str, str]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    started_at: datetime
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: Optional[float] = None


class SynthesisOrchestration(BaseModel):
    """Orchestration plan for complex synthesis operations."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str

    # Orchestration steps
    phases: list[OrchestrationPhase]
    dependencies: dict[str, list[str]] = Field(default_factory=dict)  # phase_id -> [dependent_phase_ids]

    # Configuration
    parallel_execution: bool = True
    stop_on_error: bool = False
    max_duration_seconds: int = 7200

    created_at: datetime = Field(default_factory=datetime.utcnow)


class OrchestrationPhase(BaseModel):
    """Phase in synthesis orchestration."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str

    # Phase operations
    synthesis_strategy: Optional[SynthesisStrategy] = None
    workflow_id: Optional[UUID] = None
    custom_operation: Optional[str] = None

    # Input/output
    input_memory_filter: Optional[dict[str, Any]] = None
    output_handling: str = "store"  # store, pass, aggregate

    # Configuration
    max_memories: Optional[int] = None
    batch_size: int = 100
    timeout_seconds: int = 1800
