"""
Intelligent content classifier for automatic categorization and quality assessment
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from collections import defaultdict, Counter
import logging
from datetime import datetime

from app.ingestion.models import ContentQuality, ProcessedContent, Entity, Topic, Intent, IntentType

logger = logging.getLogger(__name__)


class ContentClassifier:
    """Classify content intelligently based on multiple signals"""
    
    def __init__(self):
        """Initialize content classifier"""
        # Initialize classification rules
        self.domain_rules = self._initialize_domain_rules()
        self.quality_indicators = self._initialize_quality_indicators()
        self.memory_type_rules = self._initialize_memory_type_rules()
        self.importance_factors = self._initialize_importance_factors()
    
    def classify_content(self, processed_content: ProcessedContent) -> Dict[str, Any]:
        """
        Classify processed content and suggest metadata
        
        Args:
            processed_content: Processed content with extractions
            
        Returns:
            Classification results with suggestions
        """
        # Determine domain
        domain = self._classify_domain(processed_content)
        
        # Assess content quality
        quality = self._assess_quality(processed_content)
        
        # Calculate completeness score
        completeness = self._calculate_completeness(processed_content)
        
        # Suggest memory type
        memory_type = self._suggest_memory_type(processed_content)
        
        # Calculate importance
        importance = self._calculate_importance(processed_content)
        
        # Generate tags
        suggested_tags = self._generate_tags(processed_content)
        
        # Update processed content
        processed_content.domain = domain
        processed_content.quality = quality
        processed_content.completeness_score = completeness
        processed_content.suggested_memory_type = memory_type
        processed_content.suggested_importance = importance
        processed_content.suggested_tags = suggested_tags
        
        return {
            "domain": domain,
            "quality": quality,
            "completeness_score": completeness,
            "memory_type": memory_type,
            "importance": importance,
            "tags": suggested_tags,
            "metadata": self._generate_metadata_suggestions(processed_content)
        }
    
    def _classify_domain(self, content: ProcessedContent) -> Optional[str]:
        """Classify content domain based on multiple signals"""
        domain_scores = defaultdict(float)
        
        # Analyze topics
        for topic in content.topics:
            # Check topic hierarchy for domain hints
            if topic.hierarchy:
                potential_domain = topic.hierarchy[0]
                domain_scores[potential_domain] += topic.relevance * topic.confidence
            
            # Check topic name against domain patterns
            topic_lower = topic.name.lower()
            for domain, patterns in self.domain_rules.items():
                for pattern in patterns["keywords"]:
                    if pattern in topic_lower:
                        domain_scores[domain] += 0.5
        
        # Analyze entities
        entity_types = Counter(entity.type.value for entity in content.entities)
        
        # Map entity types to domains
        if entity_types.get("technology", 0) > 2:
            domain_scores["Technology"] += 1.0
        if entity_types.get("organization", 0) > 2:
            domain_scores["Business"] += 0.8
        if entity_types.get("person", 0) > 3:
            domain_scores["Social"] += 0.7
        
        # Analyze content text
        text_lower = content.original_content.lower()
        for domain, rules in self.domain_rules.items():
            keyword_matches = sum(1 for keyword in rules["keywords"] if keyword in text_lower)
            domain_scores[domain] += keyword_matches * 0.2
        
        # Select highest scoring domain
        if domain_scores:
            best_domain = max(domain_scores.items(), key=lambda x: x[1])
            if best_domain[1] > 1.0:  # Minimum threshold
                return best_domain[0]
        
        return "General"
    
    def _assess_quality(self, content: ProcessedContent) -> ContentQuality:
        """Assess content quality based on various factors"""
        quality_score = 0.0
        
        # Length factor
        content_length = len(content.original_content)
        if content_length < 50:
            quality_score -= 1.0
        elif content_length > 200:
            quality_score += 1.0
        if content_length > 500:
            quality_score += 0.5
        
        # Entity richness
        entity_density = len(content.entities) / max(content_length / 100, 1)
        if entity_density > 0.5:
            quality_score += 1.0
        elif entity_density > 0.2:
            quality_score += 0.5
        
        # Topic clarity
        if content.topics:
            avg_topic_confidence = sum(t.confidence for t in content.topics) / len(content.topics)
            quality_score += avg_topic_confidence
        
        # Relationship depth
        if content.relationships:
            quality_score += min(len(content.relationships) * 0.2, 1.0)
        
        # Intent clarity
        if content.intent and content.intent.confidence > 0.7:
            quality_score += 0.5
        
        # Structured data presence
        if content.structured_data:
            if content.structured_data.key_value_pairs:
                quality_score += 0.3
            if content.structured_data.lists:
                quality_score += 0.3
            if content.structured_data.code_snippets:
                quality_score += 0.5
        
        # Check quality indicators
        text_lower = content.original_content.lower()
        
        # Positive indicators
        for indicator in self.quality_indicators["positive"]:
            if indicator in text_lower:
                quality_score += 0.3
        
        # Negative indicators
        for indicator in self.quality_indicators["negative"]:
            if indicator in text_lower:
                quality_score -= 0.5
        
        # Map score to quality level
        if quality_score >= 3.0:
            return ContentQuality.HIGH
        elif quality_score >= 1.5:
            return ContentQuality.MEDIUM
        elif quality_score >= 0.5:
            return ContentQuality.LOW
        else:
            return ContentQuality.INCOMPLETE
    
    def _calculate_completeness(self, content: ProcessedContent) -> float:
        """Calculate how complete the content processing is"""
        completeness_factors = []
        
        # Entity extraction completeness
        if content.entities:
            # Check entity confidence
            avg_entity_confidence = sum(e.confidence for e in content.entities) / len(content.entities)
            completeness_factors.append(avg_entity_confidence)
        else:
            completeness_factors.append(0.3)  # Penalty for no entities
        
        # Topic extraction completeness
        if content.topics:
            avg_topic_confidence = sum(t.confidence for t in content.topics) / len(content.topics)
            completeness_factors.append(avg_topic_confidence)
        else:
            completeness_factors.append(0.4)
        
        # Relationship detection completeness
        if content.relationships:
            relationship_ratio = len(content.relationships) / max(len(content.entities) - 1, 1)
            completeness_factors.append(min(relationship_ratio, 1.0))
        else:
            completeness_factors.append(0.5)
        
        # Intent recognition
        if content.intent:
            completeness_factors.append(content.intent.confidence)
        else:
            completeness_factors.append(0.5)
        
        # Embedding generation
        if content.embeddings:
            completeness_factors.append(1.0)
        else:
            completeness_factors.append(0.0)
        
        # Structured data extraction
        if content.structured_data:
            structure_score = 0.0
            if content.structured_data.key_value_pairs:
                structure_score += 0.3
            if content.structured_data.lists:
                structure_score += 0.3
            if content.structured_data.tables:
                structure_score += 0.4
            completeness_factors.append(structure_score)
        else:
            completeness_factors.append(0.3)
        
        # Calculate average completeness
        return sum(completeness_factors) / len(completeness_factors)
    
    def _suggest_memory_type(self, content: ProcessedContent) -> Optional[str]:
        """Suggest appropriate memory type based on content"""
        type_scores = defaultdict(float)
        
        # Check intent
        if content.intent:
            intent_type = content.intent.type
            
            # Map intent to memory type
            if intent_type in [IntentType.LEARNING, IntentType.REFERENCE]:
                type_scores["semantic"] += 2.0
            elif intent_type in [IntentType.TODO, IntentType.PLANNING]:
                type_scores["procedural"] += 2.0
            elif intent_type in [IntentType.REFLECTION, IntentType.IDEA]:
                type_scores["episodic"] += 2.0
            elif intent_type == IntentType.DECISION:
                type_scores["decision"] += 2.5
        
        # Check for temporal indicators
        temporal_patterns = [
            r'\b(?:today|yesterday|tomorrow|last week|next month)\b',
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b'
        ]
        
        text_lower = content.original_content.lower()
        temporal_count = sum(1 for pattern in temporal_patterns if re.search(pattern, text_lower))
        
        if temporal_count > 0:
            type_scores["episodic"] += temporal_count * 0.5
        
        # Check for procedural indicators
        procedural_indicators = ["how to", "step by step", "instructions", "guide", "tutorial", "process"]
        procedural_count = sum(1 for indicator in procedural_indicators if indicator in text_lower)
        
        if procedural_count > 0:
            type_scores["procedural"] += procedural_count * 0.8
        
        # Check for factual/reference content
        reference_indicators = ["definition", "explanation", "concept", "theory", "principle", "fact"]
        reference_count = sum(1 for indicator in reference_indicators if indicator in text_lower)
        
        if reference_count > 0:
            type_scores["semantic"] += reference_count * 0.7
        
        # Check entity types
        entity_types = [e.type.value for e in content.entities]
        if "person" in entity_types or "organization" in entity_types:
            type_scores["episodic"] += 0.5
        if "technology" in entity_types or "concept" in entity_types:
            type_scores["semantic"] += 0.5
        
        # Select highest scoring type
        if type_scores:
            best_type = max(type_scores.items(), key=lambda x: x[1])
            if best_type[1] > 1.0:  # Minimum threshold
                return best_type[0]
        
        # Default based on content length
        if len(content.original_content) < 100:
            return "working"
        elif len(content.original_content) < 500:
            return "short-term"
        else:
            return "long-term"
    
    def _calculate_importance(self, content: ProcessedContent) -> float:
        """Calculate content importance score"""
        importance_score = 5.0  # Start with neutral importance
        
        # Factor in quality
        quality_boost = {
            ContentQuality.HIGH: 1.5,
            ContentQuality.MEDIUM: 0.5,
            ContentQuality.LOW: -0.5,
            ContentQuality.INCOMPLETE: -1.0
        }
        importance_score += quality_boost.get(content.quality, 0)
        
        # Factor in intent
        if content.intent:
            # Urgent content is more important
            if content.intent.urgency:
                importance_score += content.intent.urgency * 2
            
            # Certain intent types are inherently more important
            intent_importance = {
                IntentType.DECISION: 1.0,
                IntentType.TODO: 0.8,
                IntentType.PROBLEM: 0.7,
                IntentType.IDEA: 0.6,
                IntentType.LEARNING: 0.5,
            }
            importance_score += intent_importance.get(content.intent.type, 0)
        
        # Factor in entities
        # More unique entities = potentially more important
        unique_entities = len(set(e.normalized for e in content.entities))
        importance_score += min(unique_entities * 0.1, 1.0)
        
        # Factor in relationships
        # Content with many relationships is often more important
        if content.relationships:
            importance_score += min(len(content.relationships) * 0.15, 1.0)
        
        # Check for importance keywords
        text_lower = content.original_content.lower()
        
        for keyword, weight in self.importance_factors["keywords"].items():
            if keyword in text_lower:
                importance_score += weight
        
        # Normalize to 0-10 range
        importance_score = max(0.0, min(10.0, importance_score))
        
        return importance_score
    
    def _generate_tags(self, content: ProcessedContent) -> List[str]:
        """Generate suggested tags for content"""
        tags = set()
        
        # Add domain as tag
        if content.domain and content.domain != "General":
            tags.add(content.domain.lower())
        
        # Extract tags from topics
        for topic in content.topics[:3]:  # Top 3 topics
            # Add topic name (simplified)
            topic_tag = topic.name.lower().replace(" topic", "").replace(" & ", "-")
            tags.add(topic_tag)
            
            # Add some keywords from topic
            for keyword in topic.keywords[:2]:
                if len(keyword) > 3:  # Skip very short keywords
                    tags.add(keyword.lower())
        
        # Extract tags from high-confidence entities
        for entity in content.entities:
            if entity.confidence > 0.8 and entity.type.value in ["technology", "concept", "project"]:
                entity_tag = entity.normalized.replace(" ", "-")
                if 3 < len(entity_tag) < 20:  # Reasonable tag length
                    tags.add(entity_tag)
        
        # Add intent-based tags
        if content.intent:
            intent_tags = {
                IntentType.TODO: "todo",
                IntentType.IDEA: "idea",
                IntentType.DECISION: "decision",
                IntentType.LEARNING: "learning",
                IntentType.REFERENCE: "reference",
                IntentType.PROBLEM: "problem",
                IntentType.SOLUTION: "solution"
            }
            if content.intent.type in intent_tags:
                tags.add(intent_tags[content.intent.type])
        
        # Add quality/completeness tags if notable
        if content.quality == ContentQuality.HIGH:
            tags.add("high-quality")
        if content.completeness_score > 0.8:
            tags.add("comprehensive")
        
        # Add suggested memory type as tag
        if content.suggested_memory_type:
            tags.add(content.suggested_memory_type)
        
        # Convert to sorted list and limit
        tag_list = sorted(list(tags))
        return tag_list[:10]  # Limit to 10 tags
    
    def _generate_metadata_suggestions(self, content: ProcessedContent) -> Dict[str, Any]:
        """Generate additional metadata suggestions"""
        metadata = {}
        
        # Add source type based on content patterns
        if re.search(r'https?://', content.original_content):
            metadata["source_type"] = "web"
        elif re.search(r'@[\w]+', content.original_content):
            metadata["source_type"] = "social"
        elif any(indicator in content.original_content.lower() for indicator in ["meeting", "discussion", "conversation"]):
            metadata["source_type"] = "meeting"
        else:
            metadata["source_type"] = "note"
        
        # Add complexity level
        complexity_score = (
            len(content.entities) * 0.1 +
            len(content.relationships) * 0.2 +
            len(content.topics) * 0.15 +
            (1.0 if content.structured_data else 0)
        )
        
        if complexity_score > 2.0:
            metadata["complexity"] = "high"
        elif complexity_score > 1.0:
            metadata["complexity"] = "medium"
        else:
            metadata["complexity"] = "low"
        
        # Add content category based on patterns
        if content.structured_data and content.structured_data.code_snippets:
            metadata["category"] = "code"
        elif content.intent and content.intent.type == IntentType.REFERENCE:
            metadata["category"] = "reference"
        elif content.intent and content.intent.type in [IntentType.TODO, IntentType.PLANNING]:
            metadata["category"] = "task"
        else:
            metadata["category"] = "general"
        
        # Add extraction quality metrics
        metadata["extraction_quality"] = {
            "entity_count": len(content.entities),
            "relationship_count": len(content.relationships),
            "topic_count": len(content.topics),
            "has_embeddings": bool(content.embeddings),
            "processing_time_ms": content.processing_time_ms
        }
        
        return metadata
    
    def _initialize_domain_rules(self) -> Dict[str, Dict[str, List[str]]]:
        """Initialize domain classification rules"""
        return {
            "Technology": {
                "keywords": ["software", "code", "programming", "api", "database", "cloud", "ai", "machine learning"],
                "entity_types": ["technology", "project"]
            },
            "Business": {
                "keywords": ["business", "revenue", "customer", "market", "strategy", "sales", "profit", "roi"],
                "entity_types": ["organization", "person"]
            },
            "Science": {
                "keywords": ["research", "study", "experiment", "hypothesis", "data", "analysis", "theory"],
                "entity_types": ["concept", "location"]
            },
            "Education": {
                "keywords": ["learning", "education", "course", "lesson", "student", "teacher", "knowledge"],
                "entity_types": ["person", "organization"]
            },
            "Personal": {
                "keywords": ["personal", "life", "goal", "habit", "health", "family", "hobby"],
                "entity_types": ["person", "location"]
            }
        }
    
    def _initialize_quality_indicators(self) -> Dict[str, List[str]]:
        """Initialize content quality indicators"""
        return {
            "positive": [
                "comprehensive", "detailed", "explained", "analyzed", "structured",
                "clear", "important", "critical", "essential", "valuable"
            ],
            "negative": [
                "unclear", "confusing", "incomplete", "draft", "todo later",
                "need more info", "not sure", "maybe", "possibly", "temporary"
            ]
        }
    
    def _initialize_memory_type_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize memory type classification rules"""
        return {
            "semantic": {
                "keywords": ["definition", "concept", "theory", "principle", "fact", "knowledge"],
                "patterns": [r'\bis\s+(?:a|an|the)\b', r'\bmeans\b', r'\brefers?\s+to\b']
            },
            "episodic": {
                "keywords": ["remember", "recall", "happened", "event", "experience", "met"],
                "patterns": [r'\b(?:I|we)\s+(?:did|went|saw|met)\b', r'\b(?:last|next)\s+(?:week|month|year)\b']
            },
            "procedural": {
                "keywords": ["how to", "steps", "process", "method", "technique", "instruction"],
                "patterns": [r'\b\d+\.\s+', r'\bstep\s+\d+\b', r'\bfirst\b.*\bthen\b']
            }
        }
    
    def _initialize_importance_factors(self) -> Dict[str, Dict[str, float]]:
        """Initialize importance calculation factors"""
        return {
            "keywords": {
                "critical": 1.0,
                "important": 0.8,
                "essential": 0.8,
                "urgent": 1.2,
                "deadline": 0.9,
                "priority": 0.7,
                "key": 0.6,
                "main": 0.5,
                "note": -0.3,
                "minor": -0.5,
                "trivial": -0.8
            }
        }
    
    def get_classification_statistics(self, classifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about classifications"""
        if not classifications:
            return {
                "total_classified": 0,
                "domain_distribution": {},
                "quality_distribution": {},
                "memory_type_distribution": {},
                "avg_importance": 0,
                "avg_completeness": 0
            }
        
        # Aggregate statistics
        domain_counts = Counter(c["domain"] for c in classifications if c.get("domain"))
        quality_counts = Counter(c["quality"] for c in classifications if c.get("quality"))
        memory_type_counts = Counter(c["memory_type"] for c in classifications if c.get("memory_type"))
        
        importances = [c["importance"] for c in classifications if "importance" in c]
        completenesses = [c["completeness_score"] for c in classifications if "completeness_score" in c]
        
        return {
            "total_classified": len(classifications),
            "domain_distribution": dict(domain_counts),
            "quality_distribution": dict(quality_counts),
            "memory_type_distribution": dict(memory_type_counts),
            "avg_importance": sum(importances) / len(importances) if importances else 0,
            "avg_completeness": sum(completenesses) / len(completenesses) if completenesses else 0,
            "tag_frequency": Counter([tag for c in classifications for tag in c.get("tags", [])])
        }