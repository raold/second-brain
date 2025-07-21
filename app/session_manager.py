#!/usr/bin/env python3
"""
Session State Manager - Persistent Context Continuity System
Preserves complete conversation context, project state, and coding momentum
across sessions, interruptions, and devices for seamless AI pair programming
"""

import gzip
import hashlib
import json
import uuid
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from app.conversation_processor import get_conversation_processor
from app.dashboard import get_dashboard


class SessionState(Enum):
    """Session states"""

    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    SYNCING = "syncing"


class ContextType(Enum):
    """Types of context to preserve"""

    CONVERSATION = "conversation"
    PROJECT_STATE = "project_state"
    ARCHITECTURAL_DECISIONS = "architectural_decisions"
    CODE_CHANGES = "code_changes"
    MOMENTUM = "momentum"
    PERSONALITY = "personality"


@dataclass
class ConversationMessage:
    """Individual conversation message with context"""

    id: str
    timestamp: str
    speaker: str  # "CTO", "Principal Engineer", "System"
    message: str
    context_type: str  # "planning", "implementation", "review", "architectural"
    detected_features: list[str]
    priorities: list[str]
    code_changes: list[str]
    semantic_summary: str  # AI-generated summary of key points
    emotional_tone: str  # "collaborative", "urgent", "exploratory", etc.


@dataclass
class ProjectMomentum:
    """Current project momentum and focus"""

    current_focus: str  # What we're actively working on
    next_logical_steps: list[str]  # What should happen next
    active_decisions: list[str]  # Decisions we're in the middle of making
    blocked_items: list[str]  # Things waiting for resolution
    energy_level: str  # "high", "medium", "low" - coding session energy
    last_major_achievement: str
    upcoming_deadlines: list[str]
    technical_context: str  # Current technical state/understanding


@dataclass
class CodingSession:
    """Complete coding session state"""

    session_id: str
    start_time: str
    end_time: Optional[str]
    state: SessionState
    conversation_history: list[ConversationMessage]
    project_momentum: ProjectMomentum
    dashboard_state: dict[str, Any]
    file_changes: dict[str, Any]  # Track all file modifications
    architectural_context: dict[str, Any]
    session_summary: str
    productivity_metrics: dict[str, Any]
    sync_hash: str  # For cross-device conflict resolution


