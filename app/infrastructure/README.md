# Infrastructure Components

This directory contains the foundational infrastructure for real-time data processing, streaming, validation, and preprocessing.

## 🏗️ Architecture Overview

The infrastructure is built on four core pillars:

1. **Streaming Architecture** - Async streams with backpressure handling
2. **Preprocessing Pipelines** - Composable data transformation
3. **Advanced Validation** - Schema-based and custom validators
4. **Real-time Processing** - Priority queues and WebSocket support

## 📦 Components

### Streaming (`/streaming`)

Provides async streaming capabilities with:

- **Stream**: Generic async stream with backpressure strategies
- **StreamProcessor**: Base class for stream transformations
- **EventBus**: Central event distribution system
- **Event Types**: Structured events for system communication

#### Features:
- Multiple backpressure strategies (drop, buffer, block, sample)
- Stream operations (filter, map, batch, window)
- Stream merging and splitting
- Event-driven architecture

#### Example:
```python
from app.infrastructure import Stream, StreamProcessor, BackpressureStrategy

# Create a stream
stream = Stream[str](
    name="text-stream",
    buffer_size=1000,
    backpressure_strategy=BackpressureStrategy.BUFFER
)

# Apply transformations
processed = (
    stream
    .filter(lambda x: len(x) > 10)
    .map(lambda x: x.upper())
    .batch(10)
)

# Emit data
await stream.emit("Hello, World!")
```

### Preprocessing (`/preprocessing`)

Flexible pipeline framework for data transformation:

- **Pipeline**: Chain multiple processing steps
- **PipelineStep**: Abstract base for custom steps
- **PipelineBuilder**: Fluent API for pipeline construction
- **Text Preprocessing**: Specialized text processing steps

#### Features:
- Composable pipeline steps
- Error handling and recovery
- Performance tracking
- Pre-built text pipelines

#### Example:
```python
from app.infrastructure import PipelineBuilder, create_nlp_pipeline

# Build custom pipeline
pipeline = (
    PipelineBuilder[str]("my-pipeline")
    .validate(lambda x: len(x) > 0)
    .normalize()
    .clean(remove_html=True)
    .transform(lambda x: x.lower())
    .build()
)

# Or use pre-built pipeline
nlp_pipeline = create_nlp_pipeline()

# Process data
result = await pipeline.process("Some Text")
print(result.data)  # processed text
print(result.context.total_time)  # processing time
```

### Validation (`/validation`)

Comprehensive validation system:

- **Validators**: Composable validation rules
- **Schema Validation**: JSON Schema support
- **Custom Validators**: Function-based validation
- **Validation Results**: Detailed error reporting

#### Features:
- Type validation
- Range and length checks
- Pattern matching (regex)
- Composite validators (AND/OR)
- Schema-based validation
- Contextual validation

#### Example:
```python
from app.infrastructure import (
    RequiredValidator,
    TypeValidator,
    RangeValidator,
    validate_with_schema
)

# Simple validators
validator = RequiredValidator() & TypeValidator(int) & RangeValidator(0, 100)
result = await validator.validate(50, "score")

# Schema validation
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "age": {"type": "integer", "minimum": 0}
    },
    "required": ["name", "age"]
}

result = await validate_with_schema({"name": "John", "age": 30}, schema)
```

### Real-time Processing (`/realtime`)

High-performance real-time processing:

- **RealTimeProcessor**: Priority-based processing with worker pools
- **StreamingProcessor**: Stream processing with validation
- **WebSocketManager**: Real-time client communication
- **ProcessingOrchestrator**: Coordinate multiple processors

#### Features:
- Priority queues (critical, high, normal, low, background)
- Configurable worker pools
- Request timeouts and deadlines
- WebSocket event broadcasting
- Performance metrics

#### Example:
```python
from app.infrastructure import (
    RealTimeProcessor,
    ProcessingRequest,
    ProcessingPriority,
    get_websocket_manager
)

# Create processor
async def process_data(request: ProcessingRequest):
    # Process the data
    result_data = request.data.upper()
    return ProcessingResult(
        request_id=request.id,
        success=True,
        data=result_data
    )

processor = RealTimeProcessor(
    name="text-processor",
    process_func=process_data,
    max_workers=10,
    timeout=30.0
)

# Start processor
await processor.start()

# Submit request
request = ProcessingRequest(
    data="process this",
    priority=ProcessingPriority.HIGH
)
result = await processor.process(request)
```

## 🔄 Integration Example

Here's how to combine all components:

