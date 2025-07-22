"""
Topic modeling and classification component for the ingestion engine
"""

import logging
import re
from collections import Counter, defaultdict
from typing import Any, Union

try:
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.decomposition import LatentDirichletAllocation
    from sklearn.feature_extraction.text import TfidfVectorizer
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from app.ingestion.models import Topic

logger = logging.getLogger(__name__)


class TopicClassifier:
    """Sophisticated topic modeling and classification"""

    def __init__(self,
                 enable_lda: bool = True,
                 enable_keyword: bool = True,
                 enable_domain: bool = True,
                 enable_advanced: bool = True,
                 n_topics: int = 10):
        """
        Initialize topic classifier

        Args:
            enable_lda: Use Latent Dirichlet Allocation
            enable_keyword: Use keyword-based classification
            enable_domain: Use domain detection
            enable_advanced: Use advanced topic modeling (BERTopic)
            n_topics: Number of topics for LDA
        """
        self.enable_lda = enable_lda and SKLEARN_AVAILABLE
        self.enable_keyword = enable_keyword
        self.enable_domain = enable_domain
        self.enable_advanced = enable_advanced
        self.n_topics = n_topics

        # Initialize domain patterns
        self.domain_patterns = self._initialize_domain_patterns()

        # Initialize keyword topics
        self.keyword_topics = self._initialize_keyword_topics()

        # LDA components (initialized on first use)
        self.vectorizer = None
        self.lda_model = None
        self.feature_names = None

        # Advanced topic modeling (lazy loaded)
        self._advanced_model = None

    def extract_topics(self,
                      text: str,
                      min_relevance: float = 0.5,
                      max_topics: int = 5) -> list[Topic]:
        """
        Extract topics from text using multiple methods

        Args:
            text: Input text
            min_relevance: Minimum topic relevance
            max_topics: Maximum number of topics to return

        Returns:
            List of extracted topics
        """
        all_topics = []

        # Keyword-based topic extraction
        if self.enable_keyword:
            keyword_topics = self._extract_keyword_topics(text)
            all_topics.extend(keyword_topics)

        # Domain detection
        if self.enable_domain:
            domain_topics = self._detect_domain_topics(text)
            all_topics.extend(domain_topics)

        # LDA topic modeling (for longer texts)
        if self.enable_lda and len(text.split()) > 50:
            lda_topics = self._extract_lda_topics(text)
            all_topics.extend(lda_topics)

        # Merge and rank topics
        merged_topics = self._merge_similar_topics(all_topics)

        # Filter by relevance and limit count
        filtered_topics = [
            topic for topic in merged_topics
            if topic.relevance >= min_relevance
        ]

        # Sort by relevance and confidence
        filtered_topics.sort(
            key=lambda t: (t.relevance * t.confidence),
            reverse=True
        )

        return filtered_topics[:max_topics]

    def _extract_keyword_topics(self, text: str) -> list[Topic]:
        """Extract topics based on keyword matching"""
        topics = []
        text_lower = text.lower()
        word_count = len(text.split())

        for topic_name, topic_info in self.keyword_topics.items():
            keywords = topic_info["keywords"]
            required = topic_info.get("required", [])
            boost_phrases = topic_info.get("boost_phrases", [])

            # Count keyword occurrences
            keyword_counts = {}
            total_matches = 0

            for keyword in keywords:
                count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
                if count > 0:
                    keyword_counts[keyword] = count
                    total_matches += count

            # Check required keywords
            if required:
                has_required = all(
                    re.search(r'\b' + re.escape(req) + r'\b', text_lower)
                    for req in required
                )
                if not has_required:
                    continue

            # Skip if no matches
            if total_matches == 0:
                continue

            # Calculate relevance based on keyword density
            keyword_density = total_matches / max(1, word_count)
            relevance = min(1.0, keyword_density * 10)  # Scale up small densities

            # Boost relevance for phrase matches
            boost_factor = 1.0
            for phrase in boost_phrases:
                if phrase.lower() in text_lower:
                    boost_factor *= 1.2

            relevance = min(1.0, relevance * boost_factor)

            # Calculate confidence based on unique keyword matches
            unique_matches = len(keyword_counts)
            confidence = min(1.0, unique_matches / max(3, len(keywords) * 0.3))

            # Extract top keywords found
            top_keywords = sorted(
                keyword_counts.keys(),
                key=keyword_counts.get,
                reverse=True
            )[:5]

            # Create topic hierarchy
            hierarchy = topic_info.get("hierarchy", [topic_name])

            topics.append(Topic(
                name=topic_name,
                keywords=top_keywords,
                confidence=confidence,
                relevance=relevance,
                hierarchy=hierarchy
            ))

        return topics

    def _detect_domain_topics(self, text: str) -> list[Topic]:
        """Detect domain-specific topics using patterns"""
        topics = []
        text_lower = text.lower()

        for domain, patterns in self.domain_patterns.items():
            domain_score = 0
            matched_patterns = []

            for pattern_info in patterns:
                pattern = pattern_info["pattern"]
                weight = pattern_info.get("weight", 1.0)

                matches = re.findall(pattern, text_lower)
                if matches:
                    domain_score += len(matches) * weight
                    matched_patterns.extend(matches[:3])  # Keep top 3 matches

            if domain_score > 0:
                # Normalize score
                relevance = min(1.0, domain_score / 10)
                confidence = min(1.0, len(matched_patterns) / 3)

                # Extract unique matched terms as keywords
                keywords = list(set(matched_patterns))[:5]

                topics.append(Topic(
                    name=f"{domain} Domain",
                    keywords=keywords,
                    confidence=confidence,
                    relevance=relevance,
                    hierarchy=["Domains", domain]
                ))

        return topics

    def _extract_lda_topics(self, text: str) -> list[Topic]:
        """Extract topics using Latent Dirichlet Allocation"""
        if not SKLEARN_AVAILABLE:
            return []

        topics = []

        try:
            # Prepare text
            documents = self._prepare_text_for_lda(text)

            # Initialize LDA if needed
            if self.vectorizer is None:
                self.vectorizer = TfidfVectorizer(
                    max_features=100,
                    min_df=1,
                    max_df=0.95,
                    stop_words='english',
                    ngram_range=(1, 2)
                )
                self.lda_model = LatentDirichletAllocation(
                    n_components=min(self.n_topics, len(documents)),
                    random_state=42,
                    max_iter=10
                )

            # Transform documents
            doc_term_matrix = self.vectorizer.fit_transform(documents)
            self.feature_names = self.vectorizer.get_feature_names_out()

            # Fit LDA model
            doc_topic_dist = self.lda_model.fit_transform(doc_term_matrix)

            # Extract topics
            for topic_idx in range(self.lda_model.n_components):
                # Get top words for this topic
                topic_word_dist = self.lda_model.components_[topic_idx]
                top_word_indices = topic_word_dist.argsort()[-10:][::-1]
                top_words = [self.feature_names[i] for i in top_word_indices]

                # Calculate topic relevance (average probability across documents)
                topic_relevance = float(np.mean(doc_topic_dist[:, topic_idx]))

                # Skip topics with very low relevance
                if topic_relevance < 0.1:
                    continue

                # Generate topic name from top words
                topic_name = self._generate_topic_name(top_words[:3])

                topics.append(Topic(
                    name=topic_name,
                    keywords=top_words[:5],
                    confidence=0.7,  # LDA confidence is moderate
                    relevance=topic_relevance,
                    hierarchy=["LDA Topics", topic_name]
                ))

        except Exception as e:
            logger.warning(f"LDA topic extraction failed: {e}")

        return topics

    def _prepare_text_for_lda(self, text: str) -> list[str]:
        """Prepare text for LDA by splitting into chunks"""
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)

        # Group sentences into documents (3-5 sentences each)
        documents = []
        current_doc = []

        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                current_doc.append(sentence)
                if len(current_doc) >= 3:
                    documents.append(" ".join(current_doc))
                    current_doc = []

        # Add remaining sentences
        if current_doc:
            documents.append(" ".join(current_doc))

        # If too few documents, split by paragraphs or create overlapping windows
        if len(documents) < 3:
            # Split by paragraphs
            paragraphs = text.split('\n\n')
            if len(paragraphs) > 1:
                documents = [p.strip() for p in paragraphs if p.strip()]
            else:
                # Create overlapping windows
                words = text.split()
                window_size = 50
                step = 25
                documents = []
                for i in range(0, len(words) - window_size + 1, step):
                    documents.append(" ".join(words[i:i + window_size]))

        return documents if documents else [text]

    def _merge_similar_topics(self, topics: list[Topic]) -> list[Topic]:
        """Merge similar topics based on keyword overlap"""
        if len(topics) <= 1:
            return topics

        merged = []
        processed = set()

        for i, topic1 in enumerate(topics):
            if i in processed:
                continue

            # Find similar topics
            similar_topics = [topic1]
            keywords1 = set(topic1.keywords)

            for j, topic2 in enumerate(topics[i+1:], i+1):
                if j in processed:
                    continue

                keywords2 = set(topic2.keywords)

                # Calculate Jaccard similarity
                intersection = len(keywords1 & keywords2)
                union = len(keywords1 | keywords2)
                similarity = intersection / union if union > 0 else 0

                # Also check name similarity
                name_similarity = self._calculate_name_similarity(topic1.name, topic2.name)

                # Merge if similar enough
                if similarity > 0.3 or name_similarity > 0.7:
                    similar_topics.append(topic2)
                    processed.add(j)

            # Merge the similar topics
            if len(similar_topics) > 1:
                merged_topic = self._merge_topic_group(similar_topics)
                merged.append(merged_topic)
            else:
                merged.append(topic1)

            processed.add(i)

        return merged

    def _merge_topic_group(self, topics: list[Topic]) -> Topic:
        """Merge a group of similar topics"""
        # Combine all keywords
        all_keywords = []
        keyword_counts = Counter()

        for topic in topics:
            all_keywords.extend(topic.keywords)
            for keyword in topic.keywords:
                keyword_counts[keyword] += 1

        # Get top keywords
        top_keywords = [
            keyword for keyword, _ in keyword_counts.most_common(7)
        ]

        # Average confidence and relevance
        avg_confidence = sum(t.confidence for t in topics) / len(topics)
        avg_relevance = sum(t.relevance for t in topics) / len(topics)

        # Use the most specific (longest) name
        best_name = max(topics, key=lambda t: len(t.name)).name

        # Combine hierarchies
        hierarchies = [t.hierarchy for t in topics if t.hierarchy]
        if hierarchies:
            # Use the most detailed hierarchy
            hierarchy = max(hierarchies, key=lambda h: len(h) if h else 0)
        else:
            hierarchy = None

        return Topic(
            name=best_name,
            keywords=top_keywords,
            confidence=avg_confidence,
            relevance=avg_relevance,
            hierarchy=hierarchy
        )

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between topic names"""
        # Simple word overlap similarity
        words1 = set(name1.lower().split())
        words2 = set(name2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union

    def _generate_topic_name(self, keywords: list[str]) -> str:
        """Generate a readable topic name from keywords"""
        # Filter out very short words
        meaningful_words = [w for w in keywords if len(w) > 3]

        if not meaningful_words:
            meaningful_words = keywords

        # Capitalize and join
        name_parts = [word.capitalize() for word in meaningful_words[:2]]
        return " & ".join(name_parts) + " Topic"

    def _initialize_domain_patterns(self) -> dict[str, list[dict[str, Any]]]:
        """Initialize domain detection patterns"""
        return {
            "Technology": [
                {"pattern": r"\b(python|java|javascript|code|programming|software)\b", "weight": 1.5},
                {"pattern": r"\b(api|sdk|framework|library|package)\b", "weight": 1.2},
                {"pattern": r"\b(database|sql|nosql|mongodb|postgresql)\b", "weight": 1.3},
                {"pattern": r"\b(cloud|aws|azure|gcp|docker|kubernetes)\b", "weight": 1.4},
                {"pattern": r"\b(machine learning|ai|neural network|deep learning)\b", "weight": 1.5},
            ],
            "Business": [
                {"pattern": r"\b(revenue|profit|roi|kpi|metrics)\b", "weight": 1.4},
                {"pattern": r"\b(strategy|planning|analysis|forecast)\b", "weight": 1.2},
                {"pattern": r"\b(customer|client|market|sales)\b", "weight": 1.3},
                {"pattern": r"\b(meeting|presentation|report|quarterly)\b", "weight": 1.1},
            ],
            "Science": [
                {"pattern": r"\b(research|study|experiment|hypothesis)\b", "weight": 1.4},
                {"pattern": r"\b(data|analysis|statistical|correlation)\b", "weight": 1.3},
                {"pattern": r"\b(theory|model|equation|formula)\b", "weight": 1.2},
                {"pattern": r"\b(discovery|finding|result|conclusion)\b", "weight": 1.3},
            ],
            "Health": [
                {"pattern": r"\b(health|medical|clinical|patient)\b", "weight": 1.5},
                {"pattern": r"\b(treatment|therapy|medication|diagnosis)\b", "weight": 1.4},
                {"pattern": r"\b(symptom|condition|disease|syndrome)\b", "weight": 1.3},
                {"pattern": r"\b(doctor|physician|nurse|healthcare)\b", "weight": 1.2},
            ],
            "Education": [
                {"pattern": r"\b(learning|education|teaching|curriculum)\b", "weight": 1.4},
                {"pattern": r"\b(student|teacher|professor|instructor)\b", "weight": 1.3},
                {"pattern": r"\b(course|class|lesson|lecture)\b", "weight": 1.3},
                {"pattern": r"\b(assignment|homework|exam|grade)\b", "weight": 1.2},
            ]
        }

    def _initialize_keyword_topics(self) -> dict[str, dict[str, Any]]:
        """Initialize keyword-based topic definitions"""
        return {
            "Project Management": {
                "keywords": ["project", "timeline", "milestone", "deliverable", "scope",
                           "budget", "resource", "stakeholder", "risk", "planning"],
                "boost_phrases": ["project plan", "risk management", "scope creep"],
                "hierarchy": ["Business", "Management", "Project Management"]
            },
            "Software Development": {
                "keywords": ["code", "development", "programming", "debug", "testing",
                           "deployment", "git", "version", "release", "bug"],
                "required": [],
                "boost_phrases": ["code review", "pull request", "continuous integration"],
                "hierarchy": ["Technology", "Development", "Software Development"]
            },
            "Data Science": {
                "keywords": ["data", "analysis", "model", "algorithm", "prediction",
                           "dataset", "feature", "training", "validation", "accuracy"],
                "boost_phrases": ["machine learning", "data pipeline", "model training"],
                "hierarchy": ["Technology", "Data", "Data Science"]
            },
            "Product Design": {
                "keywords": ["design", "user", "interface", "experience", "prototype",
                           "mockup", "wireframe", "usability", "feedback", "iteration"],
                "boost_phrases": ["user experience", "design system", "user research"],
                "hierarchy": ["Design", "Product", "Product Design"]
            },
            "Marketing": {
                "keywords": ["marketing", "campaign", "audience", "brand", "content",
                           "social", "engagement", "conversion", "analytics", "strategy"],
                "boost_phrases": ["content marketing", "social media", "conversion rate"],
                "hierarchy": ["Business", "Marketing"]
            },
            "Finance": {
                "keywords": ["finance", "budget", "revenue", "cost", "investment",
                           "profit", "expense", "cash", "forecast", "financial"],
                "boost_phrases": ["financial planning", "cash flow", "return on investment"],
                "hierarchy": ["Business", "Finance"]
            },
            "Personal Development": {
                "keywords": ["goal", "habit", "productivity", "mindset", "growth",
                           "motivation", "success", "improvement", "skill", "learning"],
                "boost_phrases": ["personal growth", "skill development", "goal setting"],
                "hierarchy": ["Personal", "Development"]
            },
            "Research": {
                "keywords": ["research", "study", "paper", "publication", "methodology",
                           "literature", "review", "citation", "abstract", "conclusion"],
                "boost_phrases": ["literature review", "research methodology", "peer review"],
                "hierarchy": ["Academic", "Research"]
            }
        }

    def get_topic_statistics(self, topics: list[Topic]) -> dict[str, Any]:
        """Get statistics about extracted topics"""
        if not topics:
            return {
                "total_topics": 0,
                "avg_confidence": 0,
                "avg_relevance": 0,
                "keyword_coverage": 0,
                "domain_distribution": {}
            }

        # Basic statistics
        total_topics = len(topics)
        avg_confidence = sum(t.confidence for t in topics) / total_topics
        avg_relevance = sum(t.relevance for t in topics) / total_topics

        # Keyword statistics
        all_keywords = set()
        for topic in topics:
            all_keywords.update(topic.keywords)

        # Domain distribution
        domain_counts = defaultdict(int)
        for topic in topics:
            if topic.hierarchy and len(topic.hierarchy) > 0:
                domain = topic.hierarchy[0]
                domain_counts[domain] += 1
            else:
                domain_counts["Uncategorized"] += 1

        return {
            "total_topics": total_topics,
            "avg_confidence": avg_confidence,
            "avg_relevance": avg_relevance,
            "unique_keywords": len(all_keywords),
            "avg_keywords_per_topic": sum(len(t.keywords) for t in topics) / total_topics,
            "domain_distribution": dict(domain_counts)
        }

    def extract_advanced_topics(self,
                               texts: Union[str, list[str]],
                               use_hierarchy: bool = True,
                               **kwargs) -> list[Topic]:
        """
        Extract topics using advanced transformer-based models

        Args:
            texts: Input text(s)
            use_hierarchy: Include hierarchical clustering
            **kwargs: Additional arguments for advanced modeling

        Returns:
            List of advanced topics
        """
        # Lazy load advanced model
        if self._advanced_model is None and self.enable_advanced:
            try:
                from app.ingestion.advanced_topic_modeling import AdvancedTopicModeling
                self._advanced_model = AdvancedTopicModeling()
            except ImportError:
                logger.warning("Advanced topic modeling not available")
                self.enable_advanced = False
                return self.extract_topics(texts[0] if isinstance(texts, list) else texts)

        if self._advanced_model:
            return self._advanced_model.extract_advanced_topics(
                texts,
                include_hierarchy=use_hierarchy,
                **kwargs
            )
        else:
            # Fallback to standard extraction
            if isinstance(texts, list):
                all_topics = []
                for text in texts:
                    topics = self.extract_topics(text, **kwargs)
                    all_topics.extend(topics)
                return all_topics[:kwargs.get('max_topics', 10)]
            else:
                return self.extract_topics(texts, **kwargs)
