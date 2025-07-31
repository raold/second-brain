"""Domain classifier for content categorization"""

from typing import Dict, List, Optional
from app.utils.logging_config import get_logger
logger = get_logger(__name__)


class DomainClassifier:
    """Classifies content into knowledge domains"""
    
    def __init__(self):
        """Initialize domain classifier"""
        self.domains = {
            "technology": ["programming", "software", "hardware", "AI", "ML", "data", "algorithm"],
            "science": ["physics", "chemistry", "biology", "research", "experiment", "theory"],
            "business": ["strategy", "management", "finance", "marketing", "sales", "startup"],
            "personal": ["health", "fitness", "productivity", "learning", "goals", "habits"],
            "creative": ["art", "music", "writing", "design", "creativity", "inspiration"]
        }
    
    async def classify(self, content: str) -> Dict[str, float]:
        """Classify content into domains
        
        Args:
            content: Text content to classify
            
        Returns:
            Dictionary of domain scores
        """
        content_lower = content.lower()
        scores = {}
        
        for domain, keywords in self.domains.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                scores[domain] = min(score / len(keywords), 1.0)
        
        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            scores = {k: v/total for k, v in scores.items()}
        
        return scores
    
    def get_primary_domain(self, scores: Dict[str, float]) -> Optional[str]:
        """Get the primary domain from scores
        
        Args:
            scores: Domain scores
            
        Returns:
            Primary domain name or None
        """
        if not scores:
            return None
        
        return max(scores.items(), key=lambda x: x[1])[0]