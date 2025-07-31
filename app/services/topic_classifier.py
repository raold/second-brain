"""
Advanced topic classification and modeling service.

This service specializes in:
- Topic modeling using statistical and NLP techniques
- Hierarchical topic classification
- Topic evolution and trend analysis
- Cross-topic relationship mapping
"""

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from sklearn.cluster import KMeans
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import TfidfVectorizer

from app.utils.logging_config import get_logger
from app.utils.openai_client import get_openai_client

logger = get_logger(__name__)

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)


@dataclass
class TopicModel:
    """Represents a topic with comprehensive metadata"""
    id: str
    name: str
    keywords: list[tuple[str, float]]  # (keyword, weight)
    documents: list[str] = field(default_factory=list)
    coherence_score: float = 0.0
    prevalence: float = 0.0
    trend: str = "stable"  # growing, declining, stable
    related_topics: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TopicHierarchy:
    """Represents hierarchical topic structure"""
    parent_topic: TopicModel
    sub_topics: list[TopicModel] = field(default_factory=list)
    depth: int = 0


@dataclass
class TopicEvolution:
    """Tracks topic evolution over time"""
    topic_id: str
    timeline: list[tuple[datetime, float]]  # (timestamp, prevalence)
    keywords_evolution: dict[str, list[tuple[datetime, float]]] = field(default_factory=dict)


