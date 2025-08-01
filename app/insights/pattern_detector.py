import asyncio
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import numpy as np

"""
Pattern detection algorithms for memory analysis
"""

from collections import Counter, defaultdict

from sklearn.cluster import DBSCAN

from .models import Pattern, PatternDetectionRequest, PatternType, TimeFrame


class PatternDetector:
    """Detects various patterns in memory usage and content"""

    def __init__(self, database):
        self.db = database
        self.min_pattern_confidence = 0.5

    async def detect_patterns(self, request: PatternDetectionRequest) -> list[Pattern]:
        """Main method to detect all requested pattern types"""
        patterns = []

        # Get memories for analysis
        memories = await self._get_memories_for_timeframe(request.time_frame)

        if not memories:
            return patterns

        # Detect patterns based on requested types
        pattern_types = request.pattern_types or list(PatternType)

        detection_tasks = []
        for pattern_type in pattern_types:
            if pattern_type == PatternType.TEMPORAL:
                detection_tasks.append(self._detect_temporal_patterns(memories, request))
            elif pattern_type == PatternType.SEMANTIC:
                detection_tasks.append(self._detect_semantic_patterns(memories, request))
            elif pattern_type == PatternType.BEHAVIORAL:
                detection_tasks.append(self._detect_behavioral_patterns(memories, request))
            elif pattern_type == PatternType.STRUCTURAL:
                detection_tasks.append(self._detect_structural_patterns(memories, request))
            elif pattern_type == PatternType.EVOLUTIONARY:
                detection_tasks.append(self._detect_evolutionary_patterns(memories, request))

        # Run all detection tasks concurrently
        pattern_results = await asyncio.gather(*detection_tasks)

        # Flatten results and filter by strength
        for pattern_list in pattern_results:
            for pattern in pattern_list:
                if pattern.strength >= request.min_strength:
                    patterns.append(pattern)

        return sorted(patterns, key=lambda p: p.strength, reverse=True)

    async def _get_memories_for_timeframe(self, time_frame: TimeFrame) -> list[dict[str, Any]]:
        """Get memories within specified timeframe"""
        now = datetime.utcnow()

        if time_frame == TimeFrame.DAILY:
            start_date = now - timedelta(days=1)
        elif time_frame == TimeFrame.WEEKLY:
            start_date = now - timedelta(weeks=1)
        elif time_frame == TimeFrame.MONTHLY:
            start_date = now - timedelta(days=30)
        elif time_frame == TimeFrame.QUARTERLY:
            start_date = now - timedelta(days=90)
        elif time_frame == TimeFrame.YEARLY:
            start_date = now - timedelta(days=365)
        else:  # ALL_TIME
            start_date = datetime.min

        # Query memories with access logs
        query = """
        SELECT m.*,
               COUNT(DISTINCT al.accessed_at::date) as access_days,
               COUNT(al.id) as total_accesses,
               MAX(al.accessed_at) as last_accessed
        FROM memories m
        LEFT JOIN access_logs al ON m.id = al.memory_id
        WHERE m.created_at >= $1
        GROUP BY m.id
        ORDER BY m.created_at DESC
        """

        return await self.db.fetch_all(query, start_date)

    async def _detect_temporal_patterns(
        self, memories: list[dict[str, Any]], request: PatternDetectionRequest
    ) -> list[Pattern]:
        """Detect time-based patterns in memory creation and access"""
        patterns = []

        # Analyze creation time patterns
        creation_hours = defaultdict(int)
        creation_days = defaultdict(int)

        for memory in memories:
            created = memory["created_at"]
            creation_hours[created.hour] += 1
            creation_days[created.weekday()] += 1

        # Find peak hours
        peak_hours = sorted(creation_hours.items(), key=lambda x: x[1], reverse=True)[:3]

        if peak_hours and peak_hours[0][1] >= request.min_occurrences:
            pattern = Pattern(
                id=uuid4(),
                type=PatternType.TEMPORAL,
                name="Peak Creation Hours",
                description=f"Most memories created during hours {', '.join(str(h[0]) for h in peak_hours)}",
                strength=self._calculate_concentration_score(creation_hours.values()),
                occurrences=sum(h[1] for h in peak_hours),
                first_seen=min(m["created_at"] for m in memories),
                last_seen=max(m["created_at"] for m in memories),
                examples=[
                    {"hour": hour, "count": count, "percentage": count / len(memories) * 100}
                    for hour, count in peak_hours
                ],
                metadata={"distribution": dict(creation_hours)},
            )
            patterns.append(pattern)

        # Detect burst patterns
        burst_patterns = self._detect_burst_patterns(memories, request.min_occurrences)
        patterns.extend(burst_patterns)

        return patterns

    async def _detect_semantic_patterns(
        self, memories: list[dict[str, Any]], request: PatternDetectionRequest
    ) -> list[Pattern]:
        """Detect patterns in content similarity"""
        patterns = []

        # Group memories by semantic similarity
        if len(memories) < 10:
            return patterns

        # Get embeddings for clustering
        embeddings = []
        valid_memories = []

        for memory in memories:
            if memory.get("content_vector"):
                embeddings.append(memory["content_vector"])
                valid_memories.append(memory)

        if len(embeddings) < 10:
            return patterns

        # Perform DBSCAN clustering
        embeddings_array = np.array(embeddings)
        clustering = DBSCAN(eps=0.3, min_samples=request.min_occurrences)
        labels = clustering.fit_predict(embeddings_array)

        # Analyze clusters
        cluster_groups = defaultdict(list)
        for idx, label in enumerate(labels):
            if label != -1:  # Ignore noise
                cluster_groups[label].append(valid_memories[idx])

        # Create patterns for significant clusters
        for _cluster_id, cluster_memories in cluster_groups.items():
            if len(cluster_memories) >= request.min_occurrences:
                # Extract common themes
                all_tags = []
                for mem in cluster_memories:
                    if mem.get("tags"):
                        all_tags.extend(mem["tags"])

                common_tags = Counter(all_tags).most_common(5)

                pattern = Pattern(
                    id=uuid4(),
                    type=PatternType.SEMANTIC,
                    name=f"Semantic Cluster: {', '.join(tag[0] for tag in common_tags[:3])}",
                    description=f"Group of {len(cluster_memories)} semantically similar memories",
                    strength=self._calculate_cluster_coherence(cluster_memories, embeddings_array),
                    occurrences=len(cluster_memories),
                    first_seen=min(m["created_at"] for m in cluster_memories),
                    last_seen=max(m["created_at"] for m in cluster_memories),
                    examples=[
                        {
                            "memory_id": str(m["id"]),
                            "content_preview": m["content"][:100],
                            "importance": m.get("importance", 0),
                        }
                        for m in cluster_memories[:5]
                    ],
                    metadata={
                        "common_tags": dict(common_tags),
                        "cluster_size": len(cluster_memories),
                    },
                )
                patterns.append(pattern)

        return patterns

    async def _detect_behavioral_patterns(
        self, memories: list[dict[str, Any]], request: PatternDetectionRequest
    ) -> list[Pattern]:
        """Detect patterns in user behavior"""
        patterns = []

        # Analyze access patterns
        access_sequences = defaultdict(list)

        for memory in memories:
            if memory.get("total_accesses", 0) > 0:
                access_sequences[memory["id"]].append(
                    {
                        "accesses": memory["total_accesses"],
                        "importance": memory.get("importance", 0),
                        "tags": memory.get("tags", []),
                    }
                )

        # Detect frequently accessed memories
        high_access_memories = [
            m for m in memories if m.get("total_accesses", 0) >= request.min_occurrences
        ]

        if high_access_memories:
            pattern = Pattern(
                id=uuid4(),
                type=PatternType.BEHAVIORAL,
                name="High-Access Memories",
                description=f"Memories accessed frequently ({len(high_access_memories)} memories)",
                strength=self._calculate_access_concentration(memories),
                occurrences=sum(m["total_accesses"] for m in high_access_memories),
                first_seen=min(m["created_at"] for m in high_access_memories),
                last_seen=datetime.utcnow(),
                examples=[
                    {
                        "memory_id": str(m["id"]),
                        "content_preview": m["content"][:100],
                        "access_count": m["total_accesses"],
                    }
                    for m in sorted(
                        high_access_memories, key=lambda x: x["total_accesses"], reverse=True
                    )[:5]
                ],
                metadata={
                    "total_high_access": len(high_access_memories),
                    "average_accesses": np.mean(
                        [m["total_accesses"] for m in high_access_memories]
                    ),
                },
            )
            patterns.append(pattern)

        return patterns

    async def _detect_structural_patterns(
        self, memories: list[dict[str, Any]], request: PatternDetectionRequest
    ) -> list[Pattern]:
        """Detect patterns in memory organization (tags, metadata)"""
        patterns = []

        # Analyze tag co-occurrence
        tag_pairs = defaultdict(int)
        tag_frequency = defaultdict(int)

        for memory in memories:
            tags = memory.get("tags", [])
            for tag in tags:
                tag_frequency[tag] += 1

            # Count tag pairs
            for i, tag1 in enumerate(tags):
                for tag2 in tags[i + 1 :]:
                    pair = tuple(sorted([tag1, tag2]))
                    tag_pairs[pair] += 1

        # Find frequently co-occurring tags
        frequent_pairs = [
            (pair, count) for pair, count in tag_pairs.items() if count >= request.min_occurrences
        ]

        if frequent_pairs:
            frequent_pairs.sort(key=lambda x: x[1], reverse=True)

            pattern = Pattern(
                id=uuid4(),
                type=PatternType.STRUCTURAL,
                name="Tag Co-occurrence Pattern",
                description="Frequently paired tags in memories",
                strength=self._calculate_association_strength(frequent_pairs, tag_frequency),
                occurrences=sum(count for _, count in frequent_pairs),
                first_seen=min(m["created_at"] for m in memories),
                last_seen=max(m["created_at"] for m in memories),
                examples=[
                    {
                        "tag_pair": list(pair),
                        "count": count,
                        "lift": count
                        / (tag_frequency[pair[0]] * tag_frequency[pair[1]] / len(memories)),
                    }
                    for pair, count in frequent_pairs[:5]
                ],
                metadata={
                    "total_pairs": len(frequent_pairs),
                    "tag_frequencies": dict(
                        sorted(tag_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
                    ),
                },
            )
            patterns.append(pattern)

        return patterns

    async def _detect_evolutionary_patterns(
        self, memories: list[dict[str, Any]], request: PatternDetectionRequest
    ) -> list[Pattern]:
        """Detect how knowledge evolves over time"""
        patterns = []

        # Group memories by time periods
        time_buckets = defaultdict(list)

        for memory in memories:
            # Bucket by week
            week_start = memory["created_at"].date() - timedelta(
                days=memory["created_at"].weekday()
            )
            time_buckets[week_start].append(memory)

        if len(time_buckets) < 2:
            return patterns

        # Analyze evolution of topics/tags
        weekly_tags = {}
        for week, week_memories in sorted(time_buckets.items()):
            tags = []
            for mem in week_memories:
                tags.extend(mem.get("tags", []))
            weekly_tags[week] = Counter(tags)

        # Detect emerging topics
        emerging_topics = self._find_emerging_topics(weekly_tags)

        if emerging_topics:
            pattern = Pattern(
                id=uuid4(),
                type=PatternType.EVOLUTIONARY,
                name="Emerging Topics",
                description="Topics showing increasing frequency over time",
                strength=self._calculate_trend_strength(emerging_topics, weekly_tags),
                occurrences=len(emerging_topics),
                first_seen=min(time_buckets.keys()),
                last_seen=max(time_buckets.keys()),
                examples=[
                    {
                        "topic": topic,
                        "growth_rate": growth,
                        "timeline": self._get_topic_timeline(topic, weekly_tags),
                    }
                    for topic, growth in emerging_topics[:5]
                ],
                metadata={
                    "time_periods": len(time_buckets),
                    "total_emerging": len(emerging_topics),
                },
            )
            patterns.append(pattern)

        return patterns

    def _detect_burst_patterns(
        self, memories: list[dict[str, Any]], min_burst_size: int
    ) -> list[Pattern]:
        """Detect bursts in memory creation"""
        patterns = []

        # Sort by creation time
        sorted_memories = sorted(memories, key=lambda m: m["created_at"])

        # Detect bursts (many memories in short time)
        bursts = []
        current_burst = []

        for _i, memory in enumerate(sorted_memories):
            if not current_burst:
                current_burst.append(memory)
            else:
                time_diff = (memory["created_at"] - current_burst[-1]["created_at"]).total_seconds()

                if time_diff <= 3600:  # Within 1 hour
                    current_burst.append(memory)
                else:
                    if len(current_burst) >= min_burst_size:
                        bursts.append(current_burst)
                    current_burst = [memory]

        # Check last burst
        if len(current_burst) >= min_burst_size:
            bursts.append(current_burst)

        # Create patterns for bursts
        for burst in bursts:
            duration = (burst[-1]["created_at"] - burst[0]["created_at"]).total_seconds() / 60

            pattern = Pattern(
                id=uuid4(),
                type=PatternType.TEMPORAL,
                name="Memory Creation Burst",
                description=f"Rapid creation of {len(burst)} memories in {duration:.1f} minutes",
                strength=len(burst) / max(duration, 1) * 0.1,  # Normalize
                occurrences=len(burst),
                first_seen=burst[0]["created_at"],
                last_seen=burst[-1]["created_at"],
                examples=[
                    {
                        "memory_id": str(m["id"]),
                        "content_preview": m["content"][:50],
                        "created_at": m["created_at"].isoformat(),
                    }
                    for m in burst[:5]
                ],
                metadata={
                    "burst_duration_minutes": duration,
                    "memories_per_minute": len(burst) / max(duration, 1),
                },
            )
            patterns.append(pattern)

        return patterns

    def _calculate_concentration_score(self, values: list[int]) -> float:
        """Calculate how concentrated values are (0-1)"""
        if not values:
            return 0.0

        total = sum(values)
        if total == 0:
            return 0.0

        # Calculate entropy
        probs = [v / total for v in values if v > 0]
        entropy = -sum(p * np.log2(p) for p in probs)
        max_entropy = np.log2(len(values))

        # Normalize (1 - normalized entropy gives concentration)
        return 1 - (entropy / max_entropy) if max_entropy > 0 else 0.0

    def _calculate_cluster_coherence(
        self, cluster_memories: list[dict[str, Any]], all_embeddings: np.ndarray
    ) -> float:
        """Calculate coherence of a cluster"""
        # Simplified coherence based on cluster size and importance
        size_factor = min(len(cluster_memories) / 20, 1.0)
        avg_importance = np.mean([m.get("importance", 0) for m in cluster_memories])
        importance_factor = avg_importance / 10.0

        return (size_factor + importance_factor) / 2

    def _calculate_access_concentration(self, memories: list[dict[str, Any]]) -> float:
        """Calculate concentration of accesses"""
        accesses = [m.get("total_accesses", 0) for m in memories]
        if not accesses or sum(accesses) == 0:
            return 0.0

        # Gini coefficient for concentration
        sorted_accesses = sorted(accesses)
        n = len(sorted_accesses)
        index = np.arange(1, n + 1)
        gini = (2 * np.sum(index * sorted_accesses)) / (n * np.sum(sorted_accesses)) - (n + 1) / n

        return gini

    def _calculate_association_strength(
        self, pairs: list[tuple[tuple[str, str], int]], frequencies: dict[str, int]
    ) -> float:
        """Calculate strength of tag associations"""
        if not pairs:
            return 0.0

        # Average lift of top pairs
        lifts = []
        total_items = sum(frequencies.values())

        for (tag1, tag2), count in pairs[:10]:
            expected = (frequencies[tag1] * frequencies[tag2]) / total_items
            if expected > 0:
                lift = count / expected
                lifts.append(min(lift, 5.0) / 5.0)  # Cap at 5 and normalize

        return np.mean(lifts) if lifts else 0.0

    def _find_emerging_topics(self, weekly_tags: dict[Any, Counter]) -> list[tuple[str, float]]:
        """Find topics with increasing frequency"""
        emerging = []
        weeks = sorted(weekly_tags.keys())

        if len(weeks) < 2:
            return emerging

        # Get all unique tags
        all_tags = set()
        for counter in weekly_tags.values():
            all_tags.update(counter.keys())

        # Calculate growth for each tag
        for tag in all_tags:
            frequencies = [weekly_tags[week].get(tag, 0) for week in weeks]

            # Skip if not present in recent weeks
            if frequencies[-1] == 0:
                continue

            # Calculate trend
            if len(frequencies) >= 3:
                # Simple linear regression
                x = np.arange(len(frequencies))
                if np.sum(frequencies) > 0:
                    slope, _ = np.polyfit(x, frequencies, 1)

                    # Positive slope indicates growth
                    if slope > 0:
                        growth_rate = slope / (np.mean(frequencies) + 1)
                        emerging.append((tag, growth_rate))

        return sorted(emerging, key=lambda x: x[1], reverse=True)

    def _calculate_trend_strength(
        self, trends: list[tuple[str, float]], weekly_data: dict[Any, Counter]
    ) -> float:
        """Calculate strength of trend patterns"""
        if not trends:
            return 0.0

        # Average normalized growth rate of top trends
        strengths = []
        for _topic, growth in trends[:5]:
            # Normalize growth rate
            normalized = min(growth, 2.0) / 2.0
            strengths.append(normalized)

        return np.mean(strengths)

    def _get_topic_timeline(
        self, topic: str, weekly_tags: dict[Any, Counter]
    ) -> list[dict[str, Any]]:
        """Get timeline of topic frequency"""
        timeline = []

        for week in sorted(weekly_tags.keys()):
            count = weekly_tags[week].get(topic, 0)
            timeline.append({"week": week.isoformat(), "count": count})

        return timeline
