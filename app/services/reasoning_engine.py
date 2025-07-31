"""
Multi-hop Reasoning Engine for Second Brain
Enables complex queries that traverse multiple memories to find connections and insights
"""

from app.utils.logging_config import get_logger
logger = get_logger(__name__)


class ReasoningType(Enum):
    """Types of reasoning operations"""
    CAUSAL = "causal"  # What caused X?
    TEMPORAL = "temporal"  # What happened before/after X?
    SEMANTIC = "semantic"  # What is related to X?
    EVOLUTIONARY = "evolutionary"  # How did X change over time?
    COMPARATIVE = "comparative"  # How does X compare to Y?


@dataclass
class ReasoningNode:
    """Represents a node in the reasoning path"""
    memory_id: str
    content: str
    relevance_score: float
    hop_number: int
    relationship_type: str
    metadata: dict[str, Any]


@dataclass
class ReasoningPath:
    """Represents a complete reasoning path from query to answer"""
    query: str
    nodes: list[ReasoningNode]
    total_score: float
    reasoning_type: ReasoningType
    insights: list[str]
    execution_time_ms: float


@dataclass
class ReasoningQuery:
    """Structured reasoning query"""
    text: str
    max_hops: int = 3
    reasoning_type: ReasoningType | None = None
    min_relevance: float = 0.5
    include_temporal: bool = True
    include_semantic: bool = True