```python
from app.infrastructure import (
    Stream,
    PipelineBuilder,
    RealTimeProcessor,
    EventBus,
    EventType,
    ProcessingEvent
)

# 1. Create preprocessing pipeline
pipeline = (
    PipelineBuilder[dict]("ingestion-pipeline")
    .validate(lambda x: "content" in x)
    .normalize()
    .enrich(
        word_count=lambda x: len(x.get("content", "").split()),
        timestamp=lambda x: datetime.utcnow()
    )
    .build()
)

# 2. Create stream with preprocessing
input_stream = Stream[dict]("input")
processed_stream = input_stream.pipe(pipeline.create_stream_processor())

# 3. Create real-time processor
async def process_memory(request):
    # Process memory creation
    memory_data = request.data
    # ... processing logic ...
    
    # Emit event
    await publish_event(ProcessingEvent(
        event_type=EventType.PROCESSING_COMPLETED,
        processor_name="memory-processor",
        data={"memory_id": memory_data.get("id")}
    ))
    
    return ProcessingResult(request_id=request.id, success=True)

processor = RealTimeProcessor(
    name="memory-processor",
    process_func=process_memory
)

# 4. Start everything
await input_stream.start()
await processor.start()
await get_event_bus().start()
```

## 🎯 Use Cases

### 1. Real-time Memory Ingestion
```python
# Stream -> Preprocess -> Validate -> Process -> Store
memory_stream = Stream[dict]("memories")
preprocessed = memory_stream.pipe(create_nlp_pipeline())
validated = preprocessed.filter(lambda x: validate_memory(x).is_valid)
```

### 2. Live Dashboard Updates
```python
# Events -> WebSocket -> Client
ws_manager = get_websocket_manager()
await ws_manager.start()

# Client subscribes to memory events
connection.subscribe("memory.created")
connection.subscribe("memory.updated")
```

### 3. Batch Processing with Priority
```python
# High priority for recent memories
for memory in recent_memories:
    request = ProcessingRequest(
        data=memory,
        priority=ProcessingPriority.HIGH
    )
    await processor.process(request)
```

## 📊 Performance Considerations

1. **Streaming**
   - Choose appropriate backpressure strategy
   - Monitor buffer sizes
   - Use batching for efficiency

2. **Preprocessing**
   - Pipeline steps should be lightweight
   - Use async operations when possible
   - Cache expensive computations

3. **Validation**
   - Fail fast with early validation
   - Use schema validation for complex objects
   - Cache compiled validators

4. **Real-time Processing**
   - Balance worker count with CPU cores
   - Set appropriate timeouts
   - Monitor queue sizes

## 🔍 Monitoring

All components provide metrics:

```python
# Stream metrics
print(stream.metrics)
# {'name': 'text-stream', 'queue_size': 10, 'sequence_number': 100, ...}

# Pipeline metrics
print(pipeline.metrics)
# {'steps': [...], 'total_steps': 5}

# Processor metrics
print(processor.metrics)
# {'processed_count': 1000, 'error_rate': 0.01, 'avg_duration_ms': 50, ...}

# WebSocket metrics
print(ws_manager.get_metrics())
# {'total_connections': 5, 'channels': {...}}
```

## 🚀 Getting Started

1. **Import required components**:
```python
from app.infrastructure import (
    Stream, Pipeline, Validator, RealTimeProcessor
)
```

2. **Create your processing pipeline**:
```python
pipeline = PipelineBuilder[YourType]("your-pipeline")
    .add_your_steps()
    .build()
```

3. **Set up real-time processing**:
```python
processor = RealTimeProcessor("your-processor", your_process_func)
await processor.start()
```

4. **Connect WebSocket for live updates**:
```python
ws_manager = get_websocket_manager()
await ws_manager.start()
```

## 📝 Best Practices

1. **Always validate input data** before processing
2. **Use appropriate backpressure strategies** to prevent memory issues
3. **Monitor metrics** to identify bottlenecks
4. **Implement proper error handling** in processors
5. **Use priority queues** for time-sensitive operations
6. **Batch operations** when possible for efficiency
7. **Clean up resources** properly on shutdown

## 📌 Version Compatibility

This infrastructure module is compatible with Second Brain v2.5.0 and above.

### Version History:
- **v2.6.0**: Current version with full multimodal support
- **v2.5.0**: Initial infrastructure implementation
- **v2.4.x**: Not compatible (infrastructure module didn't exist)

### Migration Notes:
If upgrading from v2.5.x to v2.6.0:
- No breaking changes in infrastructure APIs
- New features are backward compatible
- Enhanced performance in streaming operations
- Additional validation capabilities added