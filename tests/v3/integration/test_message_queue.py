"""
Integration tests for message queue.
"""

import asyncio
import json
import pytest
from typing import Any, Dict, List
from uuid import uuid4

from src.domain.events.memory_events import MemoryCreated, MemoryDeleted, MemoryUpdated
from src.infrastructure.messaging import MessageBroker, EventPublisher
from src.infrastructure.messaging.handlers import MessageHandler

from ..fixtures.factories import MemoryFactory


class TestMessageHandler(MessageHandler):
    """Test message handler that records received messages."""
    
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.processed_count = 0
    
    async def handle(self, message: Dict[str, Any]) -> None:
        """Handle test message."""
        self.messages.append(message)
        self.processed_count += 1


@pytest.mark.integration
@pytest.mark.asyncio
class TestMessageBroker:
    """Integration tests for MessageBroker."""
    
    async def test_publish_and_subscribe(self, message_broker):
        """Test basic publish and subscribe."""
        # Arrange
        routing_key = "test.message"
        handler = TestMessageHandler()
        message = {"type": "test", "data": "Hello, World!"}
        
        # Subscribe
        await message_broker.subscribe(routing_key, handler.handle)
        
        # Give subscription time to establish
        await asyncio.sleep(0.1)
        
        # Act
        await message_broker.publish(routing_key, message)
        
        # Give message time to be delivered
        await asyncio.sleep(0.2)
        
        # Assert
        assert handler.processed_count == 1
        assert handler.messages[0] == message
    
    async def test_multiple_subscribers(self, message_broker):
        """Test multiple subscribers to same routing key."""
        # Arrange
        routing_key = "broadcast.message"
        handler1 = TestMessageHandler()
        handler2 = TestMessageHandler()
        message = {"type": "broadcast", "id": str(uuid4())}
        
        # Subscribe both handlers
        await message_broker.subscribe(routing_key, handler1.handle)
        await message_broker.subscribe(routing_key, handler2.handle)
        
        await asyncio.sleep(0.1)
        
        # Act
        await message_broker.publish(routing_key, message)
        
        await asyncio.sleep(0.2)
        
        # Assert - Both should receive
        assert handler1.processed_count == 1
        assert handler2.processed_count == 1
        assert handler1.messages[0] == message
        assert handler2.messages[0] == message
    
    async def test_persistent_messages(self, message_broker):
        """Test persistent message delivery."""
        # Arrange
        routing_key = "persistent.message"
        message = {"type": "important", "persist": True}
        
        # Publish before subscriber
        await message_broker.publish(routing_key, message, persistent=True)
        
        # Now subscribe
        handler = TestMessageHandler()
        await message_broker.subscribe(
            routing_key,
            handler.handle,
            queue_name="persistent_test_queue"
        )
        
        await asyncio.sleep(0.3)
        
        # Assert - Should receive previously published message
        assert handler.processed_count == 1
        assert handler.messages[0] == message
    
    async def test_routing_patterns(self, message_broker):
        """Test routing with wildcards."""
        # Arrange
        handlers = {
            "events.memory.*": TestMessageHandler(),
            "events.*.created": TestMessageHandler(),
            "events.#": TestMessageHandler(),  # Catch all
        }
        
        for pattern, handler in handlers.items():
            await message_broker.subscribe(pattern, handler.handle)
        
        await asyncio.sleep(0.1)
        
        # Act
        await message_broker.publish("events.memory.created", {"event": "memory_created"})
        await message_broker.publish("events.memory.updated", {"event": "memory_updated"})
        await message_broker.publish("events.user.created", {"event": "user_created"})
        await message_broker.publish("events.system.startup", {"event": "startup"})
        
        await asyncio.sleep(0.3)
        
        # Assert
        memory_handler = handlers["events.memory.*"]
        assert memory_handler.processed_count == 2  # memory.created and memory.updated
        
        created_handler = handlers["events.*.created"]
        assert created_handler.processed_count == 2  # memory.created and user.created
        
        catch_all_handler = handlers["events.#"]
        assert catch_all_handler.processed_count == 4  # All events
    
    async def test_error_handling(self, message_broker):
        """Test error handling in message processing."""
        # Arrange
        routing_key = "error.test"
        error_count = 0
        success_count = 0
        
        async def failing_handler(message: Dict[str, Any]) -> None:
            nonlocal error_count
            error_count += 1
            if message.get("fail", False):
                raise ValueError("Simulated error")
            nonlocal success_count
            success_count += 1
        
        await message_broker.subscribe(routing_key, failing_handler)
        await asyncio.sleep(0.1)
        
        # Act
        await message_broker.publish(routing_key, {"fail": True})
        await message_broker.publish(routing_key, {"fail": False})
        
        await asyncio.sleep(0.2)
        
        # Assert
        assert error_count == 2  # Both messages attempted
        assert success_count == 1  # Only non-failing succeeded
    
    async def test_large_message(self, message_broker):
        """Test handling large messages."""
        # Arrange
        routing_key = "large.message"
        handler = TestMessageHandler()
        
        # Create large message
        large_data = {
            "type": "large",
            "items": [{"id": i, "data": "x" * 1000} for i in range(100)]
        }
        
        await message_broker.subscribe(routing_key, handler.handle)
        await asyncio.sleep(0.1)
        
        # Act
        await message_broker.publish(routing_key, large_data)
        await asyncio.sleep(0.3)
        
        # Assert
        assert handler.processed_count == 1
        assert handler.messages[0] == large_data


