"""
Demo script showcasing infrastructure capabilities
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime, timedelta

from app.infrastructure import (
    # Streaming
    BackpressureStrategy,
    Event,
    EventBus,
    EventType,
    Stream,
    StreamItem,
    get_event_bus,
    publish_event,
    # Preprocessing
    PipelineBuilder,
    create_basic_text_pipeline,
    create_nlp_pipeline,
    # Validation
    JSONSchema,
    ValidationResult,
    validate_with_schema,
    # Real-time processing
    ProcessingPriority,
    ProcessingRequest,
    ProcessingResult,
    RealTimeOrchestrator,
    RealTimeProcessor,
    StreamingProcessor,
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def demo_streaming():
    """Demonstrate streaming capabilities"""
    print("\n" + "="*80)
    print("🌊 STREAMING DEMO")
    print("="*80 + "\n")
    
    # 1. Basic stream
    print("1. Basic Stream Operations:")
    stream = Stream[int](
        name="number-stream",
        buffer_size=100,
        backpressure_strategy=BackpressureStrategy.BUFFER
    )
    
    # Apply transformations
    processed_stream = (
        stream
        .filter(lambda x: x % 2 == 0)  # Keep even numbers
        .map(lambda x: x * 2)  # Double them
        .batch(5)  # Batch in groups of 5
    )
    
    await stream.start()
    
    # Emit some data
    print("Emitting numbers 1-10...")
    for i in range(1, 11):
        await stream.emit(i)
    
    # Collect results
    results = []
    async def collect_results(item: StreamItem[list[int]]):
        results.append(item.data)
        print(f"  Batch received: {item.data}")
    
    processed_stream.subscribe(collect_results)
    
    # Process
    await asyncio.sleep(0.5)
    
    # 2. Event streaming
    print("\n2. Event Streaming:")
    event_bus = get_event_bus()
    await event_bus.start()
    
    # Subscribe to events
    events_received = []
    def handle_event(event: Event):
        events_received.append(event)
        print(f"  Event received: {event.event_type.value} - {event.data}")
    
    event_bus.subscribe(EventType.PROCESSING_COMPLETED, handle_event)
    
    # Publish events
    await publish_event(Event(
        event_type=EventType.PROCESSING_COMPLETED,
        source="demo",
        data={"message": "Task completed successfully"}
    ))
    
    await asyncio.sleep(0.1)
    
    # 3. Stream windowing
    print("\n3. Stream Windowing (2-second windows):")
    time_stream = Stream[str](name="time-stream")
    windowed = time_stream.window(duration=2.0, slide=1.0)
    
    windows_received = []
    async def collect_windows(item: StreamItem[list[str]]):
        windows_received.append(item.data)
        print(f"  Window: {item.data} (size: {len(item.data)})")
    
    windowed.subscribe(collect_windows)
    
    await time_stream.start()
    
    # Emit time-based data
    for i in range(5):
        await time_stream.emit(f"Event-{i}")
        await asyncio.sleep(0.5)
    
    await asyncio.sleep(2.5)  # Wait for final window
    
    print(f"\nStream metrics: {stream.metrics}")


async def demo_preprocessing():
    """Demonstrate preprocessing pipelines"""
    print("\n" + "="*80)
    print("🔧 PREPROCESSING DEMO")
    print("="*80 + "\n")
    
    # 1. Basic text pipeline
    print("1. Basic Text Pipeline:")
    text = "Check out https://example.com for MORE information! Contact: user@email.com"
    
    pipeline = create_basic_text_pipeline()
    result = await pipeline.process(text)
    
    print(f"  Original: {text}")
    print(f"  Processed: {result.data}")
    print(f"  Processing time: {result.context.total_time:.3f}s")
    
    # 2. Custom pipeline
    print("\n2. Custom Pipeline with Multiple Steps:")
    
    custom_pipeline = (
        PipelineBuilder[dict]("custom-pipeline")
        .validate(lambda x: "text" in x, lambda x: len(x["text"]) > 0)
        .normalize()
        .transform(lambda x: {**x, "text": x["text"].upper()}, name="uppercase")
        .enrich(
            length=lambda x: len(x["text"]),
            word_count=lambda x: len(x["text"].split()),
            timestamp=lambda x: datetime.utcnow().isoformat()
        )
        .build()
    )
    
    input_data = {"text": "Hello World", "author": "Demo"}
    result = await custom_pipeline.process(input_data)
    
    print(f"  Input: {input_data}")
    print(f"  Output: {result.data}")
    print(f"  Context: {result.context.stage_times}")
    
    # 3. NLP pipeline
    print("\n3. NLP Pipeline:")
    nlp_text = "The quick brown fox jumps over the lazy dog!"
    
    nlp_pipeline = create_nlp_pipeline()
    result = await nlp_pipeline.process(nlp_text)
    
    print(f"  Original: {nlp_text}")
    print(f"  Tokens: {result.data[:10]}...")  # First 10 tokens
    print(f"  Total tokens: {len(result.data) if isinstance(result.data, list) else 'N/A'}")
    
    # 4. Error handling
    print("\n4. Pipeline Error Handling:")
    
    def failing_transform(x):
        if "error" in x:
            raise ValueError("Intentional error")
        return x
    
    error_pipeline = (
        PipelineBuilder[dict]("error-pipeline")
        .transform(failing_transform)
        .on_error(ValueError, lambda e, data: print(f"  Caught error: {e}"))
        .build()
    )
    
    try:
        await error_pipeline.process({"error": True})
    except ValueError:
        print("  Error propagated as expected")


async def demo_validation():
    """Demonstrate validation system"""
    print("\n" + "="*80)
    print("✅ VALIDATION DEMO")
    print("="*80 + "\n")
    
    # 1. Schema validation
    print("1. Schema Validation:")
    
    user_schema = {
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "minLength": 3,
                "maxLength": 20,
                "pattern": "^[a-zA-Z0-9_]+$"
            },
            "email": {
                "type": "string",
                "format": "email"
            },
            "age": {
                "type": "integer",
                "minimum": 13,
                "maximum": 120
            },
            "roles": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["user", "admin", "moderator"]
                }
            }
        },
        "required": ["username", "email"]
    }
    
    # Valid data
    valid_user = {
        "username": "john_doe",
        "email": "john@example.com",
        "age": 25,
        "roles": ["user", "moderator"]
    }
    
    result = await validate_with_schema(valid_user, user_schema)
    print(f"  Valid user validation: {result.is_valid}")
    
    # Invalid data
    invalid_user = {
        "username": "jd",  # Too short
        "email": "not-an-email",
        "age": 200,  # Too old
        "roles": ["superuser"]  # Invalid role
    }
    
    result = await validate_with_schema(invalid_user, user_schema)
    print(f"  Invalid user validation: {result.is_valid}")
    print(f"  Errors: {result.error_count}")
    for issue in result.issues[:3]:  # First 3 issues
        print(f"    - {issue.field}: {issue.message}")
    
    # 2. Memory validation
    print("\n2. Memory Validation:")
    
    from app.infrastructure.validation import validate_memory
    
    valid_memory = {
        "content": "This is a test memory",
        "memory_type": "general",
        "importance": 0.7,
        "tags": ["test", "demo"]
    }
    
    result = await validate_memory(valid_memory)
    print(f"  Valid memory: {result.is_valid}")
    
    invalid_memory = {
        "content": "",  # Empty content
        "memory_type": "invalid_type",
        "importance": 1.5  # Out of range
    }
    
    result = await validate_memory(invalid_memory)
    print(f"  Invalid memory: {result.is_valid}")
    print(f"  Issues: {[issue.message for issue in result.issues]}")


async def demo_realtime_processing():
    """Demonstrate real-time processing"""
    print("\n" + "="*80)
    print("⚡ REAL-TIME PROCESSING DEMO")
    print("="*80 + "\n")
    
    # 1. Create processor
    print("1. Real-time Processor with Priority Queues:")
    
    async def process_task(request: ProcessingRequest) -> ProcessingResult:
        """Simulate task processing"""
        start_time = time.time()
        
        # Simulate work based on priority
        if request.priority == ProcessingPriority.CRITICAL:
            await asyncio.sleep(0.1)
        elif request.priority == ProcessingPriority.HIGH:
            await asyncio.sleep(0.2)
        else:
            await asyncio.sleep(0.3)
        
        # Process data
        result_data = {
            "original": request.data,
            "processed": request.data.upper() if isinstance(request.data, str) else str(request.data),
            "priority": request.priority.value
        }
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return ProcessingResult(
            request_id=request.id,
            success=True,
            data=result_data,
            duration_ms=duration_ms
        )
    
    processor = RealTimeProcessor(
        name="demo-processor",
        process_func=process_task,
        max_workers=3,
        timeout=5.0
    )
    
    await processor.start()
    
    # 2. Submit requests with different priorities
    print("\n2. Processing Requests by Priority:")
    
    requests = [
        ProcessingRequest(data="critical task", priority=ProcessingPriority.CRITICAL),
        ProcessingRequest(data="normal task 1", priority=ProcessingPriority.NORMAL),
        ProcessingRequest(data="high priority", priority=ProcessingPriority.HIGH),
        ProcessingRequest(data="low priority", priority=ProcessingPriority.LOW),
        ProcessingRequest(data="normal task 2", priority=ProcessingPriority.NORMAL),
    ]
    
    # Submit all requests
    tasks = []
    for req in requests:
        print(f"  Submitting: {req.data} ({req.priority.value})")
        tasks.append(processor.process(req))
    
    # Wait for results
    results = await asyncio.gather(*tasks)
    
    print("\n  Results (in completion order):")
    for result in results:
        if result.success:
            print(f"    ✓ {result.data['original']} - {result.duration_ms}ms")
    
    # 3. Streaming processor
    print("\n3. Streaming Processor with Validation:")
    
    # Create input stream
    input_stream = Stream[dict](name="input")
    
    # Create validator
    from app.infrastructure.validation import DictValidator, RequiredValidator, TypeValidator
    
    validator = DictValidator({
        "text": RequiredValidator() & TypeValidator(str),
        "priority": TypeValidator(str)
    })
    
    # Create preprocessing pipeline
    preprocess = PipelineBuilder[dict]("preprocess")
        .transform(lambda x: {**x, "text": x["text"].strip().lower()})
        .build()
    
    # Create streaming processor
    stream_processor = StreamingProcessor(
        name="stream-processor",
        input_stream=input_stream,
        validator=validator,
        preprocessor=preprocess
    )
    
    await input_stream.start()
    await stream_processor.start()
    
    # Process stream items
    print("\n  Streaming items:")
    stream_items = [
        {"text": "  HELLO WORLD  ", "priority": "high"},
        {"text": "stream processing", "priority": "normal"},
        {"invalid": "data"},  # Will fail validation
        {"text": "real-time demo", "priority": "low"}
    ]
    
    for item in stream_items:
        success = await input_stream.emit(item)
        print(f"    Emitted: {item} - {'✓' if success else '✗'}")
    
    await asyncio.sleep(0.5)
    
    # 4. Show metrics
    print("\n4. Processor Metrics:")
    metrics = processor.metrics
    print(f"  Processed: {metrics['processed_count']}")
    print(f"  Errors: {metrics['error_count']}")
    print(f"  Avg Duration: {metrics['avg_duration_ms']:.1f}ms")
    print(f"  Queue sizes: {metrics['queue_sizes']}")
    
    # Cleanup
    await processor.stop()
    await stream_processor.stop()


async def demo_orchestration():
    """Demonstrate orchestration of multiple processors"""
    print("\n" + "="*80)
    print("🎭 ORCHESTRATION DEMO")
    print("="*80 + "\n")
    
    # Create orchestrator
    orchestrator = RealTimeOrchestrator("demo-orchestrator")
    
    # Add multiple processors
    async def text_processor(req: ProcessingRequest):
        await asyncio.sleep(0.1)
        return ProcessingResult(
            request_id=req.id,
            success=True,
            data={"processed_text": req.data.upper()}
        )
    
    async def number_processor(req: ProcessingRequest):
        await asyncio.sleep(0.05)
        return ProcessingResult(
            request_id=req.id,
            success=True,
            data={"squared": req.data ** 2}
        )
    
    orchestrator.add_processor(RealTimeProcessor("text-proc", text_processor, max_workers=2))
    orchestrator.add_processor(RealTimeProcessor("number-proc", number_processor, max_workers=2))
    
    await orchestrator.start()
    
    # Process different types of data
    print("Processing mixed data types through appropriate processors:")
    
    # Text processing
    text_result = await orchestrator.process(
        "text-proc",
        ProcessingRequest(data="hello orchestrator")
    )
    print(f"  Text result: {text_result.data}")
    
    # Number processing
    number_result = await orchestrator.process(
        "number-proc",
        ProcessingRequest(data=7)
    )
    print(f"  Number result: {number_result.data}")
    
    # Show orchestrator metrics
    print(f"\nOrchestrator metrics: {json.dumps(orchestrator.get_metrics(), indent=2)}")
    
    await orchestrator.stop()


async def main():
    """Run all infrastructure demos"""
    print("\n🏗️ INFRASTRUCTURE DEMO\n")
    print("This demo showcases the streaming, preprocessing, validation,")
    print("and real-time processing capabilities of the infrastructure.\n")
    
    await demo_streaming()
    await demo_preprocessing()
    await demo_validation()
    await demo_realtime_processing()
    await demo_orchestration()
    
    print("\n✅ Infrastructure demo completed!")
    print("\nKey takeaways:")
    print("- Streaming: Async streams with backpressure and transformations")
    print("- Preprocessing: Composable pipelines for data transformation")
    print("- Validation: Schema-based validation with detailed error reporting")
    print("- Real-time: Priority-based processing with worker pools")
    print("- Orchestration: Coordinate multiple processors efficiently")


if __name__ == "__main__":
    asyncio.run(main())