class TopicClassifier:
    """Advanced topic classification and modeling service"""

    def __init__(self, **kwargs):
        self.config = kwargs
        self.openai_client = None
        self.use_ai = kwargs.get('use_ai', True)

        # NLP components
        self.stemmer = PorterStemmer()
        self.stop_words = set(stopwords.words('english'))
        self.vectorizer = None
        self.lda_model = None
        self.topic_cache = {}

        # Topic modeling parameters
        self.n_topics = kwargs.get('n_topics', 10)
        self.min_topic_size = kwargs.get('min_topic_size', 3)
        self.coherence_threshold = kwargs.get('coherence_threshold', 0.5)

        if self.use_ai:
            try:
                self.openai_client = get_openai_client()
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}. Using statistical methods only.")
                self.use_ai = False

        logger.info(f"Initialized TopicClassifier (AI={'enabled' if self.use_ai else 'disabled'}, n_topics={self.n_topics})")

    def extract_topics(self, content: str) -> list[TopicModel]:
        """Extract topics using LDA topic modeling"""
        try:
            # Preprocess content
            processed_text = self._preprocess_text(content)

            if not processed_text:
                return []

            # Convert to document list (split by paragraphs for better modeling)
            documents = [p.strip() for p in content.split('\n\n') if p.strip() and len(p.strip()) > 50]

            if len(documents) < 2:
                # For single document, use keyword extraction instead
                return self._extract_topics_from_keywords(content)

            # Vectorize documents
            self.vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.8
            )

            doc_term_matrix = self.vectorizer.fit_transform(documents)

            # Apply LDA
            self.lda_model = LatentDirichletAllocation(
                n_components=min(self.n_topics, len(documents)),
                random_state=42,
                max_iter=50
            )

            lda_output = self.lda_model.fit_transform(doc_term_matrix)

            # Extract topics
            topics = []
            feature_names = self.vectorizer.get_feature_names_out()

            for idx, topic in enumerate(self.lda_model.components_):
                # Get top words for this topic
                top_indices = topic.argsort()[-10:][::-1]
                top_words = [(feature_names[i], topic[i]) for i in top_indices]

                # Calculate topic prevalence
                topic_prevalence = lda_output[:, idx].mean()

                # Generate topic name from top words
                topic_name = self._generate_topic_name(top_words)

                # Calculate coherence score
                coherence = self._calculate_coherence(top_words, documents)

                topic_model = TopicModel(
                    id=f"topic_{idx}",
                    name=topic_name,
                    keywords=top_words,
                    documents=[doc for i, doc in enumerate(documents) if lda_output[i, idx] > 0.2],
                    coherence_score=coherence,
                    prevalence=topic_prevalence,
                    trend=self._analyze_trend(topic_prevalence)
                )

                topics.append(topic_model)

            # Filter by coherence threshold
            topics = [t for t in topics if t.coherence_score >= self.coherence_threshold]

            # Sort by prevalence
            topics.sort(key=lambda t: t.prevalence, reverse=True)

            # Cache results
            self.topic_cache[hash(content)] = topics

            return topics[:10]

        except Exception as e:
            logger.error(f"Topic extraction failed: {e}")
            return self._extract_topics_from_keywords(content)

    def extract_advanced_topics(self, content: str) -> list[TopicModel]:
        """Extract topics with hierarchical clustering and advanced analysis"""
        try:
            # Get base topics
            base_topics = self.extract_topics(content)

            if not base_topics:
                return []

            # Enhance with clustering
            enhanced_topics = self._enhance_with_clustering(content, base_topics)

            # Add cross-topic relationships
            self._add_topic_relationships(enhanced_topics)

            # Apply AI enhancement if available
            if self.use_ai and self.openai_client:
                try:
                    enhanced_topics = self._enhance_topics_with_ai(content, enhanced_topics)
                except Exception as e:
                    logger.warning(f"AI topic enhancement failed: {e}")

            # Build hierarchies
            hierarchies = self._build_topic_hierarchies(enhanced_topics)

            # Flatten hierarchies for return
            all_topics = []
            for hierarchy in hierarchies:
                all_topics.append(hierarchy.parent_topic)
                all_topics.extend(hierarchy.sub_topics)

            # Remove duplicates and sort
            unique_topics = {t.id: t for t in all_topics}.values()
            return sorted(unique_topics, key=lambda t: t.prevalence, reverse=True)[:15]

        except Exception as e:
            logger.error(f"Advanced topic extraction failed: {e}")
            return self.extract_topics(content)

    def get_topic_statistics(self, topics: list[TopicModel]) -> dict[str, Any]:
        """Generate comprehensive statistics about topics"""
        try:
            if not topics:
                return {
                    "total_topics": 0,
                    "average_coherence": 0.0,
                    "topic_diversity": 0.0,
                    "dominant_topics": [],
                    "topic_coverage": 0.0
                }

            # Basic statistics
            coherence_scores = [t.coherence_score for t in topics]
            prevalence_scores = [t.prevalence for t in topics]

            # Calculate diversity (how different topics are from each other)
            diversity = self._calculate_topic_diversity(topics)

            # Find dominant topics
            dominant_topics = [t for t in topics if t.prevalence > 0.15]

            # Calculate keyword overlap
            all_keywords = set()
            keyword_overlap = 0
            for topic in topics:
                topic_keywords = set(kw[0] for kw in topic.keywords[:5])
                keyword_overlap += len(topic_keywords & all_keywords)
                all_keywords.update(topic_keywords)

            # Topic trends distribution
            trend_dist = Counter(t.trend for t in topics)

            return {
                "total_topics": len(topics),
                "average_coherence": sum(coherence_scores) / len(coherence_scores),
                "coherence_range": {
                    "min": min(coherence_scores),
                    "max": max(coherence_scores)
                },
                "average_prevalence": sum(prevalence_scores) / len(prevalence_scores),
                "topic_diversity": diversity,
                "dominant_topics": [{"name": t.name, "prevalence": t.prevalence} for t in dominant_topics],
                "topic_coverage": sum(prevalence_scores),
                "keyword_uniqueness": 1.0 - (keyword_overlap / max(len(all_keywords), 1)),
                "trend_distribution": dict(trend_dist),
                "hierarchical_depth": max(self._get_hierarchy_depth(topics), 1),
                "top_keywords": self._get_global_keywords(topics)[:10]
            }

        except Exception as e:
            logger.error(f"Topic statistics generation failed: {e}")
            return {}

    def extract_structured_data(self, content: str) -> dict[str, Any]:
        """Extract structured topic data from content"""
        try:
            topics = self.extract_topics(content)

            structured_data = {
                "topic_models": [],
                "topic_network": {},
                "keyword_index": {},
                "document_topics": {},
                "topic_evolution": []
            }

            # Build topic models
            for topic in topics:
                topic_data = {
                    "id": topic.id,
                    "name": topic.name,
                    "keywords": [{"word": kw[0], "weight": kw[1]} for kw in topic.keywords],
                    "prevalence": topic.prevalence,
                    "coherence": topic.coherence_score,
                    "document_count": len(topic.documents)
                }
                structured_data["topic_models"].append(topic_data)

            # Build keyword index
            for topic in topics:
                for keyword, weight in topic.keywords:
                    if keyword not in structured_data["keyword_index"]:
                        structured_data["keyword_index"][keyword] = []
                    structured_data["keyword_index"][keyword].append({
                        "topic_id": topic.id,
                        "weight": weight
                    })

            # Build topic network (relationships)
            for topic in topics:
                structured_data["topic_network"][topic.id] = {
                    "related": topic.related_topics,
                    "strength": [0.8] * len(topic.related_topics)  # Placeholder strengths
                }

            return structured_data

        except Exception as e:
            logger.error(f"Structured data extraction failed: {e}")
            return {}

    def extract_advanced_structured_data(self, content: str) -> dict[str, Any]:
        """Extract advanced structured topic data with temporal and hierarchical info"""
        try:
            # Get basic structured data
            data = self.extract_structured_data(content)

            # Get advanced topics for hierarchy
            advanced_topics = self.extract_advanced_topics(content)

            # Add hierarchical structure
            hierarchies = self._build_topic_hierarchies(advanced_topics)
            data["topic_hierarchies"] = []

            for hierarchy in hierarchies:
                hierarchy_data = {
                    "parent": {
                        "id": hierarchy.parent_topic.id,
                        "name": hierarchy.parent_topic.name
                    },
                    "children": [
                        {"id": st.id, "name": st.name} for st in hierarchy.sub_topics
                    ],
                    "depth": hierarchy.depth
                }
                data["topic_hierarchies"].append(hierarchy_data)

            # Add temporal analysis (simulated for single document)
            data["temporal_analysis"] = self._simulate_temporal_analysis(advanced_topics)

            # Add topic similarity matrix
            data["similarity_matrix"] = self._calculate_similarity_matrix(advanced_topics)

            return data

        except Exception as e:
            logger.error(f"Advanced structured data extraction failed: {e}")
            return self.extract_structured_data(content)

    def get_extraction_statistics(self, data: dict[str, Any]) -> dict[str, Any]:
        """Get statistics about extracted structured data"""
        try:
            topic_models = data.get("topic_models", [])
            keyword_index = data.get("keyword_index", {})
            hierarchies = data.get("topic_hierarchies", [])

            # Calculate statistics
            total_keywords = len(keyword_index)
            avg_keywords_per_topic = sum(len(t.get("keywords", [])) for t in topic_models) / max(len(topic_models), 1)

            # Hierarchy statistics
            hierarchy_depths = [h.get("depth", 0) for h in hierarchies]
            max_depth = max(hierarchy_depths) if hierarchy_depths else 0

            # Network statistics
            topic_network = data.get("topic_network", {})
            connections = sum(len(v.get("related", [])) for v in topic_network.values())

            return {
                "total_topics": len(topic_models),
                "total_unique_keywords": total_keywords,
                "average_keywords_per_topic": avg_keywords_per_topic,
                "hierarchy_levels": max_depth,
                "total_hierarchies": len(hierarchies),
                "network_connections": connections,
                "network_density": connections / max(len(topic_models) * (len(topic_models) - 1), 1),
                "has_temporal_data": "temporal_analysis" in data,
                "has_similarity_data": "similarity_matrix" in data
            }

        except Exception as e:
            logger.error(f"Extraction statistics generation failed: {e}")
            return {}

    def classify_domain(self, content: str, **kwargs) -> dict[str, Any]:
        """Classify content into topical domains based on topic analysis"""
        try:
            # Extract topics first
            topics = self.extract_advanced_topics(content)

            if not topics:
                return {"domains": [], "confidence_scores": {}}

            # Define topical domains based on keyword patterns
            domain_keywords = {
                "technical": ["software", "code", "system", "data", "algorithm", "api", "database", "framework"],
                "scientific": ["research", "study", "analysis", "hypothesis", "experiment", "theory", "evidence"],
                "business": ["market", "strategy", "customer", "revenue", "growth", "investment", "management"],
                "educational": ["learn", "teach", "student", "course", "knowledge", "skill", "training"],
                "creative": ["design", "art", "create", "inspiration", "innovation", "aesthetic", "style"]
            }

            # Calculate domain scores
            domain_scores = defaultdict(float)

            for topic in topics:
                topic_keywords = [kw[0].lower() for kw in topic.keywords[:10]]

                for domain, keywords in domain_keywords.items():
                    # Calculate overlap
                    overlap = sum(1 for kw in keywords if any(kw in tkw or tkw in kw for tkw in topic_keywords))
                    if overlap > 0:
                        domain_scores[domain] += overlap * topic.prevalence

            # Normalize scores
            total_score = sum(domain_scores.values())
            if total_score > 0:
                for domain in domain_scores:
                    domain_scores[domain] /= total_score

            # Sort domains by score
            sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)

            # Build response
            domains = []
            confidence_scores = {}

            for domain, score in sorted_domains[:3]:
                if score > 0.1:  # Minimum threshold
                    domains.append({
                        "name": domain,
                        "confidence": score,
                        "supporting_topics": [t.name for t in topics if self._topic_matches_domain(t, domain_keywords[domain])][:3]
                    })
                    confidence_scores[domain] = score

            return {
                "domains": domains,
                "confidence_scores": confidence_scores,
                "primary_domain": domains[0]["name"] if domains else "general"
            }

        except Exception as e:
            logger.error(f"Domain classification failed: {e}")
            return {"domains": [], "confidence_scores": {}}

    def get_domain_statistics(self, domains: list[dict[str, Any]]) -> dict[str, Any]:
        """Get statistics about domain classifications"""
        try:
            if not domains:
                return {
                    "total_domains": 0,
                    "primary_domain": None,
                    "average_confidence": 0.0,
                    "domain_distribution": {}
                }

            confidences = [d.get("confidence", 0.0) for d in domains]

            return {
                "total_domains": len(domains),
                "primary_domain": domains[0]["name"] if domains else None,
                "average_confidence": sum(confidences) / len(confidences),
                "confidence_range": {
                    "min": min(confidences),
                    "max": max(confidences)
                },
                "domain_distribution": {d["name"]: d["confidence"] for d in domains},
                "high_confidence_domains": [d["name"] for d in domains if d["confidence"] > 0.7],
                "supporting_topics_count": sum(len(d.get("supporting_topics", [])) for d in domains)
            }

        except Exception as e:
            logger.error(f"Domain statistics generation failed: {e}")
            return {}

    # Private helper methods

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for topic modeling"""
        # Convert to lowercase
        text = text.lower()

        # Remove special characters and digits
        text = re.sub(r'[^a-zA-Z\s]', ' ', text)

        # Tokenize
        tokens = word_tokenize(text)

        # Remove stopwords and stem
        processed_tokens = [
            self.stemmer.stem(token)
            for token in tokens
            if token not in self.stop_words and len(token) > 2
        ]

        return ' '.join(processed_tokens)

    def _extract_topics_from_keywords(self, content: str) -> list[TopicModel]:
        """Fallback method using keyword extraction"""
        try:
            # Simple keyword extraction
            words = re.findall(r'\b\w+\b', content.lower())
            word_freq = Counter(words)

            # Filter out common words
            common_words = self.stop_words | {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
            important_words = [(w, f) for w, f in word_freq.most_common(50) if w not in common_words and len(w) > 3]

            # Group into topics (simple clustering by co-occurrence)
            topics = []
            used_words = set()

            for word, freq in important_words[:20]:
                if word in used_words:
                    continue

                # Find related words
                related = [(w, f) for w, f in important_words if w != word and self._words_related(word, w, content)]
                related = sorted(related, key=lambda x: x[1], reverse=True)[:5]

                # Create topic
                keywords = [(word, float(freq) / len(words))] + [(w, float(f) / len(words)) for w, f in related]

                topic = TopicModel(
                    id=f"topic_kw_{len(topics)}",
                    name=f"{word.title()} Topic",
                    keywords=keywords,
                    prevalence=sum(kw[1] for kw in keywords),
                    coherence_score=0.6  # Default coherence
                )

                topics.append(topic)
                used_words.add(word)
                used_words.update(w for w, _ in related)

                if len(topics) >= 5:
                    break

            return topics

        except Exception as e:
            logger.error(f"Keyword topic extraction failed: {e}")
            return []

    def _generate_topic_name(self, top_words: list[tuple[str, float]]) -> str:
        """Generate a readable name for a topic"""
        # Use top 3 words
        words = [w[0] for w in top_words[:3]]

        # Clean up words
        words = [w.replace('_', ' ').title() for w in words]

        return ' & '.join(words)

    def _calculate_coherence(self, top_words: list[tuple[str, float]], documents: list[str]) -> float:
        """Calculate topic coherence score"""
        try:
            # Simple coherence: how often top words appear together
            word_list = [w[0] for w in top_words[:5]]
            co_occurrences = 0
            total_occurrences = 0

            for doc in documents:
                doc_lower = doc.lower()
                words_in_doc = [w for w in word_list if w in doc_lower]

                if len(words_in_doc) >= 2:
                    co_occurrences += len(words_in_doc) * (len(words_in_doc) - 1) / 2
                total_occurrences += len(words_in_doc)

            if total_occurrences == 0:
                return 0.0

            coherence = co_occurrences / total_occurrences
            return min(coherence, 1.0)

        except Exception:
            return 0.5  # Default coherence

    def _analyze_trend(self, prevalence: float) -> str:
        """Analyze topic trend (simplified for single document)"""
        if prevalence > 0.3:
            return "growing"
        elif prevalence < 0.1:
            return "declining"
        else:
            return "stable"

    def _enhance_with_clustering(self, content: str, base_topics: list[TopicModel]) -> list[TopicModel]:
        """Enhance topics with clustering analysis"""
        try:
            if len(base_topics) < 3:
                return base_topics

            # Create feature vectors from topic keywords
            topic_features = []
            for topic in base_topics:
                features = {kw[0]: kw[1] for kw in topic.keywords[:10]}
                topic_features.append(features)

            # Convert to matrix
            all_keywords = set()
            for features in topic_features:
                all_keywords.update(features.keys())

            feature_matrix = []
            for features in topic_features:
                row = [features.get(kw, 0.0) for kw in all_keywords]
                feature_matrix.append(row)

            # Apply K-means clustering
            n_clusters = min(3, len(base_topics) // 2)
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            clusters = kmeans.fit_predict(feature_matrix)

            # Update topics with cluster info
            for i, topic in enumerate(base_topics):
                topic.related_topics = [
                    base_topics[j].id for j in range(len(base_topics))
                    if i != j and clusters[i] == clusters[j]
                ]

            return base_topics

        except Exception as e:
            logger.warning(f"Topic clustering failed: {e}")
            return base_topics

    def _add_topic_relationships(self, topics: list[TopicModel]) -> None:
        """Add relationships between topics based on keyword overlap"""
        for i, topic1 in enumerate(topics):
            if topic1.related_topics:  # Skip if already has relationships
                continue

            keywords1 = set(kw[0] for kw in topic1.keywords[:5])

            for _j, topic2 in enumerate(topics[i+1:], i+1):
                keywords2 = set(kw[0] for kw in topic2.keywords[:5])

                # Calculate overlap
                overlap = len(keywords1 & keywords2)
                if overlap >= 2:
                    topic1.related_topics.append(topic2.id)
                    topic2.related_topics.append(topic1.id)

    def _build_topic_hierarchies(self, topics: list[TopicModel]) -> list[TopicHierarchy]:
        """Build hierarchical structure from topics"""
        hierarchies = []

        # Simple hierarchy: group by prevalence
        sorted_topics = sorted(topics, key=lambda t: t.prevalence, reverse=True)

        # Top topics become parents
        parent_topics = sorted_topics[:3]
        remaining_topics = sorted_topics[3:]

        for parent in parent_topics:
            hierarchy = TopicHierarchy(
                parent_topic=parent,
                sub_topics=[],
                depth=1
            )

            # Assign children based on keyword overlap
            parent_keywords = set(kw[0] for kw in parent.keywords[:5])

            for topic in remaining_topics[:]:
                topic_keywords = set(kw[0] for kw in topic.keywords[:5])

                if len(parent_keywords & topic_keywords) >= 2:
                    hierarchy.sub_topics.append(topic)
                    remaining_topics.remove(topic)

                    if len(hierarchy.sub_topics) >= 3:
                        break

            hierarchies.append(hierarchy)

        return hierarchies

    def _calculate_topic_diversity(self, topics: list[TopicModel]) -> float:
        """Calculate how diverse the topics are"""
        if len(topics) < 2:
            return 0.0

        # Calculate pairwise keyword overlap
        total_overlap = 0
        comparisons = 0

        for i, topic1 in enumerate(topics):
            keywords1 = set(kw[0] for kw in topic1.keywords[:5])

            for topic2 in topics[i+1:]:
                keywords2 = set(kw[0] for kw in topic2.keywords[:5])

                overlap = len(keywords1 & keywords2)
                total_overlap += overlap / max(len(keywords1), len(keywords2))
                comparisons += 1

        if comparisons == 0:
            return 1.0

        # Lower overlap means higher diversity
        avg_overlap = total_overlap / comparisons
        diversity = 1.0 - avg_overlap

        return diversity

    def _get_hierarchy_depth(self, topics: list[TopicModel]) -> int:
        """Get maximum hierarchy depth"""
        hierarchies = self._build_topic_hierarchies(topics)
        if not hierarchies:
            return 1

        max_depth = max(h.depth + (1 if h.sub_topics else 0) for h in hierarchies)
        return max_depth

    def _get_global_keywords(self, topics: list[TopicModel]) -> list[tuple[str, float]]:
        """Get global keywords across all topics"""
        keyword_weights = defaultdict(float)

        for topic in topics:
            for keyword, weight in topic.keywords:
                keyword_weights[keyword] += weight * topic.prevalence

        # Sort by weight
        sorted_keywords = sorted(keyword_weights.items(), key=lambda x: x[1], reverse=True)
        return sorted_keywords

    def _words_related(self, word1: str, word2: str, content: str) -> bool:
        """Check if two words are related in the content"""
        # Simple co-occurrence check
        sentences = re.split(r'[.!?]+', content.lower())
        co_occurrences = sum(1 for s in sentences if word1 in s and word2 in s)
        return co_occurrences >= 2

    def _topic_matches_domain(self, topic: TopicModel, domain_keywords: list[str]) -> bool:
        """Check if a topic matches a domain"""
        topic_keywords = [kw[0].lower() for kw in topic.keywords[:10]]
        matches = sum(1 for dkw in domain_keywords if any(dkw in tkw or tkw in dkw for tkw in topic_keywords))
        return matches >= 2

    def _simulate_temporal_analysis(self, topics: list[TopicModel]) -> list[dict[str, Any]]:
        """Simulate temporal analysis for single document"""
        # In a real system, this would track topics over time
        temporal_data = []

        for topic in topics[:5]:  # Top 5 topics
            temporal_data.append({
                "topic_id": topic.id,
                "topic_name": topic.name,
                "timeline": [
                    {"timestamp": datetime.now().isoformat(), "prevalence": topic.prevalence}
                ],
                "trend": topic.trend,
                "forecast": "stable"  # Would be calculated from historical data
            })

        return temporal_data

    def _calculate_similarity_matrix(self, topics: list[TopicModel]) -> dict[str, dict[str, float]]:
        """Calculate similarity matrix between topics"""
        matrix = {}

        for i, topic1 in enumerate(topics):
            matrix[topic1.id] = {}
            keywords1 = {kw[0]: kw[1] for kw in topic1.keywords[:10]}

            for j, topic2 in enumerate(topics):
                if i == j:
                    matrix[topic1.id][topic2.id] = 1.0
                else:
                    # Calculate cosine similarity based on keyword overlap
                    keywords2 = {kw[0]: kw[1] for kw in topic2.keywords[:10]}

                    common_keywords = set(keywords1.keys()) & set(keywords2.keys())
                    if not common_keywords:
                        similarity = 0.0
                    else:
                        dot_product = sum(keywords1[k] * keywords2[k] for k in common_keywords)
                        norm1 = math.sqrt(sum(v**2 for v in keywords1.values()))
                        norm2 = math.sqrt(sum(v**2 for v in keywords2.values()))

                        similarity = dot_product / (norm1 * norm2) if norm1 * norm2 > 0 else 0.0

                    matrix[topic1.id][topic2.id] = similarity

        return matrix

    def _enhance_topics_with_ai(self, content: str, topics: list[TopicModel]) -> list[TopicModel]:
        """Enhance topics using AI (placeholder for OpenAI integration)"""
        # This would use OpenAI to enhance topic names and add context
        # For now, return topics as-is
        return topics