@pytest.mark.integration
@pytest.mark.asyncio
class TestEventPublisher:
    """Integration tests for EventPublisher."""
    
    async def test_publish_domain_events(self, message_broker):
        """Test publishing domain events."""
        # Arrange
        publisher = EventPublisher(message_broker)
        handler = TestMessageHandler()
        
        # Subscribe to event types
        await message_broker.subscribe("events.memory.created", handler.handle)
        await message_broker.subscribe("events.memory.updated", handler.handle)
        await message_broker.subscribe("events.memory.deleted", handler.handle)
        
        await asyncio.sleep(0.1)
        
        # Create events
        memory_id = uuid4()
        created_event = MemoryCreated(
            aggregate_id=memory_id,
            memory_type="fact",
            title="Test Memory"
        )
        updated_event = MemoryUpdated(
            aggregate_id=memory_id,
            fields_updated=["title", "content"]
        )
        deleted_event = MemoryDeleted(aggregate_id=memory_id)
        
        # Act
        await publisher.publish(created_event)
        await publisher.publish(updated_event)
        await publisher.publish(deleted_event)
        
        await asyncio.sleep(0.3)
        
        # Assert
        assert handler.processed_count == 3
        
        # Check event data
        messages = handler.messages
        assert messages[0]["event_type"] == "MemoryCreated"
        assert messages[0]["aggregate_id"] == str(memory_id)
        assert messages[0]["data"]["memory_type"] == "fact"
        
        assert messages[1]["event_type"] == "MemoryUpdated"
        assert messages[1]["data"]["fields_updated"] == ["title", "content"]
        
        assert messages[2]["event_type"] == "MemoryDeleted"
    
    async def test_event_correlation(self, message_broker):
        """Test event correlation IDs."""
        # Arrange
        publisher = EventPublisher(message_broker)
        handler = TestMessageHandler()
        
        await message_broker.subscribe("events.memory.created", handler.handle)
        await asyncio.sleep(0.1)
        
        # Create event with correlation
        correlation_id = uuid4()
        event = MemoryCreated(
            aggregate_id=uuid4(),
            memory_type="fact",
            title="Correlated Event"
        )
        event.correlation_id = correlation_id
        
        # Act
        await publisher.publish(event)
        await asyncio.sleep(0.2)
        
        # Assert
        assert handler.processed_count == 1
        message = handler.messages[0]
        assert message["correlation_id"] == str(correlation_id)
    
    async def test_batch_event_publishing(self, message_broker):
        """Test publishing multiple events efficiently."""
        # Arrange
        publisher = EventPublisher(message_broker)
        handler = TestMessageHandler()
        
        await message_broker.subscribe("events.memory.*", handler.handle)
        await asyncio.sleep(0.1)
        
        # Create batch of events
        events = []
        for i in range(10):
            event = MemoryCreated(
                aggregate_id=uuid4(),
                memory_type="fact",
                title=f"Batch Memory {i}"
            )
            events.append(event)
        
        # Act - Publish all events
        for event in events:
            await publisher.publish(event)
        
        await asyncio.sleep(0.5)
        
        # Assert
        assert handler.processed_count == 10
        
        # Verify order preserved
        for i, message in enumerate(handler.messages):
            assert f"Batch Memory {i}" in message["data"]["title"]


