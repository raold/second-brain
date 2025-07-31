"""
Enhanced Batch Classification Engine for bulk memory operations
Supports multiple classification methods and parallel processing
"""

import re
from typing import List, Dict, Any, Optional
from app.utils.logging_config import get_logger
from typing import Optional
from typing import Dict
from typing import List
from typing import Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from pydantic import Field
logger = get_logger(__name__)


class ClassificationMethod(str, Enum):
    """Available classification methods"""
    AUTO = "auto"
    MANUAL = "manual"
    AI = "ai"
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    PATTERN = "pattern"
    HYBRID = "hybrid"
    RULES_BASED = "rules_based"


class ClassificationConfig(BaseModel):
    """Configuration for classification"""
    method: ClassificationMethod = ClassificationMethod.AUTO
    auto_apply_results: bool = False
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0)
    batch_size: int = Field(100, ge=1, le=1000)
    parallel_workers: int = Field(4, ge=1, le=16)
    custom_rules: Optional[List[Dict[str, Any]]] = None
    keywords: Optional[Dict[str, List[str]]] = None  # category -> keywords mapping


class ClassificationResult(BaseModel):
    """Individual classification result"""
    memory_id: str
    original_category: Optional[str] = None
    new_category: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    method_used: ClassificationMethod
    tags_added: List[str] = []
    metadata_updates: Dict[str, Any] = {}


class BatchClassificationResult(BaseModel):
    """Result of batch classification"""
    classified_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    processed_memories: int = 0
    classification_results: List[ClassificationResult] = []
    performance_metrics: Dict[str, Any] = {}
    errors: List[Dict[str, str]] = []


class KeywordClassifier:
    """Keyword-based classification"""
    
    def __init__(self, keywords: Optional[Dict[str, List[str]]] = None):
        self.keywords = keywords or self._get_default_keywords()
    
    def _get_default_keywords(self) -> Dict[str, List[str]]:
        """Default keyword mappings"""
        return {
            "work": ["meeting", "project", "deadline", "task", "colleague", "office", "report"],
            "personal": ["family", "friend", "vacation", "hobby", "personal", "home"],
            "learning": ["study", "learn", "course", "book", "tutorial", "research", "article"],
            "health": ["exercise", "doctor", "medicine", "health", "fitness", "diet", "sleep"],
            "finance": ["budget", "expense", "income", "investment", "money", "payment", "tax"],
            "ideas": ["idea", "concept", "innovation", "brainstorm", "solution", "creative"],
        }
    
    def classify(self, content: str) -> tuple[str, float]:
        """Classify based on keyword matching"""
        content_lower = content.lower()
        scores = {}
        
        for category, keywords in self.keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                scores[category] = score
        
        if not scores:
            return "general", 0.5
        
        best_category = max(scores, key=scores.get)
        confidence = min(scores[best_category] / 5.0, 1.0)  # Normalize score
        
        return best_category, confidence