class ReasoningEngine:
    """
    Multi-hop reasoning engine that can traverse memory connections
    to answer complex questions and discover insights
    """

    def __init__(self, database: Database):
        self.db = database
        self.max_paths = 10  # Maximum reasoning paths to explore
        self.beam_width = 5  # Beam search width for path exploration

    async def multi_hop_query(
        self,
        query: str,
        max_hops: int = 3,
        reasoning_type: ReasoningType | None = None
    ) -> list[ReasoningPath]:
        """
        Execute a multi-hop reasoning query

        Args:
            query: Natural language query
            max_hops: Maximum number of hops to traverse
            reasoning_type: Specific type of reasoning to apply

        Returns:
            List of reasoning paths ranked by relevance
        """
        # Validate inputs
        if not query or len(query.strip()) < 3:
            raise ValueError("Query must be at least 3 characters long")

        if max_hops < 1 or max_hops > 10:
            raise ValueError("max_hops must be between 1 and 10")

        if reasoning_type and not isinstance(reasoning_type, ReasoningType):
            raise ValueError(f"Invalid reasoning type: {reasoning_type}")

        start_time = datetime.now()

        # Parse and structure the query
        structured_query = await self._parse_query(query, max_hops, reasoning_type)

        # Find starting nodes based on query
        starting_nodes = await self._find_starting_nodes(structured_query)

        if not starting_nodes:
            logger.warning(f"No starting nodes found for query: {query}")
            return []

        # Execute multi-hop traversal
        paths = await self._execute_multi_hop(starting_nodes, structured_query)

        # Rank and filter paths
        ranked_paths = self._rank_paths(paths)

        # Extract insights from top paths
        for path in ranked_paths[:5]:
            path.insights = await self._extract_insights(path)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        for path in ranked_paths:
            path.execution_time_ms = execution_time

        logger.info(f"Multi-hop query completed in {execution_time:.2f}ms with {len(ranked_paths)} paths")
        return ranked_paths

    async def _parse_query(
        self,
        query: str,
        max_hops: int,
        reasoning_type: ReasoningType | None
    ) -> ReasoningQuery:
        """Parse natural language query into structured format"""

        # Detect reasoning type from query if not specified
        if not reasoning_type:
            reasoning_type = self._detect_reasoning_type(query)

        # Determine which relationship types to include
        include_temporal = any(word in query.lower() for word in [
            "when", "before", "after", "during", "timeline", "evolved", "changed"
        ])

        include_semantic = any(word in query.lower() for word in [
            "related", "similar", "like", "about", "concerning", "regarding"
        ])

        return ReasoningQuery(
            text=query,
            max_hops=max_hops,
            reasoning_type=reasoning_type,
            include_temporal=include_temporal,
            include_semantic=include_semantic
        )

    def _detect_reasoning_type(self, query: str) -> ReasoningType:
        """Detect the type of reasoning from the query text"""
        query_lower = query.lower()

        if any(word in query_lower for word in ["caused", "why", "because", "led to", "resulted"]):
            return ReasoningType.CAUSAL
        elif any(word in query_lower for word in ["evolve", "evolved", "changed", "developed", "progressed", "progression"]):
            return ReasoningType.EVOLUTIONARY
        elif any(word in query_lower for word in ["before", "after", "when", "timeline"]):
            return ReasoningType.TEMPORAL
        elif any(word in query_lower for word in ["compare", "differ", "difference", "similar", "versus"]):
            return ReasoningType.COMPARATIVE
        else:
            return ReasoningType.SEMANTIC

    async def _find_starting_nodes(self, query: ReasoningQuery) -> list[ReasoningNode]:
        """Find initial memory nodes to start reasoning from"""

        # Search for memories matching the query
        search_results = await self.db.contextual_search(
            query=query.text,
            limit=self.beam_width * 2,
            importance_threshold=0.3
        )

        starting_nodes = []
        for _idx, result in enumerate(search_results):
            node = ReasoningNode(
                memory_id=result["id"],
                content=result["content"],
                relevance_score=result.get("contextual_score", result.get("similarity", 0.5)),
                hop_number=0,
                relationship_type="query_match",
                metadata={
                    "memory_type": result.get("memory_type", "semantic"),
                    "importance_score": result.get("importance_score", 0.5),
                    "created_at": result.get("created_at"),
                }
            )
            starting_nodes.append(node)

        return starting_nodes[:self.beam_width]

    async def _execute_multi_hop(
        self,
        starting_nodes: list[ReasoningNode],
        query: ReasoningQuery
    ) -> list[ReasoningPath]:
        """Execute multi-hop traversal using beam search"""

        paths = []

        # Initialize paths with starting nodes
        current_paths = [
            ReasoningPath(
                query=query.text,
                nodes=[node],
                total_score=node.relevance_score,
                reasoning_type=query.reasoning_type,
                insights=[],
                execution_time_ms=0
            )
            for node in starting_nodes
        ]

        # Perform multi-hop traversal
        for hop in range(1, query.max_hops + 1):
            next_paths = []

            for path in current_paths:
                # Get the last node in the current path
                last_node = path.nodes[-1]

                # Find next hop candidates
                next_nodes = await self._find_next_hop_nodes(
                    last_node,
                    query,
                    hop,
                    visited_ids=set(n.memory_id for n in path.nodes)
                )

                # Create new paths with each next node
                for next_node in next_nodes:
                    new_path = ReasoningPath(
                        query=path.query,
                        nodes=path.nodes + [next_node],
                        total_score=self._calculate_path_score(path.nodes + [next_node]),
                        reasoning_type=path.reasoning_type,
                        insights=[],
                        execution_time_ms=0
                    )
                    next_paths.append(new_path)

            # Keep top paths using beam search
            next_paths.sort(key=lambda p: p.total_score, reverse=True)
            current_paths = next_paths[:self.beam_width]

            # Add completed paths to results
            paths.extend(current_paths)

        return paths

    async def _find_next_hop_nodes(
        self,
        current_node: ReasoningNode,
        query: ReasoningQuery,
        hop_number: int,
        visited_ids: set[str]
    ) -> list[ReasoningNode]:
        """Find candidate nodes for the next hop"""

        next_nodes = []

        # Find semantically related memories
        if query.include_semantic:
            semantic_nodes = await self._find_semantic_neighbors(
                current_node, query, visited_ids
            )
            next_nodes.extend(semantic_nodes)

        # Find temporally related memories
        if query.include_temporal:
            temporal_nodes = await self._find_temporal_neighbors(
                current_node, query, visited_ids
            )
            next_nodes.extend(temporal_nodes)

        # Score and filter nodes
        scored_nodes = []
        for node in next_nodes:
            node.hop_number = hop_number
            node.relevance_score = await self._score_node_relevance(
                node, current_node, query
            )

            if node.relevance_score >= query.min_relevance:
                scored_nodes.append(node)

        # Return top nodes
        scored_nodes.sort(key=lambda n: n.relevance_score, reverse=True)
        return scored_nodes[:self.beam_width]

    async def _find_semantic_neighbors(
        self,
        node: ReasoningNode,
        query: ReasoningQuery,
        visited_ids: set[str]
    ) -> list[ReasoningNode]:
        """Find semantically related memories"""

        # Search for similar memories
        results = await self.db.contextual_search(
            query=node.content[:200],  # Use first 200 chars as query
            limit=10,
            importance_threshold=0.2
        )

        neighbors = []
        for result in results:
            if result["id"] not in visited_ids and result["id"] != node.memory_id:
                neighbor = ReasoningNode(
                    memory_id=result["id"],
                    content=result["content"],
                    relevance_score=result.get("similarity", 0.5),
                    hop_number=0,  # Will be set later
                    relationship_type="semantic_similarity",
                    metadata={
                        "similarity_score": result.get("similarity", 0.5),
                        "memory_type": result.get("memory_type", "semantic"),
                    }
                )
                neighbors.append(neighbor)

        return neighbors

    async def _find_temporal_neighbors(
        self,
        node: ReasoningNode,
        query: ReasoningQuery,
        visited_ids: set[str]
    ) -> list[ReasoningNode]:
        """Find temporally related memories"""

        # This is a simplified version - in production, we'd query based on timestamps
        # For now, we'll use metadata timestamps if available

        created_at = node.metadata.get("created_at")
        if not created_at:
            return []

        # Search for memories around the same time
        # This would ideally be a custom query - for now using contextual search
        time_context = f"memories from around {created_at}"
        results = await self.db.contextual_search(
            query=time_context,
            limit=5,
            timeframe="last_year"  # Adjust based on the timestamp
        )

        neighbors = []
        for result in results:
            if result["id"] not in visited_ids and result["id"] != node.memory_id:
                neighbor = ReasoningNode(
                    memory_id=result["id"],
                    content=result["content"],
                    relevance_score=0.5,  # Base score for temporal
                    hop_number=0,
                    relationship_type="temporal_proximity",
                    metadata={
                        "temporal_distance": "close",  # Would calculate actual distance
                        "memory_type": result.get("memory_type", "episodic"),
                    }
                )
                neighbors.append(neighbor)

        return neighbors

    async def _score_node_relevance(
        self,
        node: ReasoningNode,
        previous_node: ReasoningNode,
        query: ReasoningQuery
    ) -> float:
        """Score the relevance of a node in the reasoning path"""

        # Base score from similarity
        score = node.relevance_score

        # Boost score based on reasoning type alignment
        if query.reasoning_type == ReasoningType.CAUSAL:
            if "because" in node.content.lower() or "caused" in node.content.lower():
                score *= 1.2
        elif query.reasoning_type == ReasoningType.TEMPORAL:
            if node.relationship_type == "temporal_proximity":
                score *= 1.3
        elif query.reasoning_type == ReasoningType.EVOLUTIONARY:
            if "changed" in node.content.lower() or "evolved" in node.content.lower():
                score *= 1.2

        # Decay score based on hop number
        hop_decay = 0.9 ** node.hop_number
        score *= hop_decay

        # Boost for high importance memories
        importance = node.metadata.get("importance_score", 0.5)
        if importance > 0.7:
            score *= 1.1

        return min(score, 1.0)

    def _calculate_path_score(self, nodes: list[ReasoningNode]) -> float:
        """Calculate the total score for a reasoning path"""
        if not nodes:
            return 0.0

        # Weighted average of node scores
        scores = [node.relevance_score for node in nodes]
        weights = [0.8 ** i for i in range(len(scores))]  # More weight to earlier nodes

        weighted_sum = sum(s * w for s, w in zip(scores, weights, strict=False))
        total_weight = sum(weights)

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _rank_paths(self, paths: list[ReasoningPath]) -> list[ReasoningPath]:
        """Rank reasoning paths by relevance and quality"""

        # Remove duplicate paths
        unique_paths = []
        seen_signatures = set()

        for path in paths:
            # Create a signature for the path
            signature = tuple(node.memory_id for node in path.nodes)
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_paths.append(path)

        # Sort by total score
        unique_paths.sort(key=lambda p: p.total_score, reverse=True)

        return unique_paths[:self.max_paths]

    async def _extract_insights(self, path: ReasoningPath) -> list[str]:
        """Extract insights from a reasoning path"""
        insights = []

        # Insight 1: Connection summary
        if len(path.nodes) > 1:
            start_content = path.nodes[0].content[:50]
            end_content = path.nodes[-1].content[:50]
            insights.append(
                f"Connected '{start_content}...' to '{end_content}...' through {len(path.nodes)-1} hops"
            )

        # Insight 2: Relationship types
        relationship_types = set(node.relationship_type for node in path.nodes[1:])
        if relationship_types:
            insights.append(
                f"Relationships discovered: {', '.join(relationship_types)}"
            )

        # Insight 3: Temporal progression (if applicable)
        if path.reasoning_type == ReasoningType.TEMPORAL:
            insights.append("Temporal progression identified in memory chain")

        # Insight 4: Pattern detection
        if path.reasoning_type == ReasoningType.EVOLUTIONARY:
            insights.append("Evolution pattern detected across memories")

        return insights

    async def trace_reasoning_path(
        self,
        start_memory_id: str,
        end_memory_id: str,
        max_hops: int = 5
    ) -> ReasoningPath | None:
        """
        Find the reasoning path between two specific memories

        Args:
            start_memory_id: Starting memory ID
            end_memory_id: Target memory ID
            max_hops: Maximum hops to explore

        Returns:
            ReasoningPath if found, None otherwise
        """
        # This is a simplified A* search implementation
        # In production, we'd use more sophisticated graph algorithms

        start_memory = await self.db.get_memory(start_memory_id)
        if not start_memory:
            return None

        start_node = ReasoningNode(
            memory_id=start_memory_id,
            content=start_memory["content"],
            relevance_score=1.0,
            hop_number=0,
            relationship_type="start",
            metadata=start_memory.get("metadata", {})
        )

        # Use BFS to find path
        queue = [(start_node, [start_node])]
        visited = {start_memory_id}

        while queue and len(visited) < 100:  # Limit exploration
            current_node, path = queue.pop(0)

            if current_node.memory_id == end_memory_id:
                return ReasoningPath(
                    query=f"Path from {start_memory_id} to {end_memory_id}",
                    nodes=path,
                    total_score=self._calculate_path_score(path),
                    reasoning_type=ReasoningType.SEMANTIC,
                    insights=[f"Found {len(path)}-hop connection"],
                    execution_time_ms=0
                )

            if len(path) < max_hops:
                # Get neighbors
                neighbors = await self._find_semantic_neighbors(
                    current_node,
                    ReasoningQuery(text="", max_hops=max_hops),
                    visited
                )

                for neighbor in neighbors:
                    if neighbor.memory_id not in visited:
                        visited.add(neighbor.memory_id)
                        neighbor.hop_number = len(path)
                        queue.append((neighbor, path + [neighbor]))

        return None

    async def find_causal_chains(
        self,
        event_memory_id: str,
        direction: str = "backward",
        max_depth: int = 3
    ) -> list[ReasoningPath]:
        """
        Find causal chains leading to or from an event

        Args:
            event_memory_id: The event memory to analyze
            direction: "backward" for causes, "forward" for effects
            max_depth: Maximum causal depth to explore

        Returns:
            List of causal reasoning paths
        """
        event_memory = await self.db.get_memory(event_memory_id)
        if not event_memory:
            return []

        # Extract event description for causal search
        event_desc = event_memory["content"]

        if direction == "backward":
            query = f"What caused or led to: {event_desc[:100]}"
        else:
            query = f"What resulted from or was caused by: {event_desc[:100]}"

        return await self.multi_hop_query(
            query=query,
            max_hops=max_depth,
            reasoning_type=ReasoningType.CAUSAL
        )