class SessionManager:
    """
    Comprehensive session state management for persistent AI pair programming
    """

    def __init__(self, project_name: str = "Project Pipeline"):
        self.project_name = project_name
        self.sessions_dir = Path("session_storage")
        self.sessions_dir.mkdir(exist_ok=True)

        # Current session state
        self.current_session: Optional[CodingSession] = None
        self.session_buffer = deque(maxlen=1000)  # Rolling conversation buffer

        # Context preservation
        self.conversation_context = {}
        self.technical_context = {}
        self.momentum_tracker = {}

        # Cross-device sync
        self.sync_enabled = True
        self.last_sync_time = None

        # Initialize or resume session
        self.initialize_session_system()

    def initialize_session_system(self):
        """Initialize session management system"""
        print("Initializing Session State Management...")

        # Try to resume the last active session
        last_session = self.find_last_active_session()

        if last_session:
            print(f"Found previous session: {last_session.session_id}")
            self.resume_session(last_session.session_id)
        else:
            print("Starting new session")
            self.start_new_session()

        print("Session system ready for persistent context continuity")

    def start_new_session(self) -> str:
        """Start a new coding session"""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Get current project state
        dashboard = get_dashboard()
        dashboard_state = dashboard.get_dashboard_summary()

        # Initialize momentum tracker
        momentum = ProjectMomentum(
            current_focus="Initializing new session",
            next_logical_steps=["Assess project state", "Define session goals"],
            active_decisions=[],
            blocked_items=[],
            energy_level="high",
            last_major_achievement="Session system initialization",
            upcoming_deadlines=[],
            technical_context="Starting fresh with full project context",
        )

        # Create new session
        self.current_session = CodingSession(
            session_id=session_id,
            start_time=datetime.now().isoformat(),
            end_time=None,
            state=SessionState.ACTIVE,
            conversation_history=[],
            project_momentum=momentum,
            dashboard_state=dashboard_state,
            file_changes={},
            architectural_context={},
            session_summary="",
            productivity_metrics={
                "messages_processed": 0,
                "features_added": 0,
                "files_modified": 0,
                "decisions_made": 0,
            },
            sync_hash=self.generate_sync_hash(),
        )

        self.save_session_state()
        print(f"Started new session: {session_id}")
        return session_id

    def resume_session(self, session_id: str) -> bool:
        """Resume a previous session with full context"""
        try:
            session_file = self.sessions_dir / f"{session_id}.json.gz"

            if not session_file.exists():
                print(f"Error: Session {session_id} not found")
                return False

            # Load compressed session data
            with gzip.open(session_file, "rt") as f:
                session_data = json.load(f)

            # Reconstruct session object
            self.current_session = CodingSession(**session_data)
            self.current_session.state = SessionState.ACTIVE

            # Restore context
            self.restore_conversation_context()
            self.restore_project_momentum()
            self.restore_technical_context()

            print(f"Resumed session: {session_id}")
            print(f"Current focus: {self.current_session.project_momentum.current_focus}")
            print(f"Conversation history: {len(self.current_session.conversation_history)} messages")
            print(f"Productivity: {self.current_session.productivity_metrics}")

            return True

        except Exception as e:
            print(f"Error resuming session {session_id}: {e}")
            return False

    def pause_session(self, reason: str = "Manual pause") -> str:
        """Pause current session and preserve all context"""
        if not self.current_session:
            return "No active session to pause"

        # Update session state
        self.current_session.state = SessionState.PAUSED

        # Generate comprehensive session summary
        session_summary = self.generate_session_summary()
        self.current_session.session_summary = session_summary

        # Save current momentum and context
        self.update_project_momentum()
        self.save_session_state()

        # Create resume instructions
        resume_context = self.generate_resume_context()

        print(f"Session paused: {self.current_session.session_id}")
        print(f"Reason: {reason}")
        print("Resume context ready")

        return resume_context

    def generate_session_summary(self) -> str:
        """Generate AI-powered session summary for context preservation"""
        if not self.current_session:
            return "No active session"

        # Analyze conversation history
        recent_messages = self.current_session.conversation_history[-10:]

        summary_parts = [
            f"Session: {self.current_session.session_id}",
            f"Duration: {self.calculate_session_duration()}",
            f"Current Focus: {self.current_session.project_momentum.current_focus}",
            f"Messages Processed: {self.current_session.productivity_metrics['messages_processed']}",
            f"Features Added: {self.current_session.productivity_metrics['features_added']}",
            f"Files Modified: {self.current_session.productivity_metrics['files_modified']}",
        ]

        # Add recent conversation context
        if recent_messages:
            summary_parts.append("Recent Discussion:")
            for msg in recent_messages[-3:]:
                summary_parts.append(f"  - {msg.speaker}: {msg.semantic_summary}")

        # Add next steps
        if self.current_session.project_momentum.next_logical_steps:
            summary_parts.append("Next Steps:")
            for step in self.current_session.project_momentum.next_logical_steps:
                summary_parts.append(f"  - {step}")

        return "\n".join(summary_parts)

    def generate_resume_context(self) -> str:
        """Generate comprehensive context for seamless session resumption"""
        if not self.current_session:
            return "No session context available"

        context = f"""
SESSION RESUME CONTEXT - {self.current_session.session_id}
{'=' * 60}

WHERE WE LEFT OFF:
   Focus: {self.current_session.project_momentum.current_focus}
   Energy Level: {self.current_session.project_momentum.energy_level}
   Last Achievement: {self.current_session.project_momentum.last_major_achievement}

IMMEDIATE NEXT STEPS:
"""
        for i, step in enumerate(self.current_session.project_momentum.next_logical_steps, 1):
            context += f"   {i}. {step}\n"

        context += """
ACTIVE DECISIONS IN PROGRESS:
"""
        for decision in self.current_session.project_momentum.active_decisions:
            context += f"   • {decision}\n"

        if self.current_session.project_momentum.blocked_items:
            context += """
⚠️ BLOCKED ITEMS NEEDING ATTENTION:
"""
            for item in self.current_session.project_momentum.blocked_items:
                context += f"   • {item}\n"

        context += f"""
SESSION PRODUCTIVITY:
   • Messages: {self.current_session.productivity_metrics['messages_processed']}
   • Features: {self.current_session.productivity_metrics['features_added']}
   • Files: {self.current_session.productivity_metrics['files_modified']}
   • Decisions: {self.current_session.productivity_metrics['decisions_made']}

TECHNICAL CONTEXT:
   {self.current_session.project_momentum.technical_context}

CONVERSATION VIBE:
   Recent tone: {self.get_recent_emotional_tone()}
   Communication style: Collaborative technical discussion
   CTO-Principal Engineer pair programming dynamic

TO RESUME SEAMLESSLY:
   1. Load this context into memory
   2. Review current dashboard state
   3. Continue from: "{self.current_session.project_momentum.current_focus}"
   4. Address any blocked items first
   5. Proceed with next logical steps
"""

        return context

    def process_conversation_message(
        self, speaker: str, message: str, context_type: str = "general"
    ) -> ConversationMessage:
        """Process and store conversation message with full context"""

        # Analyze message content
        processor = get_conversation_processor()

        # Extract features and context (simplified for now)
        detected_features = []
        priorities = []

        # Create semantic summary
        semantic_summary = self.generate_semantic_summary(message)

        # Detect emotional tone
        emotional_tone = self.detect_emotional_tone(message)

        # Create conversation message
        conv_message = ConversationMessage(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now().isoformat(),
            speaker=speaker,
            message=message,
            context_type=context_type,
            detected_features=detected_features,
            priorities=priorities,
            code_changes=[],
            semantic_summary=semantic_summary,
            emotional_tone=emotional_tone,
        )

        # Add to session history
        if self.current_session:
            self.current_session.conversation_history.append(conv_message)
            self.current_session.productivity_metrics["messages_processed"] += 1

        # Add to rolling buffer
        self.session_buffer.append(conv_message)

        # Update momentum based on conversation
        self.update_momentum_from_conversation(conv_message)

        # Auto-save session state
        self.save_session_state()

        return conv_message

    def update_momentum_from_conversation(self, message: ConversationMessage):
        """Update project momentum based on conversation content"""
        if not self.current_session:
            return

        momentum = self.current_session.project_momentum

        # Update current focus based on conversation
        if "let's talk about" in message.message.lower():
            focus_match = message.message.lower().split("let's talk about")[-1].strip()
            momentum.current_focus = f"Discussing: {focus_match}"

        # Update energy level based on tone
        if message.emotional_tone == "urgent":
            momentum.energy_level = "high"
        elif message.emotional_tone == "exploratory":
            momentum.energy_level = "medium"

        # Add to next steps if action items mentioned
        action_words = ["implement", "build", "create", "add", "fix", "optimize"]
        for word in action_words:
            if word in message.message.lower():
                step = f"Continue {word}ing from conversation"
                if step not in momentum.next_logical_steps:
                    momentum.next_logical_steps.append(step)

        # Update technical context
        if message.context_type == "architectural":
            momentum.technical_context = f"Architectural discussion: {message.semantic_summary}"

    def generate_semantic_summary(self, message: str) -> str:
        """Generate semantic summary of message content"""
        # Simplified semantic analysis
        if len(message) < 100:
            return message

        # Extract key concepts
        key_phrases = []
        if "implement" in message.lower():
            key_phrases.append("implementation discussion")
        if "architecture" in message.lower():
            key_phrases.append("architectural planning")
        if "priority" in message.lower():
            key_phrases.append("priority setting")

        if not key_phrases:
            return message[:100] + "..."

        return f"{', '.join(key_phrases)}: {message[:50]}..."

    def detect_emotional_tone(self, message: str) -> str:
        """Detect emotional tone of conversation"""
        message_lower = message.lower()

        if any(word in message_lower for word in ["critical", "urgent", "asap", "immediately"]):
            return "urgent"
        elif any(word in message_lower for word in ["explore", "consider", "maybe", "what if"]):
            return "exploratory"
        elif any(word in message_lower for word in ["great", "awesome", "perfect", "excellent"]):
            return "positive"
        elif any(word in message_lower for word in ["problem", "issue", "error", "broken"]):
            return "concerned"
        else:
            return "collaborative"

    def get_recent_emotional_tone(self) -> str:
        """Get the recent emotional tone of the conversation"""
        if not self.current_session or not self.current_session.conversation_history:
            return "neutral"

        recent_messages = self.current_session.conversation_history[-5:]
        tones = [msg.emotional_tone for msg in recent_messages]

        # Return most common tone
        return max(set(tones), key=tones.count) if tones else "neutral"

    def ingest_mobile_idea(self, idea: str, source: str = "mobile") -> dict[str, Any]:
        """
        The "woodchipper" function - automatically process ideas from mobile/remote
        and integrate them into the project pipeline
        """
        print(f"IDEA INGESTION: Processing idea from {source}")
        print(f"Idea: {idea}")

        # Process the idea through conversation processor
        processor = get_conversation_processor()

        # Create a special "idea ingestion" conversation message
        conv_message = self.process_conversation_message(
            speaker="CTO (Remote)", message=idea, context_type="idea_ingestion"
        )

        # Auto-process through dashboard system
        dashboard = get_dashboard()

        # Extract and classify the idea
        result = {
            "idea_id": conv_message.id,
            "processed_at": datetime.now().isoformat(),
            "source": source,
            "original_idea": idea,
            "semantic_summary": conv_message.semantic_summary,
            "detected_features": conv_message.detected_features,
            "auto_updates": {},
        }

        # Automatically update project components
        if conv_message.detected_features:
            # Add features to roadmap
            for feature in conv_message.detected_features:
                milestone_id = dashboard.add_new_feature_context(feature, f"Idea ingested from {source}: {idea}")
                result["auto_updates"][feature] = milestone_id

        # Update session momentum
        if self.current_session:
            momentum = self.current_session.project_momentum
            momentum.next_logical_steps.append(f"Review and prioritize idea: {conv_message.semantic_summary}")
            momentum.current_focus = f"Processing remote idea: {conv_message.semantic_summary}"

        # Generate updated dashboard state
        updated_dashboard = dashboard.generate_visual_report()
        result["updated_dashboard"] = updated_dashboard

        print("AUTOMATIC UPDATES COMPLETED:")
        print(f"   • Features detected: {len(conv_message.detected_features)}")
        print(f"   • Roadmap updates: {len(result['auto_updates'])}")
        print("   • Session momentum updated")
        print("   • Dashboard refreshed")

        return result

    def save_session_state(self):
        """Save current session state with compression"""
        if not self.current_session:
            return

        try:
            # Update sync hash
            self.current_session.sync_hash = self.generate_sync_hash()

            # Convert to dict for JSON serialization
            session_dict = asdict(self.current_session)

            # Save compressed session file
            session_file = self.sessions_dir / f"{self.current_session.session_id}.json.gz"
            with gzip.open(session_file, "wt") as f:
                json.dump(session_dict, f, indent=2, default=str)

            # Save quick resume file (uncompressed for fast access)
            resume_file = self.sessions_dir / "last_session.json"
            resume_data = {
                "session_id": self.current_session.session_id,
                "last_active": datetime.now().isoformat(),
                "resume_context": self.generate_resume_context(),
                "quick_summary": self.generate_session_summary(),
            }

            with open(resume_file, "w") as f:
                json.dump(resume_data, f, indent=2)

        except Exception as e:
            print(f"Error saving session state: {e}")

    def find_last_active_session(self) -> Optional[CodingSession]:
        """Find the last active session for resumption"""
        try:
            resume_file = self.sessions_dir / "last_session.json"
            if not resume_file.exists():
                return None

            with open(resume_file) as f:
                resume_data = json.load(f)

            session_id = resume_data["session_id"]
            session_file = self.sessions_dir / f"{session_id}.json.gz"

            if not session_file.exists():
                return None

            with gzip.open(session_file, "rt") as f:
                session_data = json.load(f)

            return CodingSession(**session_data)

        except Exception as e:
            print(f"Warning: Could not load last session: {e}")
            return None

    def generate_sync_hash(self) -> str:
        """Generate hash for cross-device sync conflict resolution"""
        if not self.current_session:
            return ""

        # Create hash based on session content
        content = f"{self.current_session.session_id}{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def calculate_session_duration(self) -> str:
        """Calculate human-readable session duration"""
        if not self.current_session:
            return "0 minutes"

        start = datetime.fromisoformat(self.current_session.start_time)
        end = datetime.now()
        duration = end - start

        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def restore_conversation_context(self):
        """Restore conversation context from session"""
        if not self.current_session:
            return

        # Rebuild conversation buffer
        self.session_buffer.clear()
        for msg in self.current_session.conversation_history[-100:]:  # Last 100 messages
            self.session_buffer.append(msg)

        print(f"Restored {len(self.session_buffer)} conversation messages")

    def restore_project_momentum(self):
        """Restore project momentum and focus"""
        if not self.current_session:
            return

        momentum = self.current_session.project_momentum
        print("Restored project momentum:")
        print(f"   Current focus: {momentum.current_focus}")
        print(f"   Energy level: {momentum.energy_level}")
        print(f"   Next steps: {len(momentum.next_logical_steps)}")

    def restore_technical_context(self):
        """Restore technical context and architectural decisions"""
        if not self.current_session:
            return

        context = self.current_session.architectural_context
        print(f"Restored technical context: {len(context)} items")

    def update_project_momentum(self):
        """Update project momentum before pausing"""
        if not self.current_session:
            return

        momentum = self.current_session.project_momentum

        # Update based on recent activity
        recent_messages = self.current_session.conversation_history[-5:]
        if recent_messages:
            last_message = recent_messages[-1]
            momentum.current_focus = f"Last discussed: {last_message.semantic_summary}"

        # Update technical context
        dashboard = get_dashboard()
        dashboard_summary = dashboard.get_dashboard_summary()
        momentum.technical_context = f"Dashboard state at pause: {dashboard_summary['overall_health']['status']}"

    def get_session_analytics(self) -> dict[str, Any]:
        """Get comprehensive session analytics"""
        if not self.current_session:
            return {"error": "No active session"}

        return {
            "session_id": self.current_session.session_id,
            "duration": self.calculate_session_duration(),
            "state": self.current_session.state.value,
            "productivity_metrics": self.current_session.productivity_metrics,
            "conversation_summary": {
                "total_messages": len(self.current_session.conversation_history),
                "speakers": list(set(msg.speaker for msg in self.current_session.conversation_history)),
                "emotional_tone": self.get_recent_emotional_tone(),
                "context_types": list(set(msg.context_type for msg in self.current_session.conversation_history)),
            },
            "momentum": asdict(self.current_session.project_momentum),
            "sync_status": {
                "last_sync": self.last_sync_time,
                "sync_hash": self.current_session.sync_hash,
                "sync_enabled": self.sync_enabled,
            },
        }