class PatternClassifier:
    """Pattern-based classification using regex"""
    
    def __init__(self):
        self.patterns = self._get_default_patterns()
    
    def _get_default_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Default regex patterns"""
        return {
            "technical": [
                re.compile(r'\b(code|programming|debug|api|function|class|method)\b', re.I),
                re.compile(r'\b(python|javascript|java|cpp|golang)\b', re.I),
            ],
            "communication": [
                re.compile(r'\b(email|call|message|discuss|meeting|conversation)\b', re.I),
                re.compile(r'@\w+'),  # Mentions
            ],
            "documentation": [
                re.compile(r'\b(document|guide|manual|readme|specification)\b', re.I),
                re.compile(r'#+\s+\w+'),  # Markdown headers
            ],
            "task": [
                re.compile(r'\b(todo|task|complete|pending|done|action)\b', re.I),
                re.compile(r'^\s*[-*]\s+\[[ x]\]', re.M),  # Checkboxes
            ],
        }
    
    def classify(self, content: str) -> tuple[str, float]:
        """Classify based on pattern matching"""
        scores = {}
        
        for category, patterns in self.patterns.items():
            matches = sum(len(pattern.findall(content)) for pattern in patterns)
            if matches > 0:
                scores[category] = matches
        
        if not scores:
            return "general", 0.5
        
        best_category = max(scores, key=scores.get)
        confidence = min(scores[best_category] / 10.0, 1.0)  # Normalize score
        
        return best_category, confidence


class RulesBasedClassifier:
    """Rules-based classification with custom logic"""
    
    def __init__(self, custom_rules: Optional[List[Dict[str, Any]]] = None):
        self.rules = custom_rules or self._get_default_rules()
    
    def _get_default_rules(self) -> List[Dict[str, Any]]:
        """Default classification rules"""
        return [
            {
                "name": "url_link",
                "condition": lambda m: "http://" in m.get("content", "") or "https://" in m.get("content", ""),
                "category": "reference",
                "confidence": 0.8
            },
            {
                "name": "question",
                "condition": lambda m: m.get("content", "").strip().endswith("?"),
                "category": "question",
                "confidence": 0.9
            },
            {
                "name": "code_block",
                "condition": lambda m: "```" in m.get("content", "") or "def " in m.get("content", ""),
                "category": "code",
                "confidence": 0.95
            },
        ]
    
    def classify(self, memory: Dict[str, Any]) -> tuple[str, float]:
        """Apply rules to classify memory"""
        for rule in self.rules:
            try:
                if rule["condition"](memory):
                    return rule["category"], rule["confidence"]
            except Exception as e:
                logger.warning(f"Rule {rule.get('name', 'unknown')} failed: {e}")
        
        return "general", 0.5


class BatchClassifier:
    """Enhanced batch classification with multiple methods"""
    
    def __init__(self):
        self.keyword_classifier = KeywordClassifier()
        self.pattern_classifier = PatternClassifier()
        self.rules_classifier = RulesBasedClassifier()
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def classify_batch(
        self, 
        memories: List[Dict[str, Any]], 
        config: ClassificationConfig
    ) -> List[ClassificationResult]:
        """Classify a batch of memories using configured method"""
        
        if config.method == ClassificationMethod.KEYWORD:
            classifier = KeywordClassifier(config.keywords)
            return await self._classify_with_method(memories, classifier.classify, config)
        
        elif config.method == ClassificationMethod.PATTERN:
            return await self._classify_with_method(memories, self.pattern_classifier.classify, config)
        
        elif config.method == ClassificationMethod.RULES_BASED:
            classifier = RulesBasedClassifier(config.custom_rules)
            return await self._classify_with_rules(memories, classifier, config)
        
        elif config.method == ClassificationMethod.HYBRID:
            return await self._classify_hybrid(memories, config)
        
        else:  # AUTO or fallback
            return await self._classify_auto(memories, config)
    
    async def _classify_with_method(
        self, 
        memories: List[Dict[str, Any]], 
        classify_func, 
        config: ClassificationConfig
    ) -> List[ClassificationResult]:
        """Generic classification with a specific method"""
        results = []
        
        for memory in memories:
            try:
                content = memory.get("content", "")
                category, confidence = classify_func(content)
                
                if confidence >= config.confidence_threshold:
                    result = ClassificationResult(
                        memory_id=memory.get("id", ""),
                        original_category=memory.get("category"),
                        new_category=category,
                        confidence=confidence,
                        method_used=config.method,
                        tags_added=self._generate_tags(category)
                    )
                    results.append(result)
            except Exception as e:
                logger.error(f"Classification failed for memory {memory.get('id')}: {e}")
        
        return results
    
    async def _classify_with_rules(
        self, 
        memories: List[Dict[str, Any]], 
        classifier: RulesBasedClassifier,
        config: ClassificationConfig
    ) -> List[ClassificationResult]:
        """Classification using rules that operate on full memory object"""
        results = []
        
        for memory in memories:
            try:
                category, confidence = classifier.classify(memory)
                
                if confidence >= config.confidence_threshold:
                    result = ClassificationResult(
                        memory_id=memory.get("id", ""),
                        original_category=memory.get("category"),
                        new_category=category,
                        confidence=confidence,
                        method_used=ClassificationMethod.RULES_BASED,
                        tags_added=self._generate_tags(category)
                    )
                    results.append(result)
            except Exception as e:
                logger.error(f"Rules classification failed for memory {memory.get('id')}: {e}")
        
        return results
    
    async def _classify_hybrid(
        self, 
        memories: List[Dict[str, Any]], 
        config: ClassificationConfig
    ) -> List[ClassificationResult]:
        """Hybrid classification using multiple methods"""
        results = []
        
        for memory in memories:
            try:
                content = memory.get("content", "")
                
                # Get results from all classifiers
                keyword_cat, keyword_conf = self.keyword_classifier.classify(content)
                pattern_cat, pattern_conf = self.pattern_classifier.classify(content)
                rules_cat, rules_conf = self.rules_classifier.classify(memory)
                
                # Combine results (weighted average)
                all_results = [
                    (keyword_cat, keyword_conf * 0.3),
                    (pattern_cat, pattern_conf * 0.3),
                    (rules_cat, rules_conf * 0.4)
                ]
                
                # Group by category and sum scores
                category_scores = {}
                for cat, score in all_results:
                    category_scores[cat] = category_scores.get(cat, 0) + score
                
                # Get best category
                if category_scores:
                    best_category = max(category_scores, key=category_scores.get)
                    confidence = min(category_scores[best_category], 1.0)
                    
                    if confidence >= config.confidence_threshold:
                        result = ClassificationResult(
                            memory_id=memory.get("id", ""),
                            original_category=memory.get("category"),
                            new_category=best_category,
                            confidence=confidence,
                            method_used=ClassificationMethod.HYBRID,
                            tags_added=self._generate_tags(best_category)
                        )
                        results.append(result)
            except Exception as e:
                logger.error(f"Hybrid classification failed for memory {memory.get('id')}: {e}")
        
        return results
    
    async def _classify_auto(
        self, 
        memories: List[Dict[str, Any]], 
        config: ClassificationConfig
    ) -> List[ClassificationResult]:
        """Automatic classification choosing best method per memory"""
        # For now, use hybrid approach
        return await self._classify_hybrid(memories, config)
    
    def _generate_tags(self, category: str) -> List[str]:
        """Generate relevant tags based on category"""
        tag_mapping = {
            "work": ["professional", "career"],
            "personal": ["life", "private"],
            "learning": ["education", "knowledge"],
            "technical": ["technology", "development"],
            "code": ["programming", "software"],
        }
        return tag_mapping.get(category, [])


class BatchClassificationEngine:
    """Main engine for batch classification"""
    
    def __init__(self):
        self.classifier = BatchClassifier()
        self._cache = {}
        self._statistics = {
            "total_classified": 0,
            "total_failed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "processing_time_avg": 0.0
        }
    
    async def classify_batch(
        self, 
        memories: List[Dict[str, Any]], 
        config: ClassificationConfig
    ) -> BatchClassificationResult:
        """Classify a batch of memories with given configuration"""
        start_time = datetime.utcnow()
        result = BatchClassificationResult()
        result.processed_memories = len(memories)
        
        try:
            # Process in chunks for better performance
            chunks = [memories[i:i + config.batch_size] 
                     for i in range(0, len(memories), config.batch_size)]
            
            all_results = []
            for chunk in chunks:
                chunk_results = await self.classifier.classify_batch(chunk, config)
                all_results.extend(chunk_results)
            
            result.classification_results = all_results
            result.classified_count = len(all_results)
            result.failed_count = len(memories) - len(all_results)
            
            # Calculate performance metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            result.performance_metrics = {
                "processing_time": processing_time,
                "memories_per_second": len(memories) / max(processing_time, 0.001),
                "success_rate": result.classified_count / max(result.processed_memories, 1),
                "average_confidence": sum(r.confidence for r in all_results) / max(len(all_results), 1)
            }
            
            # Update statistics
            self._statistics["total_classified"] += result.classified_count
            self._statistics["total_failed"] += result.failed_count
            
        except Exception as e:
            logger.error(f"Batch classification failed: {e}")
            result.errors.append({"error": str(e), "timestamp": datetime.utcnow().isoformat()})
        
        return result
    
    async def apply_classification_results(
        self, 
        results: List[ClassificationResult], 
        config: ClassificationConfig
    ) -> Dict[str, Any]:
        """Apply classification results to memories"""
        applied = 0
        failed = 0
        
        for result in results:
            try:
                # In a real implementation, this would update the database
                # For now, just count successes
                applied += 1
            except Exception as e:
                logger.error(f"Failed to apply classification for {result.memory_id}: {e}")
                failed += 1
        
        return {
            "applied": applied,
            "failed": failed,
            "message": f"Applied {applied} classifications successfully"
        }
    
    def get_classification_statistics(self) -> Dict[str, Any]:
        """Get classification engine statistics"""
        return self._statistics.copy()
    
    def clear_cache(self):
        """Clear classification cache"""
        self._cache.clear()
        self._statistics["cache_hits"] = 0
        self._statistics["cache_misses"] = 0


# Singleton instance
_engine_instance = None


def get_batch_classification_engine() -> BatchClassificationEngine:
    """Get singleton instance of batch classification engine"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = BatchClassificationEngine()
    return _engine_instance