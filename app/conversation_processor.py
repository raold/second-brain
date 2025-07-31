#!/usr/bin/env python3
"""
Conversation Processor - Automatic Dashboard Updates
Monitors conversation context and automatically updates project dashboard
when CTO discusses new features, architectural challenges, or project goals
"""

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.docs import Priority
from typing import Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ConversationContext:
    """Structured conversation context"""

    speaker: str
    message: str
    timestamp: str
    detected_features: list[str]
    priorities: list[str]
    architectural_elements: list[str]
    timeline_mentions: list[str]


class ConversationProcessor:
    """
    Intelligent conversation processor that detects project-related discussions
    and automatically updates the dashboard with new goals, features, and timelines
    """

    def __init__(self):
        self.dashboard = None

        # Enhanced pattern matching for feature detection
        self.feature_patterns = [
            # Direct feature discussions
            r"(?:let'?s talk about|discuss|implement|add|create|build) (?:the )?(.+?)(?:\s(?:feature|system|component|module)|$)",
            r"(?:we need|i want|let'?s build|should implement) (?:a |an |the )?(.+?)(?:\s|$)",
            r"(?:new feature|feature) (?:called |named |for )?(.+?)(?:\s|$)",
            # Automated/AI features
            r"(?:automated|automatic|ai|machine learning|smart) (.+?)(?:\s|$)",
            r"(?:auto|intelligent|adaptive) (.+?)(?:\s|$)",
            # Technical components
            r"(?:algorithm|engine|processor|analyzer|detector|classifier) (?:for )?(.+?)(?:\s|$)",
            r"(.+?) (?:algorithm|engine|processor|analyzer|detector|classifier)(?:\s|$)",
            # Process improvements
            r"(?:optimize|improve|enhance|upgrade) (?:the )?(.+?)(?:\s|$)",
            r"(.+?) (?:optimization|improvement|enhancement|upgrade)(?:\s|$)",
            # Integration features
            r"(?:integrate|connect|link) (?:with |to )?(.+?)(?:\s|$)",
            r"(.+?) (?:integration|connection|interface)(?:\s|$)",
        ]

        # Priority detection patterns
        self.priority_patterns = {
            "critical": [r"critical", r"urgent", r"asap", r"immediately", r"emergency"],
            "high": [r"high priority", r"important", r"soon", r"next sprint", r"this week"],
            "medium": [r"medium", r"moderate", r"when possible", r"next month"],
            "low": [r"low priority", r"eventually", r"nice to have", r"future", r"someday"],
        }

        # Architectural element detection
        self.architectural_patterns = [
            r"(?:architecture|design|pattern|framework|structure) (?:for )?(.+?)(?:\s|$)",
            r"(.+?) (?:architecture|design|pattern|framework|structure)(?:\s|$)",
            r"(?:microservice|api|database|queue|cache|storage) (?:for )?(.+?)(?:\s|$)",
            r"(.+?) (?:microservice|api|database|queue|cache|storage)(?:\s|$)",
        ]

        # Timeline detection patterns
        self.timeline_patterns = [
            r"(?:in|within|by|before) (?:the )?(\d+) (?:day|week|month|sprint)s?",
            r"(?:next|this) (week|month|quarter|sprint)",
            r"(?:by|before) (.+?)(?:\s|$)",
            r"deadline (?:is |of )?(.+?)(?:\s|$)",
        ]

    async def process_message(self, speaker: str, message: str) -> ConversationContext:
        """
        Process a conversation message and extract project-relevant information
        """
        context = ConversationContext(
            speaker=speaker,
            message=message,
            timestamp=datetime.now().isoformat(),
            detected_features=[],
            priorities=[],
            architectural_elements=[],
            timeline_mentions=[],
        )

        # Detect features
        context.detected_features = self._extract_features(message)

        # Detect priorities
        context.priorities = self._extract_priorities(message)

        # Detect architectural elements
        context.architectural_elements = self._extract_architectural_elements(message)

        # Detect timeline mentions
        context.timeline_mentions = self._extract_timelines(message)

        return context

    def _extract_features(self, message: str) -> list[str]:
        """Extract feature names from conversation message"""
        detected_features = []
        message_lower = message.lower()

        for pattern in self.feature_patterns:
            matches = re.findall(pattern, message_lower, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = " ".join(match)

                # Clean up the match
                feature_name = self._clean_feature_name(match)
                if feature_name and len(feature_name) > 3 and feature_name not in detected_features:
                    detected_features.append(feature_name)

        return detected_features

    def _clean_feature_name(self, raw_name: str) -> str:
        """Clean and format detected feature name"""
        # Remove common stop words and clean up
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "this",
            "that",
            "these",
            "those",
        }

        # Split into words and filter
        words = [word.strip(".,!?()[]{}") for word in raw_name.split()]
        filtered_words = [word for word in words if word.lower() not in stop_words and len(word) > 1]

        if not filtered_words:
            return ""

        # Join and title case
        feature_name = " ".join(filtered_words).title()

        # Limit length
        if len(feature_name) > 50:
            feature_name = feature_name[:47] + "..."

        return feature_name

    def _extract_priorities(self, message: str) -> list[str]:
        """Extract priority indicators from message"""
        detected_priorities = []
        message_lower = message.lower()

        for priority, patterns in self.priority_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    detected_priorities.append(priority)
                    break

        return detected_priorities

    def _extract_architectural_elements(self, message: str) -> list[str]:
        """Extract architectural elements from message"""
        detected_elements = []
        message_lower = message.lower()

        for pattern in self.architectural_patterns:
            matches = re.findall(pattern, message_lower, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = " ".join(match)

                element = self._clean_feature_name(match)
                if element and len(element) > 3 and element not in detected_elements:
                    detected_elements.append(element)

        return detected_elements

    def _extract_timelines(self, message: str) -> list[str]:
        """Extract timeline mentions from message"""
        detected_timelines = []
        message_lower = message.lower()

        for pattern in self.timeline_patterns:
            matches = re.findall(pattern, message_lower, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = " ".join(match)
                detected_timelines.append(match.strip())

        return detected_timelines

    async def auto_update_dashboard(self, context: ConversationContext) -> dict[str, Any]:
        """
        Automatically update dashboard based on conversation context
        This is the core feature that makes the dashboard "live updating"
        """
        updates = {
            "features_added": [],
            "priorities_updated": [],
            "timelines_adjusted": [],
            "architectural_decisions": [],
        }

        # Process detected features
        for feature_name in context.detected_features:
            # Determine priority
            priority = Priority.HIGH  # Default
            if "critical" in context.priorities:
                priority = Priority.CRITICAL
            elif "low" in context.priorities:
                priority = Priority.LOW
            elif "medium" in context.priorities:
                priority = Priority.MEDIUM

            # Generate description with context
            description = self._generate_feature_description(
                feature_name, context.message, context.architectural_elements, context.timeline_mentions
            )

            # Add to dashboard
            milestone_id = self.dashboard.add_new_feature_context(feature_name, description, priority)

            updates["features_added"].append(
                {
                    "name": feature_name,
                    "milestone_id": milestone_id,
                    "priority": priority.value,
                    "description": description,
                }
            )

        # Update metrics based on conversation
        if context.detected_features:
            # Record conversation-driven feature addition metric
            self.dashboard.record_metric(
                "conversation_driven_features", len(context.detected_features), "features", target=None
            )

        return updates

    def _generate_feature_description(
        self, feature_name: str, original_message: str, architectural_elements: list[str], timeline_mentions: list[str]
    ) -> str:
        """Generate rich feature description based on conversation context"""

        description_parts = [f"Feature discussed in conversation: {feature_name}"]

        # Add context from original message
        if len(original_message) < 200:
            description_parts.append(f"Context: {original_message}")
        else:
            description_parts.append(f"Context: {original_message[:197]}...")

        # Add architectural context
        if architectural_elements:
            description_parts.append(f"Architectural elements: {', '.join(architectural_elements)}")

        # Add timeline context
        if timeline_mentions:
            description_parts.append(f"Timeline considerations: {', '.join(timeline_mentions)}")

        return " | ".join(description_parts)

    async def simulate_cto_conversation(self, message: str) -> dict[str, Any]:
        """
        Simulate CTO conversation for demonstration
        This shows how the system responds to executive discussions
        """
        context = await self.process_message("CTO", message)
        updates = await self.auto_update_dashboard(context)

        return {
            "conversation_context": context,
            "dashboard_updates": updates,
            "summary": f"Processed CTO message and detected {len(context.detected_features)} features",
        }

    def get_conversation_intelligence_summary(self) -> dict[str, Any]:
        """
        Get summary of conversation-driven intelligence and dashboard updates
        """
        return {
            "processor_status": "active",
            "features_detected_today": len(
                [
                    m
                    for m in self.dashboard.milestones.values()
                    if "conversation" in m.description.lower()
                    and datetime.fromisoformat(m.created_at).date() == datetime.now().date()
                ]
            ),
            "conversation_patterns": {
                "feature_patterns": len(self.feature_patterns),
                "priority_patterns": sum(len(p) for p in self.priority_patterns.values()),
                "architectural_patterns": len(self.architectural_patterns),
                "timeline_patterns": len(self.timeline_patterns),
            },
            "last_processed": datetime.now().isoformat(),
        }


# Global processor instance
_processor_instance = None


def get_conversation_processor() -> ConversationProcessor:
    """Get or create global conversation processor instance"""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = ConversationProcessor()
    return _processor_instance


async def process_cto_message(message: str) -> dict[str, Any]:
    """
    Main entry point for processing CTO messages
    This function should be called whenever the CTO discusses project features
    """
    processor = get_conversation_processor()
    return await processor.simulate_cto_conversation(message)


def setup_conversation_monitoring():
    """
    Setup conversation monitoring (would integrate with actual conversation systems)
    For now, this provides the framework for integration
    """
    processor = get_conversation_processor()

    # This is where you would integrate with:
    # - Slack/Teams monitoring
    # - Meeting transcription services
    # - Voice assistant integration
    # - Email parsing
    # - Chat application hooks

    print("Conversation monitoring setup complete")
    print("Dashboard will auto-update when CTO discusses:")
    print("   - New features and capabilities")
    print("   - Architectural challenges")
    print("   - Project priorities and timelines")
    print("   - Technical improvements")

    return processor


if __name__ == "__main__":
    # Demo conversation processing

    async def demo():
        processor = ConversationProcessor()

        # Simulate CTO discussions
        test_messages = [
            "lets talk about Automated importance scoring",
            "we need to implement real-time analytics dashboard with machine learning",
            "I want to build an intelligent memory consolidation system",
            "critical priority: automated testing pipeline with CI/CD integration",
            "next sprint we should add smart notification system",
        ]

        print("🎯 CONVERSATION PROCESSOR DEMO")
        print("=" * 50)

        for message in test_messages:
            print(f"\n💬 CTO: {message}")
            result = await processor.simulate_cto_conversation(message)

            print(f"🔍 Detected features: {result['conversation_context'].detected_features}")
            print(f"📊 Dashboard updates: {len(result['dashboard_updates']['features_added'])} new features")

        print("\n📈 Final dashboard state:")
        dashboard = None
        print(dashboard.generate_visual_report())

    asyncio.run(demo())
