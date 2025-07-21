"""
Preprocessing pipeline framework for data transformation and preparation
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Generic, Optional, TypeVar, Union

from app.infrastructure.streaming import Stream, StreamItem, StreamProcessor

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


class PreprocessingStage(str, Enum):
    """Stages in preprocessing pipeline"""
    INPUT_VALIDATION = "input_validation"
    NORMALIZATION = "normalization"
    CLEANING = "cleaning"
    TRANSFORMATION = "transformation"
    ENRICHMENT = "enrichment"
    VALIDATION = "validation"
    OUTPUT = "output"


@dataclass
class PipelineContext:
    """Context passed through pipeline stages"""
    pipeline_id: str
    stage: PreprocessingStage
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    stage_times: dict[str, float] = field(default_factory=dict)
    
    def add_error(self, error: str):
        """Add an error to context"""
        self.errors.append(f"[{self.stage.value}] {error}")
        
    def add_warning(self, warning: str):
        """Add a warning to context"""
        self.warnings.append(f"[{self.stage.value}] {warning}")
        
    def set_stage(self, stage: PreprocessingStage):
        """Update current stage and track timing"""
        if self.stage != stage:
            # Record time for previous stage
            elapsed = (datetime.utcnow() - self.start_time).total_seconds()
            self.stage_times[self.stage.value] = elapsed
            self.stage = stage
            
    @property
    def has_errors(self) -> bool:
        """Check if context has errors"""
        return len(self.errors) > 0
        
    @property
    def total_time(self) -> float:
        """Get total processing time"""
        return (datetime.utcnow() - self.start_time).total_seconds()


@dataclass
class PipelineData(Generic[T]):
    """Container for data flowing through pipeline"""
    data: T
    context: PipelineContext
    original_data: Optional[T] = None
    
    def __post_init__(self):
        if self.original_data is None:
            self.original_data = self.data


class PipelineStep(ABC, Generic[T, R]):
    """Abstract base class for pipeline steps"""
    
    def __init__(self, name: str = None, stage: PreprocessingStage = PreprocessingStage.TRANSFORMATION):
        self.name = name or self.__class__.__name__
        self.stage = stage
        self._processed_count = 0
        self._error_count = 0
        
    @abstractmethod
    async def process(self, data: T, context: PipelineContext) -> R:
        """Process data through this step"""
        pass
        
    async def __call__(self, pipeline_data: PipelineData[T]) -> PipelineData[R]:
        """Execute the step"""
        context = pipeline_data.context
        context.set_stage(self.stage)
        
        try:
            self._processed_count += 1
            processed_data = await self.process(pipeline_data.data, context)
            
            return PipelineData(
                data=processed_data,
                context=context,
                original_data=pipeline_data.original_data
            )
        except Exception as e:
            self._error_count += 1
            context.add_error(f"{self.name}: {str(e)}")
            logger.error(f"Error in pipeline step {self.name}: {e}")
            raise
            
    @property
    def metrics(self) -> dict[str, Any]:
        """Get step metrics"""
        return {
            "name": self.name,
            "stage": self.stage.value,
            "processed_count": self._processed_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(1, self._processed_count)
        }


class Pipeline(Generic[T, R]):
    """
    Preprocessing pipeline that chains multiple steps
    """
    
    def __init__(self, name: str = None):
        self.name = name or f"pipeline-{id(self)}"
        self._steps: list[PipelineStep] = []
        self._error_handlers: dict[type, Callable[[Exception, PipelineData], Any]] = {}
        self._before_hooks: list[Callable[[PipelineData], Any]] = []
        self._after_hooks: list[Callable[[PipelineData], Any]] = []
        
    def add_step(self, step: PipelineStep) -> 'Pipeline':
        """Add a step to the pipeline"""
        self._steps.append(step)
        return self
        
    def add_error_handler(self, error_type: type, handler: Callable[[Exception, PipelineData], Any]) -> 'Pipeline':
        """Add error handler for specific exception type"""
        self._error_handlers[error_type] = handler
        return self
        
    def add_before_hook(self, hook: Callable[[PipelineData], Any]) -> 'Pipeline':
        """Add hook to run before pipeline"""
        self._before_hooks.append(hook)
        return self
        
    def add_after_hook(self, hook: Callable[[PipelineData], Any]) -> 'Pipeline':
        """Add hook to run after pipeline"""
        self._after_hooks.append(hook)
        return self
        
    async def process(self, data: T) -> PipelineData[R]:
        """Process data through the pipeline"""
        # Create context
        context = PipelineContext(
            pipeline_id=f"{self.name}-{datetime.utcnow().isoformat()}",
            stage=PreprocessingStage.INPUT_VALIDATION
        )
        
        # Create initial pipeline data
        pipeline_data = PipelineData(data=data, context=context)
        
        # Run before hooks
        for hook in self._before_hooks:
            result = hook(pipeline_data)
            if asyncio.iscoroutine(result):
                await result
                
        try:
            # Process through steps
            current_data = pipeline_data
            for step in self._steps:
                current_data = await step(current_data)
                
            # Set final stage
            current_data.context.set_stage(PreprocessingStage.OUTPUT)
            
            # Run after hooks
            for hook in self._after_hooks:
                result = hook(current_data)
                if asyncio.iscoroutine(result):
                    await result
                    
            return current_data
            
        except Exception as e:
            # Try to find appropriate error handler
            for error_type, handler in self._error_handlers.items():
                if isinstance(e, error_type):
                    result = handler(e, current_data)
                    if asyncio.iscoroutine(result):
                        await result
                    break
            else:
                # No handler found, re-raise
                raise
                
    def create_stream_processor(self) -> StreamProcessor[T, PipelineData[R]]:
        """Create a stream processor from this pipeline"""
        class PipelineStreamProcessor(StreamProcessor[T, PipelineData[R]]):
            def __init__(self, pipeline: Pipeline):
                super().__init__(name=f"{pipeline.name}-processor")
                self.pipeline = pipeline
                
            async def process(self, item: StreamItem[T]) -> Optional[StreamItem[PipelineData[R]]]:
                try:
                    result = await self.pipeline.process(item.data)
                    return StreamItem(data=result, metadata=item.metadata)
                except Exception as e:
                    logger.error(f"Pipeline processing failed: {e}")
                    return None
                    
        return PipelineStreamProcessor(self)
        
    @property
    def metrics(self) -> dict[str, Any]:
        """Get pipeline metrics"""
        return {
            "name": self.name,
            "steps": [step.metrics for step in self._steps],
            "total_steps": len(self._steps)
        }


# Common preprocessing steps

class ValidationStep(PipelineStep[T, T]):
    """Validate data against rules"""
    
    def __init__(self, validators: list[Callable[[T], bool]], name: str = "validation"):
        super().__init__(name=name, stage=PreprocessingStage.INPUT_VALIDATION)
        self.validators = validators
        
    async def process(self, data: T, context: PipelineContext) -> T:
        """Validate data"""
        for i, validator in enumerate(self.validators):
            if not validator(data):
                raise ValueError(f"Validation {i} failed")
        return data


class NormalizationStep(PipelineStep[dict, dict]):
    """Normalize dictionary data"""
    
    def __init__(self, name: str = "normalization"):
        super().__init__(name=name, stage=PreprocessingStage.NORMALIZATION)
        
    async def process(self, data: dict, context: PipelineContext) -> dict:
        """Normalize data"""
        normalized = {}
        
        for key, value in data.items():
            # Normalize keys (lowercase, replace spaces)
            norm_key = key.lower().replace(" ", "_").replace("-", "_")
            
            # Normalize values
            if isinstance(value, str):
                norm_value = value.strip()
            elif isinstance(value, list):
                norm_value = [v.strip() if isinstance(v, str) else v for v in value]
            else:
                norm_value = value
                
            normalized[norm_key] = norm_value
            
        return normalized


class CleaningStep(PipelineStep[str, str]):
    """Clean text data"""
    
    def __init__(self, remove_html: bool = True, remove_extra_spaces: bool = True, name: str = "cleaning"):
        super().__init__(name=name, stage=PreprocessingStage.CLEANING)
        self.remove_html = remove_html
        self.remove_extra_spaces = remove_extra_spaces
        
    async def process(self, data: str, context: PipelineContext) -> str:
        """Clean text data"""
        import re
        
        cleaned = data
        
        if self.remove_html:
            # Remove HTML tags
            cleaned = re.sub(r'<[^>]+>', '', cleaned)
            
        if self.remove_extra_spaces:
            # Remove extra whitespace
            cleaned = re.sub(r'\s+', ' ', cleaned)
            cleaned = cleaned.strip()
            
        return cleaned


class TransformStep(PipelineStep[T, R]):
    """Generic transformation step"""
    
    def __init__(self, transform_func: Callable[[T], R], name: str = "transform"):
        super().__init__(name=name, stage=PreprocessingStage.TRANSFORMATION)
        self.transform_func = transform_func
        
    async def process(self, data: T, context: PipelineContext) -> R:
        """Transform data"""
        return self.transform_func(data)


class EnrichmentStep(PipelineStep[dict, dict]):
    """Enrich data with additional information"""
    
    def __init__(self, enrichers: dict[str, Callable[[dict], Any]], name: str = "enrichment"):
        super().__init__(name=name, stage=PreprocessingStage.ENRICHMENT)
        self.enrichers = enrichers
        
    async def process(self, data: dict, context: PipelineContext) -> dict:
        """Enrich data"""
        enriched = data.copy()
        
        for field, enricher in self.enrichers.items():
            try:
                enriched[field] = enricher(data)
            except Exception as e:
                context.add_warning(f"Failed to enrich field {field}: {e}")
                
        return enriched


class BatchingStep(PipelineStep[T, list[T]]):
    """Batch items together"""
    
    def __init__(self, batch_size: int, name: str = "batching"):
        super().__init__(name=name, stage=PreprocessingStage.TRANSFORMATION)
        self.batch_size = batch_size
        self._buffer: list[T] = []
        
    async def process(self, data: T, context: PipelineContext) -> list[T]:
        """Batch data"""
        self._buffer.append(data)
        
        if len(self._buffer) >= self.batch_size:
            batch = self._buffer[:self.batch_size]
            self._buffer = self._buffer[self.batch_size:]
            return batch
        else:
            # Return empty list if batch not full
            return []


class FilterStep(PipelineStep[T, Optional[T]]):
    """Filter data based on condition"""
    
    def __init__(self, predicate: Callable[[T], bool], name: str = "filter"):
        super().__init__(name=name, stage=PreprocessingStage.TRANSFORMATION)
        self.predicate = predicate
        
    async def process(self, data: T, context: PipelineContext) -> Optional[T]:
        """Filter data"""
        if self.predicate(data):
            return data
        else:
            context.add_warning("Data filtered out")
            return None


# Pipeline builder for fluent API

class PipelineBuilder(Generic[T]):
    """Builder for creating pipelines fluently"""
    
    def __init__(self, name: str = None):
        self._pipeline = Pipeline[T, Any](name=name)
        
    def validate(self, *validators: Callable[[Any], bool]) -> 'PipelineBuilder[T]':
        """Add validation step"""
        self._pipeline.add_step(ValidationStep(list(validators)))
        return self
        
    def normalize(self) -> 'PipelineBuilder[T]':
        """Add normalization step"""
        self._pipeline.add_step(NormalizationStep())
        return self
        
    def clean(self, **options) -> 'PipelineBuilder[T]':
        """Add cleaning step"""
        self._pipeline.add_step(CleaningStep(**options))
        return self
        
    def transform(self, func: Callable[[Any], Any], name: str = None) -> 'PipelineBuilder[T]':
        """Add transformation step"""
        self._pipeline.add_step(TransformStep(func, name=name or "transform"))
        return self
        
    def enrich(self, **enrichers) -> 'PipelineBuilder[T]':
        """Add enrichment step"""
        self._pipeline.add_step(EnrichmentStep(enrichers))
        return self
        
    def filter(self, predicate: Callable[[Any], bool]) -> 'PipelineBuilder[T]':
        """Add filter step"""
        self._pipeline.add_step(FilterStep(predicate))
        return self
        
    def batch(self, size: int) -> 'PipelineBuilder[T]':
        """Add batching step"""
        self._pipeline.add_step(BatchingStep(size))
        return self
        
    def add_step(self, step: PipelineStep) -> 'PipelineBuilder[T]':
        """Add custom step"""
        self._pipeline.add_step(step)
        return self
        
    def on_error(self, error_type: type, handler: Callable) -> 'PipelineBuilder[T]':
        """Add error handler"""
        self._pipeline.add_error_handler(error_type, handler)
        return self
        
    def before(self, hook: Callable) -> 'PipelineBuilder[T]':
        """Add before hook"""
        self._pipeline.add_before_hook(hook)
        return self
        
    def after(self, hook: Callable) -> 'PipelineBuilder[T]':
        """Add after hook"""
        self._pipeline.add_after_hook(hook)
        return self
        
    def build(self) -> Pipeline[T, Any]:
        """Build the pipeline"""
        return self._pipeline