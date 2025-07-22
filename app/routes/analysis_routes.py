"""
API routes for advanced analysis features including domain classification
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.shared import get_db_instance, verify_api_key
from app.ingestion.topic_classifier import TopicClassifier
from app.ingestion.structured_extractor import StructuredDataExtractor
from app.ingestion.domain_classifier import DomainClassifier
# Authentication handled by shared verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/analysis",
    tags=["analysis"],
    responses={404: {"description": "Not found"}}
)


class AnalysisRequest(BaseModel):
    """Request model for content analysis"""
    content: str = Field(..., description="Content to analyze")
    include_topics: bool = Field(True, description="Include topic analysis")
    include_structure: bool = Field(True, description="Include structured data extraction")
    include_domain: bool = Field(True, description="Include domain classification")
    advanced_features: bool = Field(False, description="Use advanced analysis features")


class BatchAnalysisRequest(BaseModel):
    """Request model for batch analysis"""
    memory_ids: Optional[List[str]] = Field(None, description="Memory IDs to analyze")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    limit: int = Field(50, description="Maximum memories to analyze")
    include_topics: bool = Field(True, description="Include topic analysis")
    include_structure: bool = Field(True, description="Include structured data extraction")
    include_domain: bool = Field(True, description="Include domain classification")


class DomainClassificationRequest(BaseModel):
    """Request model for domain classification"""
    content: str = Field(..., description="Content to classify")
    multi_label: bool = Field(True, description="Allow multiple domain labels")
    include_hierarchy: bool = Field(True, description="Include domain hierarchy")
    confidence_threshold: float = Field(0.3, description="Minimum confidence threshold")


@router.post("/analyze")
async def analyze_content(
    request: AnalysisRequest,
    _: str = Depends(verify_api_key)
):
    """
    Perform comprehensive content analysis
    """
    try:
        results = {
            "status": "success",
            "analysis": {}
        }
        
        # Topic analysis
        if request.include_topics:
            topic_classifier = TopicClassifier(enable_advanced=request.advanced_features)
            
            if request.advanced_features:
                topics = topic_classifier.extract_advanced_topics(request.content)
            else:
                topics = topic_classifier.extract_topics(request.content)
            
            results["analysis"]["topics"] = {
                "extracted_topics": [
                    {
                        "name": topic.name,
                        "keywords": topic.keywords,
                        "confidence": topic.confidence,
                        "relevance": topic.relevance,
                        "hierarchy": topic.hierarchy
                    }
                    for topic in topics
                ],
                "statistics": topic_classifier.get_topic_statistics(topics)
            }
        
        # Structured data extraction
        if request.include_structure:
            extractor = StructuredDataExtractor()
            
            if request.advanced_features:
                structured_data = extractor.extract_advanced_structured_data(request.content)
            else:
                structured_data = extractor.extract_structured_data(request.content)
            
            results["analysis"]["structured_data"] = {
                "key_value_pairs": structured_data.key_value_pairs,
                "lists": structured_data.lists,
                "tables": structured_data.tables,
                "code_snippets": structured_data.code_snippets,
                "metadata": structured_data.metadata_fields,
                "statistics": extractor.get_extraction_statistics(structured_data)
            }
        
        # Domain classification
        if request.include_domain:
            domain_classifier = DomainClassifier()
            domain_results = domain_classifier.classify_domain(
                request.content,
                multi_label=True,
                include_hierarchy=True
            )
            
            results["analysis"]["domains"] = domain_results
        
        return results
        
    except Exception as e:
        logger.error(f"Error analyzing content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def batch_analyze(
    request: BatchAnalysisRequest,
    _: str = Depends(verify_api_key),
    db=Depends(get_db_instance)
):
    """
    Perform batch analysis on multiple memories
    """
    try:
        memory_service = MemoryService(db)
        
        # Get memories based on filters
        if request.memory_ids:
            memories = []
            for memory_id in request.memory_ids:
                memory = await memory_service.get_memory(memory_id, current_user.id)
                if memory:
                    memories.append(memory)
        else:
            memories = await memory_service.search_memories(
                user_id=current_user.id,
                tags=request.tags,
                limit=request.limit
            )
        
        if not memories:
            return {
                "status": "no_data",
                "message": "No memories found with specified filters"
            }
        
        # Initialize analyzers
        topic_classifier = TopicClassifier() if request.include_topics else None
        extractor = StructuredDataExtractor() if request.include_structure else None
        domain_classifier = DomainClassifier() if request.include_domain else None
        
        # Analyze each memory
        analyzed_memories = []
        all_topics = []
        all_domains = []
        
        for memory in memories:
            analysis = {
                "memory_id": memory.id,
                "title": memory.title
            }
            
            # Topic analysis
            if topic_classifier:
                topics = topic_classifier.extract_topics(memory.content)
                analysis["topics"] = [topic.name for topic in topics[:3]]
                all_topics.extend(topics)
            
            # Structured data extraction
            if extractor:
                structured_data = extractor.extract_structured_data(memory.content)
                analysis["structured_summary"] = {
                    "kv_pairs": len(structured_data.key_value_pairs),
                    "lists": len(structured_data.lists),
                    "tables": len(structured_data.tables),
                    "code_snippets": len(structured_data.code_snippets)
                }
            
            # Domain classification
            if domain_classifier:
                domain_results = domain_classifier.classify_domain(memory.content)
                analysis["domains"] = domain_results["domains"][:2]
                all_domains.append(domain_results)
            
            analyzed_memories.append(analysis)
        
        # Aggregate statistics
        statistics = {
            "total_memories": len(memories),
            "memories_analyzed": len(analyzed_memories)
        }
        
        if topic_classifier and all_topics:
            statistics["topic_statistics"] = topic_classifier.get_topic_statistics(all_topics)
        
        if domain_classifier and all_domains:
            statistics["domain_statistics"] = domain_classifier.get_domain_statistics(all_domains)
        
        return {
            "status": "success",
            "analyzed_memories": analyzed_memories,
            "statistics": statistics
        }
        
    except Exception as e:
        logger.error(f"Error in batch analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classify-domain")
async def classify_domain(
    request: DomainClassificationRequest,
    _: str = Depends(verify_api_key)
):
    """
    Classify content into knowledge domains
    """
    try:
        classifier = DomainClassifier(
            confidence_threshold=request.confidence_threshold
        )
        
        results = classifier.classify_domain(
            request.content,
            multi_label=request.multi_label,
            include_hierarchy=request.include_hierarchy
        )
        
        return {
            "status": "success",
            "classification": results
        }
        
    except Exception as e:
        logger.error(f"Error classifying domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics/trending")
async def get_trending_topics(
    days: int = Query(7, description="Number of days to analyze"),
    limit: int = Query(10, description="Number of top topics"),
    _: str = Depends(verify_api_key),
    db=Depends(get_db_instance)
):
    """
    Get trending topics from recent memories
    """
    try:
        memory_service = MemoryService(db)
        
        # Get recent memories
        from datetime import datetime, timedelta
        since = datetime.utcnow() - timedelta(days=days)
        
        memories = await memory_service.search_memories(
            user_id=current_user.id,
            created_after=since,
            limit=100
        )
        
        if not memories:
            return {
                "status": "no_data",
                "message": "No recent memories found"
            }
        
        # Extract topics from all memories
        topic_classifier = TopicClassifier()
        all_topics = []
        
        for memory in memories:
            topics = topic_classifier.extract_topics(memory.content)
            all_topics.extend(topics)
        
        # Count topic occurrences
        from collections import Counter
        topic_counts = Counter()
        topic_keywords = {}
        
        for topic in all_topics:
            topic_counts[topic.name] += 1
            if topic.name not in topic_keywords:
                topic_keywords[topic.name] = set()
            topic_keywords[topic.name].update(topic.keywords[:3])
        
        # Get top trending topics
        trending = []
        for topic_name, count in topic_counts.most_common(limit):
            trending.append({
                "topic": topic_name,
                "occurrences": count,
                "keywords": list(topic_keywords[topic_name])[:5],
                "trend_score": count / len(memories)
            })
        
        return {
            "status": "success",
            "period_days": days,
            "memories_analyzed": len(memories),
            "trending_topics": trending
        }
        
    except Exception as e:
        logger.error(f"Error getting trending topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domains/distribution")
async def get_domain_distribution(
    _: str = Depends(verify_api_key),
    db=Depends(get_db_instance)
):
    """
    Get distribution of content across domains
    """
    try:
        memory_service = MemoryService(db)
        memories = await memory_service.search_memories(
            user_id=current_user.id,
            limit=200
        )
        
        if not memories:
            return {
                "status": "no_data",
                "message": "No memories found"
            }
        
        # Classify all memories
        domain_classifier = DomainClassifier()
        domain_counts = Counter()
        domain_confidence = defaultdict(list)
        cross_domain_count = 0
        
        for memory in memories:
            results = domain_classifier.classify_domain(memory.content)
            domains = results["domains"]
            scores = results["confidence_scores"]
            
            if len(domains) > 1:
                cross_domain_count += 1
            
            for domain in domains:
                domain_counts[domain] += 1
                if domain in scores:
                    domain_confidence[domain].append(scores[domain])
        
        # Calculate statistics
        distribution = []
        for domain, count in domain_counts.most_common():
            avg_confidence = sum(domain_confidence[domain]) / len(domain_confidence[domain])
            distribution.append({
                "domain": domain,
                "count": count,
                "percentage": (count / len(memories)) * 100,
                "avg_confidence": avg_confidence
            })
        
        return {
            "status": "success",
            "total_memories": len(memories),
            "domain_distribution": distribution,
            "cross_domain_percentage": (cross_domain_count / len(memories)) * 100,
            "unique_domains": len(domain_counts)
        }
        
    except Exception as e:
        logger.error(f"Error getting domain distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))