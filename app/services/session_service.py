"""
Session Service - Handles all session-related business logic.
Manages session persistence, context continuity, and idea processing.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.conversation_processor import ConversationProcessor
from app.services.monitoring import get_metrics_collector
from app.session_manager import SessionManager
from app.utils.logging_config import PerformanceLogger, get_logger

logger = get_logger(__name__)


class SessionService:
    """
    Service layer for session operations.
    Handles session management, idea processing, and context preservation.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        conversation_processor: ConversationProcessor,
        project_dashboard: Any
    ):
        self.session_manager = session_manager
        self.conversation_processor = conversation_processor
        self.project_dashboard = project_dashboard
        self.logger = logger  # Deprecated: use module logger instead

    async def ingest_idea(
        self, idea: str, source: str = "mobile", priority: str = "medium", context: str | None = None
    ) -> dict[str, Any]:
        """
        Process an idea through the woodchipper.

        Args:
            idea: The idea content
            source: Source of the idea (mobile, web, etc.)
            priority: Priority level
            context: Additional context

        Returns:
            Processing result with extracted features and updates
        """
        try:
            # Generate unique ID for the idea
            idea_id = f"idea_{uuid4().hex[:8]}"

            # Process idea to extract features
            features = self.conversation_processor.extract_features_from_idea(idea)

            # Update project dashboard
            dashboard_update = self.project_dashboard.process_idea_impact(
                idea=idea, features=features, priority=priority
            )

            # Add to session history
            self.session_manager.add_idea_to_session(idea_id=idea_id, idea=idea, source=source, features=features)

            # Prepare auto-updates
            auto_updates = {
                "roadmap": "updated" if features else "unchanged",
                "timeline": "adjusted" if priority == "high" else "reviewed",
                "documentation": "scheduled",
                "milestones": dashboard_update.get("milestones_affected", []),
            }

            self.logger.info(f"Processed idea {idea_id} with {len(features)} features detected")

            return {
                "idea_id": idea_id,
                "processed_at": datetime.utcnow().isoformat(),
                "detected_features": features,
                "auto_updates": auto_updates,
                "updated_dashboard": dashboard_update,
                "impact_summary": self._generate_impact_summary(features, priority),
            }

        except Exception as e:
                # Record failed metrics
                metrics_collector = get_metrics_collector()
                await metrics_collector.record_operation(
                    operation="idea_ingestion",
                    success=False,
                    labels={"source": source, "priority": priority}
                )

                logger.exception("Failed to process idea", extra={
                    "operation": "ingest_idea",
                    "source": source,
                    "priority": priority,
                    "idea_length": len(idea),
                    "error_type": type(e).__name__
                })
                raise

    async def pause_session(self, reason: str = "User requested") -> dict[str, Any]:
        """
        Pause the current session and generate resume context.

        Args:
            reason: Reason for pausing

        Returns:
            Resume context and session summary
        """
        with PerformanceLogger("session_pause", logger):
            logger.info("Pausing session", extra={
                "operation": "pause_session",
                "reason": reason
            })

            try:
                # Get current session state
                session_state = self.session_manager.get_current_session_state()

                # Generate comprehensive resume context
                resume_context = self.session_manager.generate_resume_context()

                # Save session state
                saved_session = self.session_manager.save_session(reason=reason)

                # Get analytics
                analytics = self.session_manager.get_session_analytics()

                logger.info("Session paused successfully", extra={
                    "operation": "pause_session",
                    "session_id": saved_session.get('session_id'),
                    "reason": reason
                })

                return {
                    "session_id": saved_session["session_id"],
                    "pause_reason": reason,
                    "resume_context": resume_context,
                    "session_analytics": analytics,
                    "conversation_summary": session_state.get("conversation_summary", ""),
                    "next_steps": session_state.get("next_steps", []),
                    "cost_savings": self._calculate_cost_savings(analytics),
                }

            except Exception as e:
                logger.exception("Failed to pause session", extra={
                    "operation": "pause_session",
                    "reason": reason,
                    "error_type": type(e).__name__
                })
                raise

    async def resume_session(
        self, session_id: str | None = None, device_context: str | None = None
    ) -> dict[str, Any]:
        """
        Resume a previously paused session.

        Args:
            session_id: Specific session to resume (or latest if None)
            device_context: Device/platform context

        Returns:
            Restored session information
        """
        try:
            # Resume the session
            resumed_session = self.session_manager.resume_session(session_id=session_id, device_context=device_context)

            # Restore project dashboard state
            self.project_dashboard.restore_state(resumed_session.get("dashboard_state", {}))

            # Get session context
            session_context = self.session_manager.get_current_session_context()

            self.logger.info(f"Session resumed: {resumed_session['session_id']}")

            return {
                "session_id": resumed_session["session_id"],
                "restored_context": session_context,
                "conversation_buffer": len(resumed_session.get("conversation_history", [])),
                "project_momentum": resumed_session.get("project_momentum", {}),
                "time_gap": self._calculate_time_gap(resumed_session),
                "synchronization_status": "complete",
            }

        except Exception as e:
            self.logger.error(f"Failed to resume session: {e}")
            raise

    async def process_conversation_message(self, message: str, context_type: str = "general") -> dict[str, Any]:
        """
        Process a conversation message for insights and updates.

        Args:
            message: Conversation content
            context_type: Type of conversation context

        Returns:
            Processing results
        """
        try:
            # Analyze conversation
            analysis = self.conversation_processor.analyze_conversation(message=message, context_type=context_type)

            # Update dashboard if relevant
            if analysis.get("is_relevant", False):
                dashboard_update = self.project_dashboard.update_from_conversation(analysis)
            else:
                dashboard_update = None

            # Add to session history
            self.session_manager.add_conversation_message(message=message, analysis=analysis)

            self.logger.info(f"Processed conversation message: {len(message)} chars")

            return {
                "analysis": analysis,
                "dashboard_updated": dashboard_update is not None,
                "detected_topics": analysis.get("topics", []),
                "action_items": analysis.get("action_items", []),
                "priority_changes": analysis.get("priority_changes", []),
            }

        except Exception as e:
            self.logger.error(f"Failed to process conversation: {e}")
            raise

    async def get_session_status(self) -> dict[str, Any]:
        """
        Get comprehensive session status and analytics.

        Returns:
            Current session status and metrics
        """
        try:
            # Get session analytics
            analytics = self.session_manager.get_session_analytics()

            # Get current state
            current_state = self.session_manager.get_current_session_state()

            # Get dashboard summary
            dashboard_summary = {}

            return {
                "session_analytics": analytics,
                "current_state": current_state,
                "dashboard_summary": dashboard_summary,
                "sync_status": {
                    "enabled": self.session_manager.sync_enabled,
                    "last_sync": self.session_manager.last_sync_time,
                    "pending_sync": len(self.session_manager.get_pending_sync_items()),
                },
                "capabilities": self._get_available_capabilities(),
            }

        except Exception as e:
            self.logger.error(f"Failed to get session status: {e}")
            raise

    def _generate_impact_summary(self, features: list[str], priority: str) -> str:
        """Generate a summary of the idea's impact on the project."""
        if not features:
            return "No specific features detected. Idea logged for future review."

        feature_count = len(features)
        impact_level = "high" if priority == "high" or feature_count > 3 else "medium"

        return (
            f"Detected {feature_count} feature(s) with {impact_level} impact. "
            f"Roadmap and timeline have been automatically updated."
        )

    def _calculate_cost_savings(self, analytics: dict[str, Any]) -> dict[str, Any]:
        """Calculate estimated cost savings from session pause."""
        session_duration = analytics.get("session_duration_minutes", 0)

        # Rough estimates for API costs
        cost_per_minute = 0.10  # $0.10 per minute for high-tier models
        saved_cost = session_duration * cost_per_minute

        return {
            "estimated_savings": f"${saved_cost:.2f}",
            "session_minutes": session_duration,
            "optimization_tips": [
                "Resume when ready to continue active development",
                "Use pause feature during breaks to minimize costs",
                "Session context fully preserved - no re-explanation needed",
            ],
        }

    def _calculate_time_gap(self, session: dict[str, Any]) -> str:
        """Calculate time elapsed since session was paused."""
        pause_time = session.get("pause_time")
        if not pause_time:
            return "Unknown"

        # Parse and calculate difference
        paused_at = datetime.fromisoformat(pause_time.replace("Z", "+00:00"))
        time_gap = datetime.utcnow() - paused_at.replace(tzinfo=None)

        hours = int(time_gap.total_seconds() // 3600)
        minutes = int((time_gap.total_seconds() % 3600) // 60)

        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    def _get_available_capabilities(self) -> list[str]:
        """Get list of available session capabilities."""
        return [
            "Pause and resume sessions with full context",
            "Process ideas through the woodchipper",
            "Track conversation insights",
            "Cross-device synchronization",
            "Real-time dashboard updates",
            "Cost optimization through pause/resume",
            "Project momentum tracking",
            "Automatic feature extraction",
        ]
