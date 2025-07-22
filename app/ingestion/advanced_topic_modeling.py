"""
Advanced topic modeling with transformer-based models and hierarchical clustering
"""

import logging
from collections import Counter, defaultdict
from typing import Any, Union

try:
    import numpy as np
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from bertopic import BERTopic
    from sentence_transformers import SentenceTransformer
    BERTOPIC_AVAILABLE = True
except ImportError:
    BERTOPIC_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from app.ingestion.models import Topic
from app.ingestion.topic_classifier import TopicClassifier

logger = logging.getLogger(__name__)


class AdvancedTopicModeling:
    """Advanced topic modeling with transformer models and hierarchical clustering"""

    def __init__(self,
                 enable_bertopic: bool = True,
                 enable_hierarchical: bool = True,
                 enable_dynamic: bool = True,
                 min_topic_size: int = 10,
                 nr_topics: Union[int, str] = "auto",
                 embedding_model: str | None = None):
        """
        Initialize advanced topic modeling
        
        Args:
            enable_bertopic: Use BERTopic for transformer-based topic modeling
            enable_hierarchical: Use hierarchical topic clustering
            enable_dynamic: Enable dynamic topic modeling over time
            min_topic_size: Minimum size of a topic
            nr_topics: Number of topics to reduce to
            embedding_model: Specific embedding model to use
        """
        self.enable_bertopic = enable_bertopic and BERTOPIC_AVAILABLE
        self.enable_hierarchical = enable_hierarchical and SKLEARN_AVAILABLE
        self.enable_dynamic = enable_dynamic
        self.min_topic_size = min_topic_size
        self.nr_topics = nr_topics

        # Initialize models
        self.bertopic_model = None
        self.embedding_model = None
        self.hierarchical_topics = {}

        # Fallback to basic topic classifier
        self.basic_classifier = TopicClassifier()

        # Initialize if available
        if self.enable_bertopic:
            self._initialize_bertopic(embedding_model)

    def _initialize_bertopic(self, embedding_model: str | None = None):
        """Initialize BERTopic model with optimal settings"""
        try:
            # Select embedding model
            if embedding_model:
                self.embedding_model = SentenceTransformer(embedding_model)
            else:
                # Auto-select based on availability and performance
                model_candidates = [
                    "all-MiniLM-L6-v2",  # Fast and good quality
                    "all-mpnet-base-v2",  # Higher quality
                    "paraphrase-MiniLM-L6-v2"  # Fallback
                ]

                for model_name in model_candidates:
                    try:
                        self.embedding_model = SentenceTransformer(model_name)
                        logger.info(f"Loaded embedding model: {model_name}")
                        break
                    except Exception:
                        continue

            # Initialize BERTopic with custom configuration
            self.bertopic_model = BERTopic(
                embedding_model=self.embedding_model,
                min_topic_size=self.min_topic_size,
                nr_topics=self.nr_topics,
                calculate_probabilities=True,
                verbose=False
            )

            logger.info("BERTopic model initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize BERTopic: {e}")
            self.enable_bertopic = False

    def extract_advanced_topics(self,
                              texts: Union[str, list[str]],
                              min_relevance: float = 0.3,
                              max_topics: int = 10,
                              include_hierarchy: bool = True) -> list[Topic]:
        """
        Extract topics using advanced modeling techniques
        
        Args:
            texts: Input text(s)
            min_relevance: Minimum topic relevance
            max_topics: Maximum number of topics
            include_hierarchy: Include hierarchical topic structure
            
        Returns:
            List of advanced topics with metadata
        """
        # Ensure texts is a list
        if isinstance(texts, str):
            texts = [texts]

        all_topics = []

        # Try BERTopic first
        if self.enable_bertopic and len(texts) >= 5:
            bertopic_results = self._extract_bertopic_topics(texts)
            all_topics.extend(bertopic_results)

        # Fall back to basic classification for smaller datasets
        if not all_topics:
            for text in texts:
                basic_topics = self.basic_classifier.extract_topics(
                    text, min_relevance, max_topics
                )
                all_topics.extend(basic_topics)

        # Apply hierarchical clustering if enabled
        if include_hierarchy and self.enable_hierarchical and len(all_topics) > 3:
            all_topics = self._apply_hierarchical_clustering(all_topics)

        # Filter and sort topics
        filtered_topics = [
            topic for topic in all_topics
            if topic.relevance >= min_relevance
        ]

        filtered_topics.sort(
            key=lambda t: (t.relevance * t.confidence),
            reverse=True
        )

        return filtered_topics[:max_topics]

    def _extract_bertopic_topics(self, texts: list[str]) -> list[Topic]:
        """Extract topics using BERTopic"""
        if not self.bertopic_model:
            return []

        topics_list = []

        try:
            # Fit BERTopic model
            topics, probs = self.bertopic_model.fit_transform(texts)

            # Get topic information
            topic_info = self.bertopic_model.get_topic_info()

            # Process each discovered topic
            for index, row in topic_info.iterrows():
                if row['Topic'] == -1:  # Skip outlier topic
                    continue

                topic_id = row['Topic']
                topic_words = self.bertopic_model.get_topic(topic_id)

                if not topic_words:
                    continue

                # Extract keywords and scores
                keywords = []
                keyword_scores = []

                for word, score in topic_words[:10]:
                    keywords.append(word)
                    keyword_scores.append(score)

                # Calculate relevance based on topic size and probability
                topic_size = row['Count']
                total_docs = len(texts)
                size_relevance = min(1.0, topic_size / (total_docs * 0.1))

                # Average probability for this topic
                topic_probs = [probs[i][topic_id] for i in range(len(texts))
                              if topics[i] == topic_id]
                avg_prob = np.mean(topic_probs) if topic_probs else 0.0

                relevance = (size_relevance + avg_prob) / 2

                # Generate readable topic name
                topic_name = self._generate_bertopic_name(keywords[:3], topic_id)

                # Create topic with rich metadata
                topic = Topic(
                    name=topic_name,
                    keywords=keywords[:7],
                    confidence=min(1.0, avg_prob * 1.5),
                    relevance=relevance,
                    hierarchy=["BERTopic", f"Cluster {topic_id}", topic_name],
                    metadata={
                        "model": "bertopic",
                        "cluster_id": topic_id,
                        "cluster_size": topic_size,
                        "keyword_scores": keyword_scores[:7],
                        "representative_docs": row.get('Representative_Docs', [])[:3]
                    }
                )

                topics_list.append(topic)

            # Add topic relationships
            if len(topics_list) > 1:
                self._add_topic_relationships(topics_list)

        except Exception as e:
            logger.error(f"BERTopic extraction failed: {e}")

        return topics_list

    def _apply_hierarchical_clustering(self, topics: list[Topic]) -> list[Topic]:
        """Apply hierarchical clustering to create topic hierarchies"""
        if len(topics) < 2:
            return topics

        try:
            # Create keyword vectors for clustering
            keyword_vectors = []
            all_keywords = set()

            for topic in topics:
                all_keywords.update(topic.keywords)

            keyword_to_idx = {kw: idx for idx, kw in enumerate(all_keywords)}

            # Create binary vectors for each topic
            for topic in topics:
                vector = np.zeros(len(all_keywords))
                for keyword in topic.keywords:
                    if keyword in keyword_to_idx:
                        vector[keyword_to_idx[keyword]] = 1
                keyword_vectors.append(vector)

            keyword_vectors = np.array(keyword_vectors)

            # Perform hierarchical clustering
            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=0.5,
                linkage='ward'
            )

            cluster_labels = clustering.fit_predict(keyword_vectors)

            # Build hierarchy
            cluster_topics = defaultdict(list)
            for idx, label in enumerate(cluster_labels):
                cluster_topics[label].append(topics[idx])

            # Update topic hierarchies
            for cluster_id, cluster_members in cluster_topics.items():
                # Find cluster theme
                cluster_keywords = Counter()
                for topic in cluster_members:
                    cluster_keywords.update(topic.keywords)

                # Most common keywords define the cluster
                common_keywords = [kw for kw, _ in cluster_keywords.most_common(3)]
                cluster_name = " & ".join(common_keywords[:2]) + " Cluster"

                # Update hierarchies
                for topic in cluster_members:
                    if not topic.hierarchy:
                        topic.hierarchy = []

                    # Prepend cluster to hierarchy
                    topic.hierarchy = [cluster_name] + topic.hierarchy

                    # Add cluster metadata
                    if not topic.metadata:
                        topic.metadata = {}
                    topic.metadata['cluster_id'] = cluster_id
                    topic.metadata['cluster_size'] = len(cluster_members)

        except Exception as e:
            logger.error(f"Hierarchical clustering failed: {e}")

        return topics

    def _add_topic_relationships(self, topics: list[Topic]):
        """Add relationship information between topics"""
        if len(topics) < 2:
            return

        try:
            # Calculate topic similarity matrix
            for i, topic1 in enumerate(topics):
                if not topic1.metadata:
                    topic1.metadata = {}

                topic1.metadata['related_topics'] = []

                for j, topic2 in enumerate(topics):
                    if i == j:
                        continue

                    # Calculate similarity based on keyword overlap
                    keywords1 = set(topic1.keywords)
                    keywords2 = set(topic2.keywords)

                    if keywords1 and keywords2:
                        jaccard = len(keywords1 & keywords2) / len(keywords1 | keywords2)

                        if jaccard > 0.2:  # Threshold for relationship
                            topic1.metadata['related_topics'].append({
                                'name': topic2.name,
                                'similarity': round(jaccard, 3),
                                'shared_keywords': list(keywords1 & keywords2)
                            })

                # Sort by similarity
                topic1.metadata['related_topics'].sort(
                    key=lambda x: x['similarity'],
                    reverse=True
                )

                # Keep only top 3 relationships
                topic1.metadata['related_topics'] = topic1.metadata['related_topics'][:3]

        except Exception as e:
            logger.error(f"Failed to add topic relationships: {e}")

    def _generate_bertopic_name(self, keywords: list[str], topic_id: int) -> str:
        """Generate readable name for BERTopic cluster"""
        if not keywords:
            return f"Topic {topic_id}"

        # Clean and capitalize keywords
        clean_keywords = []
        for kw in keywords[:2]:
            # Remove special characters and capitalize
            clean_kw = ''.join(c for c in kw if c.isalnum() or c.isspace())
            clean_kw = clean_kw.strip().title()
            if clean_kw:
                clean_keywords.append(clean_kw)

        if clean_keywords:
            return " & ".join(clean_keywords)
        else:
            return f"Topic {topic_id}"

    def extract_temporal_topics(self,
                              documents: list[dict],
                              time_field: str = "created_at",
                              min_relevance: float = 0.3) -> dict[str, list[Topic]]:
        """
        Extract topics over time for temporal analysis
        
        Args:
            documents: List of documents with timestamps
            time_field: Field containing timestamp
            min_relevance: Minimum topic relevance
            
        Returns:
            Dictionary mapping time periods to topics
        """
        if not self.enable_dynamic or not documents:
            return {}

        # Group documents by time period
        time_groups = defaultdict(list)

        for doc in documents:
            if time_field in doc and 'content' in doc:
                # Extract time period (e.g., month)
                timestamp = doc[time_field]
                if isinstance(timestamp, str):
                    # Parse ISO format assumption
                    time_period = timestamp[:7]  # YYYY-MM
                else:
                    time_period = str(timestamp)[:7]

                time_groups[time_period].append(doc['content'])

        # Extract topics for each time period
        temporal_topics = {}

        for period, texts in time_groups.items():
            if len(texts) >= 3:  # Minimum texts for meaningful topics
                topics = self.extract_advanced_topics(
                    texts,
                    min_relevance=min_relevance,
                    include_hierarchy=False  # Faster processing
                )
                temporal_topics[period] = topics

        return temporal_topics

    def get_topic_evolution(self, temporal_topics: dict[str, list[Topic]]) -> dict[str, Any]:
        """
        Analyze how topics evolve over time
        
        Args:
            temporal_topics: Topics organized by time period
            
        Returns:
            Topic evolution analysis
        """
        if not temporal_topics:
            return {}

        # Track topic presence across time
        topic_timeline = defaultdict(list)
        topic_first_seen = {}
        topic_last_seen = {}

        sorted_periods = sorted(temporal_topics.keys())

        for period in sorted_periods:
            topics = temporal_topics[period]

            for topic in topics:
                topic_key = topic.name
                topic_timeline[topic_key].append({
                    'period': period,
                    'relevance': topic.relevance,
                    'keywords': topic.keywords
                })

                if topic_key not in topic_first_seen:
                    topic_first_seen[topic_key] = period
                topic_last_seen[topic_key] = period

        # Analyze evolution patterns
        evolution_analysis = {
            'emerging_topics': [],
            'declining_topics': [],
            'stable_topics': [],
            'trending_topics': []
        }

        # Identify patterns
        recent_periods = sorted_periods[-3:] if len(sorted_periods) >= 3 else sorted_periods

        for topic_name, timeline in topic_timeline.items():
            appearances = len(timeline)
            total_periods = len(sorted_periods)

            # Calculate metrics
            presence_ratio = appearances / total_periods
            recent_presence = sum(1 for t in timeline if t['period'] in recent_periods)

            # Classify topic evolution
            if topic_first_seen[topic_name] in recent_periods:
                evolution_analysis['emerging_topics'].append({
                    'name': topic_name,
                    'first_seen': topic_first_seen[topic_name],
                    'appearances': appearances
                })
            elif topic_last_seen[topic_name] not in recent_periods:
                evolution_analysis['declining_topics'].append({
                    'name': topic_name,
                    'last_seen': topic_last_seen[topic_name],
                    'peak_relevance': max(t['relevance'] for t in timeline)
                })
            elif presence_ratio > 0.7:
                evolution_analysis['stable_topics'].append({
                    'name': topic_name,
                    'consistency': presence_ratio,
                    'avg_relevance': np.mean([t['relevance'] for t in timeline])
                })

            # Check for trending (increasing relevance)
            if len(timeline) >= 3:
                recent_relevances = [t['relevance'] for t in timeline[-3:]]
                if all(recent_relevances[i] <= recent_relevances[i+1]
                      for i in range(len(recent_relevances)-1)):
                    evolution_analysis['trending_topics'].append({
                        'name': topic_name,
                        'growth_rate': recent_relevances[-1] / recent_relevances[0],
                        'current_relevance': recent_relevances[-1]
                    })

        return evolution_analysis

    def export_topic_model(self, filepath: str):
        """Export the trained topic model for reuse"""
        if self.bertopic_model:
            try:
                self.bertopic_model.save(filepath)
                logger.info(f"Topic model exported to {filepath}")
            except Exception as e:
                logger.error(f"Failed to export topic model: {e}")

    def load_topic_model(self, filepath: str):
        """Load a previously trained topic model"""
        try:
            self.bertopic_model = BERTopic.load(filepath)
            self.enable_bertopic = True
            logger.info(f"Topic model loaded from {filepath}")
        except Exception as e:
            logger.error(f"Failed to load topic model: {e}")
            self.enable_bertopic = False