@pytest.mark.integration
@pytest.mark.asyncio
class TestMessageQueuePatterns:
    """Test common message queue patterns."""
    
    async def test_request_reply_pattern(self, message_broker):
        """Test request-reply messaging pattern."""
        # Arrange
        request_queue = "rpc.request"
        reply_queue = f"rpc.reply.{uuid4()}"
        
        # Service that handles requests
        async def service_handler(message: Dict[str, Any]) -> None:
            if message.get("method") == "add":
                result = message["params"]["a"] + message["params"]["b"]
                reply = {
                    "id": message["id"],
                    "result": result
                }
                await message_broker.publish(message["reply_to"], reply)
        
        await message_broker.subscribe(request_queue, service_handler)
        
        # Client handler for replies
        reply_handler = TestMessageHandler()
        await message_broker.subscribe(reply_queue, reply_handler.handle)
        
        await asyncio.sleep(0.1)
        
        # Act - Send request
        request = {
            "id": str(uuid4()),
            "method": "add",
            "params": {"a": 5, "b": 3},
            "reply_to": reply_queue
        }
        await message_broker.publish(request_queue, request)
        
        await asyncio.sleep(0.2)
        
        # Assert
        assert reply_handler.processed_count == 1
        reply = reply_handler.messages[0]
        assert reply["id"] == request["id"]
        assert reply["result"] == 8
    
    async def test_work_queue_pattern(self, message_broker):
        """Test work queue with multiple workers."""
        # Arrange
        work_queue = "tasks.process"
        workers = [TestMessageHandler() for _ in range(3)]
        
        # Subscribe workers to same queue (competing consumers)
        for i, worker in enumerate(workers):
            await message_broker.subscribe(
                work_queue,
                worker.handle,
                queue_name=f"worker_queue_{i}"
            )
        
        await asyncio.sleep(0.1)
        
        # Act - Send multiple tasks
        for i in range(9):
            task = {"task_id": i, "work": f"Process item {i}"}
            await message_broker.publish(work_queue, task)
        
        await asyncio.sleep(0.5)
        
        # Assert - Work distributed among workers
        total_processed = sum(w.processed_count for w in workers)
        assert total_processed == 9
        
        # Each worker should have processed some tasks
        for worker in workers:
            assert worker.processed_count > 0
    
    async def test_dead_letter_queue(self, message_broker):
        """Test dead letter queue for failed messages."""
        # This test would require specific RabbitMQ configuration
        # Simplified version for demonstration
        
        # Arrange
        main_queue = "process.items"
        dlq = "process.items.dlq"
        max_retries = 3
        retry_count = {}
        
        async def failing_handler(message: Dict[str, Any]) -> None:
            msg_id = message["id"]
            retry_count[msg_id] = retry_count.get(msg_id, 0) + 1
            
            if retry_count[msg_id] < max_retries:
                # Simulate failure
                raise Exception(f"Processing failed, attempt {retry_count[msg_id]}")
            else:
                # Send to DLQ
                await message_broker.publish(dlq, {
                    "original_message": message,
                    "error": "Max retries exceeded",
                    "attempts": retry_count[msg_id]
                })
        
        dlq_handler = TestMessageHandler()
        
        await message_broker.subscribe(main_queue, failing_handler)
        await message_broker.subscribe(dlq, dlq_handler.handle)
        
        await asyncio.sleep(0.1)
        
        # Act
        message = {"id": str(uuid4()), "data": "Important data"}
        
        # Simulate retries
        for _ in range(max_retries):
            try:
                await message_broker.publish(main_queue, message)
                await asyncio.sleep(0.1)
            except:
                pass
        
        await asyncio.sleep(0.3)
        
        # Assert - Message should end up in DLQ
        assert dlq_handler.processed_count == 1
        dlq_message = dlq_handler.messages[0]
        assert dlq_message["original_message"] == message
        assert dlq_message["attempts"] == max_retries