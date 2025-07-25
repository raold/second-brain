"""
RabbitMQ message broker implementation.

Handles connection management and message routing.
"""

import asyncio
import json
from typing import Any, Callable, Optional

import aio_pika
from aio_pika import DeliveryMode, ExchangeType

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class MessageBroker:
    """RabbitMQ message broker for async event processing."""
    
    def __init__(
        self,
        url: str,
        exchange_name: str = "secondbrain.events",
        queue_prefix: str = "secondbrain",
    ):
        """
        Initialize message broker.
        
        Args:
            url: RabbitMQ connection URL
            exchange_name: Name of the exchange
            queue_prefix: Prefix for queue names
        """
        self.url = url
        self.exchange_name = exchange_name
        self.queue_prefix = queue_prefix
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        self._consumers: dict[str, asyncio.Task] = {}
    
    async def connect(self) -> None:
        """Connect to RabbitMQ."""
        try:
            self.connection = await aio_pika.connect_robust(
                self.url,
                client_properties={
                    "connection_name": "secondbrain-app",
                },
            )
            
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name,
                ExchangeType.TOPIC,
                durable=True,
            )
            
            logger.info(f"Connected to RabbitMQ at {self.url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from RabbitMQ."""
        # Cancel all consumers
        for task in self._consumers.values():
            task.cancel()
        
        if self._consumers:
            await asyncio.gather(*self._consumers.values(), return_exceptions=True)
        
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("Disconnected from RabbitMQ")
    
    async def publish(
        self,
        routing_key: str,
        message: dict[str, Any],
        persistent: bool = True,
    ) -> None:
        """
        Publish a message to the exchange.
        
        Args:
            routing_key: Routing key for the message
            message: Message payload
            persistent: Whether to persist the message
        """
        if not self.exchange:
            raise RuntimeError("Not connected to RabbitMQ")
        
        body = json.dumps(message).encode()
        
        await self.exchange.publish(
            aio_pika.Message(
                body=body,
                delivery_mode=DeliveryMode.PERSISTENT if persistent else DeliveryMode.NOT_PERSISTENT,
                content_type="application/json",
            ),
            routing_key=routing_key,
        )
        
        logger.debug(f"Published message to {routing_key}")
    
    async def subscribe(
        self,
        routing_key: str,
        handler: Callable[[dict[str, Any]], Any],
        queue_name: Optional[str] = None,
    ) -> None:
        """
        Subscribe to messages with a specific routing key.
        
        Args:
            routing_key: Routing key pattern to subscribe to
            handler: Async function to handle messages
            queue_name: Optional queue name (auto-generated if not provided)
        """
        if not self.channel or not self.exchange:
            raise RuntimeError("Not connected to RabbitMQ")
        
        # Create queue
        if not queue_name:
            queue_name = f"{self.queue_prefix}.{routing_key.replace('*', 'star').replace('#', 'hash')}"
        
        queue = await self.channel.declare_queue(
            queue_name,
            durable=True,
            arguments={
                "x-message-ttl": 86400000,  # 24 hours
                "x-max-length": 10000,  # Max 10k messages
            },
        )
        
        # Bind queue to exchange
        await queue.bind(self.exchange, routing_key)
        
        # Start consuming
        async def process_message(message: aio_pika.IncomingMessage) -> None:
            """Process incoming message."""
            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    await handler(data)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Requeue message on error
                    await message.nack(requeue=True)
        
        # Start consumer
        consumer = await queue.consume(process_message)
        task = asyncio.create_task(self._consume_forever(consumer))
        self._consumers[queue_name] = task
        
        logger.info(f"Subscribed to {routing_key} on queue {queue_name}")
    
    async def _consume_forever(self, consumer: Any) -> None:
        """Keep consumer running."""
        try:
            await asyncio.Future()  # Run forever
        except asyncio.CancelledError:
            await consumer.cancel()
    
    async def __aenter__(self) -> "MessageBroker":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()


# Singleton instance
_message_broker: Optional[MessageBroker] = None


async def get_message_broker(url: str) -> MessageBroker:
    """
    Get or create message broker instance.
    
    Args:
        url: RabbitMQ connection URL
        
    Returns:
        Message broker instance
    """
    global _message_broker
    
    if _message_broker is None:
        _message_broker = MessageBroker(url)
        await _message_broker.connect()
    
    return _message_broker