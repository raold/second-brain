"""Spaced repetition scheduler for memory review"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SpacedRepetitionEngine:
    """Engine for spaced repetition algorithm"""
    
    def __init__(self):
        self.default_intervals = [1, 3, 7, 14, 30, 90]  # Days
    
    def calculate_next_review(self, difficulty: int, previous_interval: int = 0) -> int:
        """Calculate next review interval based on difficulty"""
        if previous_interval == 0:
            return self.default_intervals[0]
        
        # Simple algorithm: easier items have longer intervals
        multiplier = {
            1: 2.5,    # Very easy
            2: 2.0,    # Easy
            3: 1.5,    # Medium
            4: 1.0,    # Hard
            5: 0.5     # Very hard
        }.get(difficulty, 1.0)
        
        return int(previous_interval * multiplier)


class RepetitionScheduler:
    """Scheduler for spaced repetition reviews"""
    
    def __init__(self):
        self.engine = SpacedRepetitionEngine()
        self.schedules = {}
    
    async def schedule_review(self, memory_id: str, difficulty: int = 3) -> Dict[str, Any]:
        """Schedule a memory for review"""
        current_schedule = self.schedules.get(memory_id, {})
        previous_interval = current_schedule.get("interval", 0)
        
        next_interval = self.engine.calculate_next_review(difficulty, previous_interval)
        next_review = datetime.utcnow() + timedelta(days=next_interval)
        
        schedule = {
            "memory_id": memory_id,
            "next_review": next_review.isoformat(),
            "interval": next_interval,
            "difficulty": difficulty,
            "review_count": current_schedule.get("review_count", 0) + 1
        }
        
        self.schedules[memory_id] = schedule
        return schedule
    
    async def get_due_reviews(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get memories due for review"""
        now = datetime.utcnow()
        due_reviews = []
        
        for memory_id, schedule in self.schedules.items():
            next_review = datetime.fromisoformat(schedule["next_review"])
            if next_review <= now:
                due_reviews.append({
                    "memory_id": memory_id,
                    "overdue_days": (now - next_review).days,
                    **schedule
                })
        
        # Sort by most overdue first
        due_reviews.sort(key=lambda x: x["overdue_days"], reverse=True)
        return due_reviews[:limit]
    
    async def bulk_review(self, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process multiple reviews at once"""
        results = []
        
        for review in reviews:
            memory_id = review["memory_id"]
            difficulty = review.get("difficulty", 3)
            schedule = await self.schedule_review(memory_id, difficulty)
            results.append(schedule)
        
        return {
            "reviewed": len(results),
            "results": results
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get repetition statistics"""
        total_scheduled = len(self.schedules)
        due_count = len(await self.get_due_reviews(limit=1000))
        
        return {
            "total_scheduled": total_scheduled,
            "due_for_review": due_count,
            "completion_rate": (total_scheduled - due_count) / max(total_scheduled, 1)
        }


class ReportGeneratorConfig:
    """Configuration for report generation"""
    
    def __init__(self, **kwargs):
        self.include_statistics = kwargs.get("include_statistics", True)
        self.include_graphs = kwargs.get("include_graphs", False)
        self.time_range = kwargs.get("time_range", "last_30_days")
        self.format = kwargs.get("format", "pdf")