# Global session manager instance
_session_manager_instance = None


def get_session_manager() -> SessionManager:
    """Get or create global session manager instance"""
    global _session_manager_instance
    if _session_manager_instance is None:
        _session_manager_instance = SessionManager()
    return _session_manager_instance


def ingest_idea(idea: str, source: str = "mobile") -> dict[str, Any]:
    """Main entry point for idea ingestion - the "woodchipper" function"""
    session_manager = get_session_manager()
    return session_manager.ingest_mobile_idea(idea, source)


def pause_and_preserve_context(reason: str = "Manual pause") -> str:
    """Pause session and generate resume context"""
    session_manager = get_session_manager()
    return session_manager.pause_session(reason)


def resume_coding_session(session_id: Optional[str] = None) -> bool:
    """Resume coding session with full context"""
    session_manager = get_session_manager()
    if session_id:
        return session_manager.resume_session(session_id)
    else:
        # Resume last active session
        last_session = session_manager.find_last_active_session()
        if last_session:
            return session_manager.resume_session(last_session.session_id)
        return False


if __name__ == "__main__":
    # Demo session management
    print("Session Management Demo")
    print("=" * 50)

    # Initialize session manager
    session_manager = SessionManager()

    # Simulate some conversation
    session_manager.process_conversation_message("CTO", "lets talk about automated importance scoring", "planning")

    session_manager.process_conversation_message(
        "Principal Engineer", "I'll design the importance algorithm with machine learning", "implementation"
    )

    # Test idea ingestion
    idea_result = session_manager.ingest_mobile_idea(
        "Add real-time collaboration features with live cursor tracking", "mobile_app"
    )

    print("\nIdea ingestion result:")
    print(f"   Features detected: {len(idea_result['detected_features'])}")
    print(f"   Auto updates: {len(idea_result['auto_updates'])}")

    # Pause session and generate resume context
    resume_context = session_manager.pause_session("Demo complete")
    print("\nSession paused. Resume context:")
    print(resume_context[:500] + "...")

    # Show session analytics
    analytics = session_manager.get_session_analytics()
    print("\nSession Analytics:")
    print(f"   Duration: {analytics['duration']}")
    print(f"   Messages: {analytics['conversation_summary']['total_messages']}")
    print(f"   Productivity: {analytics['productivity_metrics']}")
