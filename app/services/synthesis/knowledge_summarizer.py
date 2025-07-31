"""Knowledge Summarizer Service with LLM Integration

Real implementation that creates intelligent summaries of knowledge domains,
topics, and memory collections using advanced NLP techniques.
"""

import asyncio
import json
from typing import Optional, Dict, List, Any, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict

from app.utils.logging_config import get_logger
from app.models.synthesis.summary_models import (
    SummaryType,
    SummaryRequest,
    SummaryResponse,
    FormatType
)

logger = get_logger(__name__)


class KnowledgeDomain:
    """Represents a knowledge domain with associated memories"""
    
    def __init__(self, name: str):
        self.name = name
        self.memories: List[Dict[str, Any]] = []
        self.sub_topics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.key_concepts: Set[str] = set()
        self.temporal_range: Optional[Tuple[datetime, datetime]] = None
        self.importance_score: float = 0.0


class KnowledgeSummarizer:
    """Service for creating intelligent knowledge summaries"""
    
    def __init__(self, db, memory_service, openai_client):
        self.db = db
        self.memory_service = memory_service
        self.openai_client = openai_client
        
        # Summary templates
        self.summary_templates = {
            SummaryType.EXECUTIVE: """
You are an executive summary specialist. Create a concise executive summary that:
1. Highlights the most important findings and insights
2. Focuses on actionable information
3. Uses clear, business-oriented language
4. Includes key metrics and outcomes

Content to summarize:
{content}

Create an executive summary suitable for decision-makers.
""",
            SummaryType.DETAILED: """
You are a comprehensive knowledge analyst. Create a detailed summary that:
1. Covers all major topics and subtopics
2. Preserves important details and nuances
3. Explains relationships between concepts
4. Includes examples and evidence

Content to summarize:
{content}

Create a thorough summary that serves as a complete reference.
""",
            SummaryType.TECHNICAL: """
You are a technical documentation expert. Create a technical summary that:
1. Focuses on technical details and specifications
2. Uses precise terminology
3. Includes implementation details
4. Highlights technical challenges and solutions

Content to summarize:
{content}

Create a technical summary for practitioners and experts.
""",
            SummaryType.LEARNING: """
You are an educational content creator. Create a learning-oriented summary that:
1. Structures information for easy learning
2. Identifies key concepts to master
3. Suggests learning paths and prerequisites
4. Includes practice examples

Content to summarize:
{content}

Create an educational summary optimized for learning and retention.
"""
        }
    
    async def create_summary(self, request: SummaryRequest) -> SummaryResponse:
        """Create intelligent summary based on request parameters"""
        try:
            # Fetch and organize memories
            memories = await self._fetch_memories_for_summary(request)
            if not memories:
                return self._empty_summary_response(request)
            
            # Organize into domains and topics
            domains = await self._organize_knowledge_domains(memories)
            
            # Extract key insights
            key_insights = await self._extract_key_insights(memories, domains)
            
            # Generate summaries based on type
            if request.summary_type == SummaryType.EXECUTIVE:
                summary_content = await self._create_executive_summary(domains, key_insights)
            elif request.summary_type == SummaryType.DETAILED:
                summary_content = await self._create_detailed_summary(domains, key_insights)
            elif request.summary_type == SummaryType.TECHNICAL:
                summary_content = await self._create_technical_summary(domains, key_insights)
            else:  # LEARNING
                summary_content = await self._create_learning_summary(domains, key_insights)
            
            # Create topic summaries
            topic_summaries = await self._create_topic_summaries(domains)
            
            # Create domain overviews
            domain_overviews = await self._create_domain_overviews(domains)
            
            return SummaryResponse(
                summary_type=request.summary_type,
                content=summary_content,
                key_insights=key_insights,
                topic_summaries=topic_summaries,
                domain_overviews=domain_overviews,
                word_count=len(summary_content.split()),
                reading_time_minutes=max(1, len(summary_content.split()) // 200),
                coverage_score=self._calculate_coverage_score(memories, domains),
                metadata={
                    'total_memories': len(memories),
                    'domains_identified': len(domains),
                    'topics_covered': sum(len(d.sub_topics) for d in domains.values()),
                    'time_range': self._get_time_range(memories),
                    'summary_focus': request.focus_areas or ['general']
                }
            )
            
        except Exception as e:
            logger.error(f"Summary creation failed: {e}")
            return self._empty_summary_response(request)
    
    async def _fetch_memories_for_summary(self, request: SummaryRequest) -> List[Dict[str, Any]]:
        """Fetch memories based on summary request criteria"""
        memories = []
        
        # Fetch by memory IDs if provided
        if request.memory_ids:
            for memory_id in request.memory_ids:
                try:
                    memory = await self.memory_service.get_memory(str(memory_id))
                    if memory:
                        memories.append({
                            'id': memory_id,
                            'content': memory.content,
                            'importance': memory.importance_score,
                            'created_at': memory.created_at,
                            'tags': getattr(memory, 'tags', []),
                            'metadata': getattr(memory, 'metadata', {})
                        })
                except Exception as e:
                    logger.error(f"Failed to fetch memory {memory_id}: {e}")
        
        # Fetch by time range if provided
        elif request.time_range:
            query = """
            SELECT id, content, importance, created_at, tags, metadata
            FROM memories
            WHERE created_at >= $1 AND created_at <= $2
            ORDER BY importance DESC, created_at DESC
            LIMIT 500
            """
            results = await self.db.fetch_all(
                query,
                request.time_range.start_date,
                request.time_range.end_date
            )
            memories = [dict(r) for r in results]
        
        # Fetch by topic filter if provided
        elif request.topic_filter:
            # Search for memories with matching tags or content
            query = """
            SELECT id, content, importance, created_at, tags, metadata
            FROM memories
            WHERE tags && $1 OR content ILIKE $2
            ORDER BY importance DESC, created_at DESC
            LIMIT 500
            """
            topic_pattern = f"%{request.topic_filter}%"
            results = await self.db.fetch_all(
                query,
                [request.topic_filter],
                topic_pattern
            )
            memories = [dict(r) for r in results]
        
        else:
            # Default: fetch recent high-importance memories
            query = """
            SELECT id, content, importance, created_at, tags, metadata
            FROM memories
            WHERE importance >= 7
            ORDER BY created_at DESC
            LIMIT 200
            """
            results = await self.db.fetch_all(query)
            memories = [dict(r) for r in results]
        
        return memories
    
    async def _organize_knowledge_domains(self, memories: List[Dict[str, Any]]) -> Dict[str, KnowledgeDomain]:
        """Organize memories into knowledge domains and topics"""
        domains = {}
        
        # First pass: organize by explicit tags
        for memory in memories:
            tags = memory.get('tags', [])
            
            # Use first tag as primary domain if available
            if tags:
                domain_name = tags[0]
                if domain_name not in domains:
                    domains[domain_name] = KnowledgeDomain(domain_name)
                
                domain = domains[domain_name]
                domain.memories.append(memory)
                
                # Add to sub-topics based on other tags
                for tag in tags[1:]:
                    domain.sub_topics[tag].append(memory)
                
                # Update domain metrics
                domain.key_concepts.update(tags)
                if domain.temporal_range is None:
                    domain.temporal_range = (memory['created_at'], memory['created_at'])
                else:
                    domain.temporal_range = (
                        min(domain.temporal_range[0], memory['created_at']),
                        max(domain.temporal_range[1], memory['created_at'])
                    )
        
        # Second pass: use topic modeling for untagged memories
        untagged = [m for m in memories if not m.get('tags')]
        if untagged:
            discovered_topics = await self._discover_topics(untagged)
            for topic_name, topic_memories in discovered_topics.items():
                if topic_name not in domains:
                    domains[topic_name] = KnowledgeDomain(topic_name)
                domains[topic_name].memories.extend(topic_memories)
        
        # Calculate importance scores for domains
        for domain in domains.values():
            if domain.memories:
                domain.importance_score = np.mean([m['importance'] for m in domain.memories])
        
        return domains
    
    async def _discover_topics(self, memories: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Discover topics using LDA topic modeling"""
        if len(memories) < 5:
            return {"General": memories}
        
        try:
            # Prepare texts
            texts = [m['content'] for m in memories]
            
            # TF-IDF vectorization
            vectorizer = TfidfVectorizer(
                max_features=100,
                min_df=2,
                max_df=0.8,
                stop_words='english'
            )
            doc_term_matrix = vectorizer.fit_transform(texts)
            
            # LDA topic modeling
            n_topics = min(5, len(memories) // 3)
            lda = LatentDirichletAllocation(
                n_components=n_topics,
                random_state=42,
                max_iter=10
            )
            lda.fit(doc_term_matrix)
            
            # Get topic words
            feature_names = vectorizer.get_feature_names_out()
            topics = {}
            
            for topic_idx, topic in enumerate(lda.components_):
                top_words_idx = topic.argsort()[-5:][::-1]
                top_words = [feature_names[i] for i in top_words_idx]
                topic_name = f"{top_words[0].title()} {top_words[1].title()}"
                topics[topic_name] = []
            
            # Assign memories to topics
            doc_topics = lda.transform(doc_term_matrix)
            for i, memory in enumerate(memories):
                topic_idx = doc_topics[i].argmax()
                topic_name = list(topics.keys())[topic_idx]
                topics[topic_name].append(memory)
            
            return topics
            
        except Exception as e:
            logger.error(f"Topic discovery failed: {e}")
            return {"General": memories}
    
    async def _extract_key_insights(
        self,
        memories: List[Dict[str, Any]],
        domains: Dict[str, KnowledgeDomain]
    ) -> List[str]:
        """Extract key insights from memories and domains"""
        insights = []
        
        # Analyze patterns across domains
        domain_insights = await self._analyze_domain_patterns(domains)
        insights.extend(domain_insights)
        
        # Extract insights from high-importance memories
        important_memories = sorted(memories, key=lambda m: m['importance'], reverse=True)[:10]
        memory_insights = await self._extract_memory_insights(important_memories)
        insights.extend(memory_insights)
        
        # Find cross-domain connections
        if len(domains) > 1:
            connection_insights = await self._find_cross_domain_insights(domains)
            insights.extend(connection_insights)
        
        # Sort by impact and limit
        insights.sort(key=lambda i: i.impact_score, reverse=True)
        return insights[:10]  # Top 10 insights
    
    async def _analyze_domain_patterns(self, domains: Dict[str, KnowledgeDomain]) -> List[str]:
        """Analyze patterns within domains"""
        insights = []
        
        for domain_name, domain in domains.items():
            if len(domain.memories) < 3:
                continue
            
            # Prepare domain summary
            memory_contents = "\n".join([
                f"- {m['content'][:100]}..." for m in domain.memories[:10]
            ])
            
            prompt = f"""
Analyze this knowledge domain '{domain_name}' and identify 1-2 key insights or patterns:

Memories in this domain:
{memory_contents}

Provide insights as a JSON array with each insight having:
- "title": Brief insight title
- "description": Detailed explanation
- "evidence": Supporting evidence from the memories

Focus on actionable, non-obvious insights.
"""
            
            try:
                response = await self.openai_client.generate(
                    prompt=prompt,
                    max_tokens=300,
                    temperature=0.7
                )
                
                domain_insights = json.loads(response)
                
                for insight_data in domain_insights[:2]:
                    insights.append(f"{insight_data['title']}: {insight_data['description']}")
                    
            except Exception as e:
                logger.error(f"Domain pattern analysis failed for {domain_name}: {e}")
        
        return insights
    
    async def _extract_memory_insights(self, memories: List[Dict[str, Any]]) -> List[str]:
        """Extract insights from individual important memories"""
        insights = []
        
        for memory in memories[:5]:  # Top 5 important memories
            # Simple insight extraction based on content analysis
            content_length = len(memory['content'])
            
            if content_length > 500:  # Substantial memory
                # Extract key point
                prompt = f"""
Extract the single most important insight from this memory:

{memory['content'][:500]}...

Provide a JSON object with:
- "title": Brief insight (max 10 words)
- "key_point": The main takeaway (max 50 words)
"""
                
                try:
                    response = await self.openai_client.generate(
                        prompt=prompt,
                        max_tokens=100,
                        temperature=0.5
                    )
                    
                    insight_data = json.loads(response)
                    
                    insights.append(f"{insight_data['title']}: {insight_data['key_point']}")
                    
                except Exception as e:
                    logger.error(f"Memory insight extraction failed: {e}")
        
        return insights
    
    async def _find_cross_domain_insights(self, domains: Dict[str, KnowledgeDomain]) -> List[str]:
        """Find insights from connections between domains"""
        insights = []
        domain_list = list(domains.items())
        
        # Look for domains with overlapping concepts
        for i in range(len(domain_list)):
            for j in range(i + 1, len(domain_list)):
                domain1_name, domain1 = domain_list[i]
                domain2_name, domain2 = domain_list[j]
                
                # Check for concept overlap
                common_concepts = domain1.key_concepts.intersection(domain2.key_concepts)
                
                if common_concepts:
                    connection_desc = (f"Connection: {domain1_name} ↔ {domain2_name} - "
                                     f"These domains share concepts: {', '.join(list(common_concepts)[:3])}. "
                                     f"This suggests potential for knowledge transfer or integration.")
                    insights.append(connection_desc)
        
        return insights[:3]  # Limit cross-domain insights
    
    async def _create_executive_summary(
        self,
        domains: Dict[str, KnowledgeDomain],
        key_insights: List[str]
    ) -> str:
        """Create executive summary"""
        # Prepare content
        domain_summary = self._prepare_domain_summary(domains)
        insights_summary = self._prepare_insights_summary(key_insights)
        
        content = f"""
Key Domains Covered:
{domain_summary}

Top Insights:
{insights_summary}
"""
        
        # Generate executive summary
        prompt = self.summary_templates[SummaryType.EXECUTIVE].format(content=content)
        
        try:
            summary = await self.openai_client.generate(
                prompt=prompt,
                max_tokens=500,
                temperature=0.7
            )
            return summary
        except Exception as e:
            logger.error(f"Executive summary generation failed: {e}")
            return self._create_fallback_summary(domains, key_insights)
    
    async def _create_detailed_summary(
        self,
        domains: Dict[str, KnowledgeDomain],
        key_insights: List[str]
    ) -> str:
        """Create detailed comprehensive summary"""
        sections = []
        
        # Add overview
        sections.append("# Comprehensive Knowledge Summary\n")
        sections.append(f"## Overview\n")
        sections.append(f"This summary covers {len(domains)} knowledge domains with "
                       f"{sum(len(d.memories) for d in domains.values())} total memories.\n")
        
        # Add insights section
        sections.append("## Key Insights\n")
        for i, insight in enumerate(key_insights[:5], 1):
            sections.append(f"{i}. **{insight.title}**\n   {insight.description}\n")
        
        # Add domain sections
        for domain_name, domain in sorted(domains.items(), key=lambda x: x[1].importance_score, reverse=True):
            sections.append(f"\n## Domain: {domain_name}\n")
            
            # Domain overview
            sections.append(f"- **Memories**: {len(domain.memories)}\n")
            sections.append(f"- **Importance**: {domain.importance_score:.1f}/10\n")
            if domain.temporal_range:
                sections.append(f"- **Time Span**: {domain.temporal_range[0].strftime('%Y-%m-%d')} to "
                              f"{domain.temporal_range[1].strftime('%Y-%m-%d')}\n")
            
            # Sub-topics
            if domain.sub_topics:
                sections.append(f"- **Sub-topics**: {', '.join(list(domain.sub_topics.keys())[:5])}\n")
            
            # Key memories
            sections.append("\n### Key Content\n")
            for memory in domain.memories[:3]:
                sections.append(f"- {memory['content'][:150]}...\n")
        
        return "\n".join(sections)
    
    async def _create_technical_summary(
        self,
        domains: Dict[str, KnowledgeDomain],
        key_insights: List[str]
    ) -> str:
        """Create technical summary focusing on technical details"""
        # Filter for technical content
        tech_domains = {
            name: domain for name, domain in domains.items()
            if any(tech_word in name.lower() for tech_word in 
                   ['code', 'api', 'system', 'data', 'algorithm', 'tech'])
        }
        
        if not tech_domains:
            tech_domains = domains  # Fall back to all domains
        
        # Prepare technical content
        content_parts = []
        for domain_name, domain in tech_domains.items():
            tech_memories = [m for m in domain.memories if 
                           any(word in m['content'].lower() for word in 
                               ['function', 'class', 'api', 'endpoint', 'algorithm'])]
            
            if tech_memories:
                content_parts.append(f"\n{domain_name}:")
                for memory in tech_memories[:3]:
                    content_parts.append(f"- {memory['content'][:200]}...")
        
        content = "\n".join(content_parts)
        
        # Generate technical summary
        prompt = self.summary_templates[SummaryType.TECHNICAL].format(content=content)
        
        try:
            summary = await self.openai_client.generate(
                prompt=prompt,
                max_tokens=800,
                temperature=0.5
            )
            return summary
        except Exception as e:
            logger.error(f"Technical summary generation failed: {e}")
            return self._create_fallback_summary(tech_domains, key_insights)
    
    async def _create_learning_summary(
        self,
        domains: Dict[str, KnowledgeDomain],
        key_insights: List[str]
    ) -> str:
        """Create learning-oriented summary"""
        # Structure content for learning
        learning_structure = {
            'prerequisites': [],
            'core_concepts': [],
            'learning_path': [],
            'practice_areas': []
        }
        
        # Analyze domains for learning structure
        sorted_domains = sorted(domains.items(), key=lambda x: len(x[1].memories))
        
        for i, (domain_name, domain) in enumerate(sorted_domains):
            if i == 0:
                learning_structure['prerequisites'].append(domain_name)
            elif i < 3:
                learning_structure['core_concepts'].append(domain_name)
            else:
                learning_structure['practice_areas'].append(domain_name)
        
        # Create learning path
        for i, (domain_name, domain) in enumerate(sorted_domains):
            step = {
                'step': i + 1,
                'topic': domain_name,
                'concepts': list(domain.key_concepts)[:5],
                'estimated_items': len(domain.memories)
            }
            learning_structure['learning_path'].append(step)
        
        # Format content
        content = f"""
Learning Structure:
- Prerequisites: {', '.join(learning_structure['prerequisites'])}
- Core Concepts: {', '.join(learning_structure['core_concepts'])}
- Practice Areas: {', '.join(learning_structure['practice_areas'])}

Learning Path:
{self._format_learning_path(learning_structure['learning_path'])}

Key Insights for Learning:
{self._prepare_insights_summary(key_insights)}
"""
        
        # Generate learning summary
        prompt = self.summary_templates[SummaryType.LEARNING].format(content=content)
        
        try:
            summary = await self.openai_client.generate(
                prompt=prompt,
                max_tokens=800,
                temperature=0.7
            )
            return summary
        except Exception as e:
            logger.error(f"Learning summary generation failed: {e}")
            return self._create_fallback_summary(domains, key_insights)
    
    async def _create_topic_summaries(self, domains: Dict[str, KnowledgeDomain]) -> List[Dict[str, Any]]:
        """Create summaries for individual topics"""
        summaries = []
        
        for domain_name, domain in domains.items():
            # Create summary for main domain
            domain_summary = dict(
                topic_name=domain_name,
                summary=f"Domain containing {len(domain.memories)} memories covering "
                       f"{len(domain.key_concepts)} key concepts.",
                memory_count=len(domain.memories),
                key_points=[
                    f"Importance: {domain.importance_score:.1f}/10",
                    f"Key concepts: {', '.join(list(domain.key_concepts)[:3])}"
                ],
                temporal_coverage=self._format_temporal_coverage(domain.temporal_range)
            )
            summaries.append(domain_summary)
            
            # Create summaries for significant sub-topics
            for sub_topic, sub_memories in domain.sub_topics.items():
                if len(sub_memories) >= 3:  # Significant sub-topic
                    sub_summary = dict(
                        topic_name=f"{domain_name} → {sub_topic}",
                        summary=f"Sub-topic with {len(sub_memories)} related memories.",
                        memory_count=len(sub_memories),
                        key_points=[m['content'][:50] + "..." for m in sub_memories[:2]],
                        temporal_coverage=None
                    )
                    summaries.append(sub_summary)
        
        return summaries
    
    async def _create_domain_overviews(self, domains: Dict[str, KnowledgeDomain]) -> List[Dict[str, Any]]:
        """Create domain overview summaries"""
        overviews = []
        
        for domain_name, domain in sorted(domains.items(), key=lambda x: x[1].importance_score, reverse=True):
            # Calculate domain statistics
            memory_contents = [m['content'] for m in domain.memories]
            avg_length = np.mean([len(c) for c in memory_contents]) if memory_contents else 0
            
            overview = dict(
                domain_name=domain_name,
                description=f"Knowledge domain focused on {domain_name} with "
                           f"{len(domain.sub_topics)} identified sub-topics.",
                total_memories=len(domain.memories),
                sub_topics=list(domain.sub_topics.keys())[:10],  # Top 10 sub-topics
                importance_score=domain.importance_score,
                growth_trend=self._calculate_growth_trend(domain),
                key_contributors=[],  # Could be enhanced with author tracking
                metadata={
                    'avg_memory_length': int(avg_length),
                    'unique_concepts': len(domain.key_concepts),
                    'time_span_days': (domain.temporal_range[1] - domain.temporal_range[0]).days 
                                     if domain.temporal_range else 0
                }
            )
            overviews.append(overview)
        
        return overviews
    
    def _prepare_domain_summary(self, domains: Dict[str, KnowledgeDomain]) -> str:
        """Prepare domain summary text"""
        lines = []
        for domain_name, domain in sorted(domains.items(), key=lambda x: x[1].importance_score, reverse=True)[:5]:
            lines.append(f"- {domain_name}: {len(domain.memories)} memories, "
                        f"importance {domain.importance_score:.1f}/10")
        return "\n".join(lines)
    
    def _prepare_insights_summary(self, insights: List[str]) -> str:
        """Prepare insights summary text"""
        lines = []
        for i, insight in enumerate(insights[:5], 1):
            lines.append(f"{i}. {insight}")
        return "\n".join(lines)
    
    def _format_learning_path(self, path: List[Dict[str, Any]]) -> str:
        """Format learning path for display"""
        lines = []
        for step in path[:5]:
            lines.append(f"Step {step['step']}: {step['topic']} "
                        f"({step['estimated_items']} items)")
        return "\n".join(lines)
    
    def _format_temporal_coverage(self, temporal_range: Optional[Tuple[datetime, datetime]]) -> Optional[str]:
        """Format temporal coverage for display"""
        if not temporal_range:
            return None
        
        start, end = temporal_range
        days = (end - start).days
        
        if days == 0:
            return "Single day"
        elif days < 30:
            return f"{days} days"
        elif days < 365:
            return f"{days // 30} months"
        else:
            return f"{days // 365} years"
    
    def _calculate_growth_trend(self, domain: KnowledgeDomain) -> str:
        """Calculate growth trend for a domain"""
        if len(domain.memories) < 2:
            return "stable"
        
        # Sort memories by date
        sorted_memories = sorted(domain.memories, key=lambda m: m['created_at'])
        
        # Calculate memories per month for recent period
        recent_cutoff = datetime.utcnow() - timedelta(days=90)
        recent_memories = [m for m in sorted_memories if m['created_at'] > recent_cutoff]
        
        if len(recent_memories) > len(sorted_memories) * 0.5:
            return "growing"
        elif len(recent_memories) < len(sorted_memories) * 0.1:
            return "declining"
        else:
            return "stable"
    
    def _calculate_coverage_score(self, memories: List[Dict[str, Any]], domains: Dict[str, KnowledgeDomain]) -> float:
        """Calculate how well the summary covers the knowledge base"""
        if not memories:
            return 0.0
        
        # Factors for coverage score
        domain_diversity = min(len(domains) / 10, 1.0)  # More domains = better
        memory_coverage = min(len(memories) / 100, 1.0)  # More memories = better
        
        # Topic coverage within domains
        total_topics = sum(len(d.sub_topics) for d in domains.values())
        topic_diversity = min(total_topics / 20, 1.0)  # More topics = better
        
        # Temporal coverage
        if memories:
            time_range = max(m['created_at'] for m in memories) - min(m['created_at'] for m in memories)
            temporal_coverage = min(time_range.days / 365, 1.0)  # Longer range = better
        else:
            temporal_coverage = 0.0
        
        # Weighted average
        coverage_score = (
            domain_diversity * 0.3 +
            memory_coverage * 0.3 +
            topic_diversity * 0.2 +
            temporal_coverage * 0.2
        )
        
        return coverage_score
    
    def _create_fallback_summary(self, domains: Dict[str, KnowledgeDomain], insights: List[str]) -> str:
        """Create a basic fallback summary"""
        lines = [
            "# Knowledge Summary\n",
            f"This summary covers {len(domains)} domains:\n"
        ]
        
        for domain_name, domain in list(domains.items())[:5]:
            lines.append(f"- **{domain_name}**: {len(domain.memories)} memories")
        
        if insights:
            lines.append("\n## Key Insights\n")
            for insight in insights[:3]:
                lines.append(f"- {insight.title}")
        
        return "\n".join(lines)
    
    def _empty_summary_response(self, request: SummaryRequest) -> SummaryResponse:
        """Return empty summary response"""
        return SummaryResponse(
            summary_type=request.summary_type,
            content="No content available for summarization.",
            key_insights=[],
            topic_summaries=[],
            domain_overviews=[],
            word_count=0,
            reading_time_minutes=0,
            coverage_score=0.0,
            metadata={'empty': True}
        )