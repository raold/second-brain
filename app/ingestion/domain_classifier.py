"""
Domain classification component for categorizing content into knowledge domains
"""

import logging
import re
from collections import Counter, defaultdict
from typing import Any, Optional, Union
import json

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.svm import LinearSVC
    from sklearn.ensemble import RandomForestClassifier
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)


class DomainClassifier:
    """Multi-label domain classification for content"""
    
    def __init__(self,
                 enable_ml_classification: bool = True,
                 enable_rule_based: bool = True,
                 enable_transformer: bool = False,
                 confidence_threshold: float = 0.3):
        """
        Initialize domain classifier
        
        Args:
            enable_ml_classification: Use ML models for classification
            enable_rule_based: Use rule-based classification
            enable_transformer: Use transformer models
            confidence_threshold: Minimum confidence for classification
        """
        self.enable_ml = enable_ml_classification and SKLEARN_AVAILABLE
        self.enable_rules = enable_rule_based
        self.enable_transformer = enable_transformer and TRANSFORMERS_AVAILABLE
        self.confidence_threshold = confidence_threshold
        
        # Initialize domain definitions
        self.domains = self._initialize_domains()
        self.domain_keywords = self._initialize_domain_keywords()
        self.domain_patterns = self._initialize_domain_patterns()
        self.domain_hierarchy = self._initialize_domain_hierarchy()
        
        # ML components
        self.vectorizer = None
        self.classifiers = {}
        self.transformer_classifier = None
        
        # Initialize models if needed
        if self.enable_ml:
            self._initialize_ml_models()
        
        if self.enable_transformer:
            self._initialize_transformer_model()
    
    def classify_domain(self, 
                       text: str, 
                       multi_label: bool = True,
                       include_hierarchy: bool = True) -> dict[str, Any]:
        """
        Classify text into one or more domains
        
        Args:
            text: Input text
            multi_label: Allow multiple domain labels
            include_hierarchy: Include hierarchical domain structure
            
        Returns:
            Domain classification results
        """
        results = {
            "domains": [],
            "confidence_scores": {},
            "method": [],
            "hierarchy": {} if include_hierarchy else None
        }
        
        # Rule-based classification
        if self.enable_rules:
            rule_results = self._classify_with_rules(text)
            results["domains"].extend(rule_results["domains"])
            results["confidence_scores"].update(rule_results["scores"])
            results["method"].append("rule_based")
        
        # ML classification
        if self.enable_ml and self.vectorizer:
            ml_results = self._classify_with_ml(text)
            for domain, score in ml_results.items():
                if score >= self.confidence_threshold:
                    if domain not in results["domains"]:
                        results["domains"].append(domain)
                    # Average scores if domain already exists
                    if domain in results["confidence_scores"]:
                        results["confidence_scores"][domain] = (
                            results["confidence_scores"][domain] + score
                        ) / 2
                    else:
                        results["confidence_scores"][domain] = score
            results["method"].append("machine_learning")
        
        # Transformer classification
        if self.enable_transformer and self.transformer_classifier:
            transformer_results = self._classify_with_transformer(text)
            for domain, score in transformer_results.items():
                if score >= self.confidence_threshold:
                    if domain not in results["domains"]:
                        results["domains"].append(domain)
                    # Weight transformer results higher
                    if domain in results["confidence_scores"]:
                        results["confidence_scores"][domain] = (
                            results["confidence_scores"][domain] * 0.3 + score * 0.7
                        )
                    else:
                        results["confidence_scores"][domain] = score
            results["method"].append("transformer")
        
        # Sort domains by confidence
        results["domains"] = sorted(
            results["domains"],
            key=lambda d: results["confidence_scores"].get(d, 0),
            reverse=True
        )
        
        # Apply multi-label constraint
        if not multi_label and results["domains"]:
            results["domains"] = results["domains"][:1]
        
        # Add hierarchical information
        if include_hierarchy:
            for domain in results["domains"]:
                if domain in self.domain_hierarchy:
                    results["hierarchy"][domain] = self.domain_hierarchy[domain]
        
        # Add domain metadata
        results["metadata"] = self._get_domain_metadata(results["domains"])
        
        return results
    
    def _classify_with_rules(self, text: str) -> dict[str, Any]:
        """Rule-based domain classification"""
        text_lower = text.lower()
        domain_scores = defaultdict(float)
        
        # Keyword matching
        for domain, keywords in self.domain_keywords.items():
            keyword_count = 0
            total_weight = 0
            
            for keyword_info in keywords:
                keyword = keyword_info["term"]
                weight = keyword_info.get("weight", 1.0)
                
                # Count occurrences
                count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
                if count > 0:
                    keyword_count += count * weight
                    total_weight += weight
            
            if keyword_count > 0:
                # Normalize by text length and keyword weights
                score = min(1.0, keyword_count / (len(text.split()) / 100))
                domain_scores[domain] = score
        
        # Pattern matching
        for domain, patterns in self.domain_patterns.items():
            pattern_matches = 0
            
            for pattern_info in patterns:
                pattern = pattern_info["pattern"]
                weight = pattern_info.get("weight", 1.0)
                
                matches = len(re.findall(pattern, text_lower))
                if matches > 0:
                    pattern_matches += matches * weight
            
            if pattern_matches > 0:
                # Combine with keyword score
                pattern_score = min(1.0, pattern_matches / 10)
                if domain in domain_scores:
                    domain_scores[domain] = (domain_scores[domain] + pattern_score) / 2
                else:
                    domain_scores[domain] = pattern_score
        
        # Filter by threshold
        filtered_domains = [
            domain for domain, score in domain_scores.items()
            if score >= self.confidence_threshold
        ]
        
        return {
            "domains": filtered_domains,
            "scores": dict(domain_scores)
        }
    
    def _classify_with_ml(self, text: str) -> dict[str, float]:
        """Machine learning based classification"""
        if not self.vectorizer or not self.classifiers:
            return {}
        
        try:
            # Vectorize text
            features = self.vectorizer.transform([text])
            
            domain_scores = {}
            
            # Get predictions from each classifier
            for domain, classifier in self.classifiers.items():
                if hasattr(classifier, "predict_proba"):
                    # Get probability for positive class
                    proba = classifier.predict_proba(features)[0]
                    score = proba[1] if len(proba) > 1 else proba[0]
                else:
                    # Binary prediction
                    prediction = classifier.predict(features)[0]
                    score = 1.0 if prediction == 1 else 0.0
                
                domain_scores[domain] = float(score)
            
            return domain_scores
            
        except Exception as e:
            logger.error(f"ML classification failed: {e}")
            return {}
    
    def _classify_with_transformer(self, text: str) -> dict[str, float]:
        """Transformer-based classification"""
        if not self.transformer_classifier:
            return {}
        
        try:
            # Get predictions
            results = self.transformer_classifier(text)
            
            # Map to domain scores
            domain_scores = {}
            for result in results:
                label = result["label"]
                score = result["score"]
                
                # Map label to domain
                domain = self._map_label_to_domain(label)
                if domain:
                    domain_scores[domain] = score
            
            return domain_scores
            
        except Exception as e:
            logger.error(f"Transformer classification failed: {e}")
            return {}
    
    def _initialize_ml_models(self):
        """Initialize ML classification models"""
        try:
            # Initialize vectorizer
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                ngram_range=(1, 2),
                stop_words='english'
            )
            
            # Initialize classifiers for each domain
            # In a real implementation, these would be trained on labeled data
            for domain in self.domains:
                # Use different classifiers for different domains
                if domain in ["Technology", "Science"]:
                    self.classifiers[domain] = LinearSVC(probability=True)
                else:
                    self.classifiers[domain] = MultinomialNB()
            
            logger.info("ML models initialized (requires training)")
            
        except Exception as e:
            logger.error(f"Failed to initialize ML models: {e}")
            self.enable_ml = False
    
    def _initialize_transformer_model(self):
        """Initialize transformer model for classification"""
        try:
            # Try to load a pre-trained classifier
            model_name = "facebook/bart-large-mnli"  # Zero-shot classification
            self.transformer_classifier = pipeline(
                "zero-shot-classification",
                model=model_name
            )
            
            logger.info(f"Transformer model loaded: {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize transformer model: {e}")
            self.enable_transformer = False
    
    def _map_label_to_domain(self, label: str) -> Optional[str]:
        """Map transformer output label to domain"""
        label_lower = label.lower()
        
        # Simple mapping - can be enhanced
        label_domain_map = {
            "technology": "Technology",
            "science": "Science",
            "business": "Business",
            "health": "Health",
            "education": "Education",
            "arts": "Arts",
            "sports": "Sports",
            "politics": "Politics",
            "entertainment": "Entertainment",
            "finance": "Finance"
        }
        
        for key, domain in label_domain_map.items():
            if key in label_lower:
                return domain
        
        return None
    
    def _get_domain_metadata(self, domains: list[str]) -> dict[str, Any]:
        """Get metadata for classified domains"""
        metadata = {}
        
        for domain in domains:
            if domain in self.domains:
                metadata[domain] = {
                    "description": self.domains[domain]["description"],
                    "parent": self.domains[domain].get("parent"),
                    "related": self.domains[domain].get("related", []),
                    "typical_entities": self.domains[domain].get("entities", [])
                }
        
        return metadata
    
    def train_ml_models(self, training_data: list[tuple[str, list[str]]]):
        """
        Train ML models with labeled data
        
        Args:
            training_data: List of (text, domains) tuples
        """
        if not self.enable_ml or not training_data:
            return
        
        try:
            # Prepare training data
            texts = [text for text, _ in training_data]
            
            # Fit vectorizer
            X = self.vectorizer.fit_transform(texts)
            
            # Train classifier for each domain
            for domain in self.domains:
                # Create binary labels
                y = [1 if domain in domains else 0 for _, domains in training_data]
                
                # Train classifier
                if domain in self.classifiers:
                    self.classifiers[domain].fit(X, y)
                    logger.info(f"Trained classifier for domain: {domain}")
            
        except Exception as e:
            logger.error(f"Failed to train ML models: {e}")
    
    def _initialize_domains(self) -> dict[str, dict[str, Any]]:
        """Initialize domain definitions"""
        return {
            "Technology": {
                "description": "Computer science, IT, software, hardware, and digital technologies",
                "parent": None,
                "related": ["Science", "Engineering"],
                "entities": ["software", "algorithm", "database", "network", "API"]
            },
            "Science": {
                "description": "Natural sciences, research, experiments, and scientific discoveries",
                "parent": None,
                "related": ["Technology", "Health", "Engineering"],
                "entities": ["research", "experiment", "hypothesis", "data", "analysis"]
            },
            "Business": {
                "description": "Commerce, management, economics, and corporate activities",
                "parent": None,
                "related": ["Finance", "Marketing"],
                "entities": ["company", "strategy", "market", "revenue", "customer"]
            },
            "Health": {
                "description": "Medicine, healthcare, wellness, and medical research",
                "parent": None,
                "related": ["Science", "Biology"],
                "entities": ["patient", "treatment", "diagnosis", "medicine", "health"]
            },
            "Education": {
                "description": "Learning, teaching, academic institutions, and pedagogy",
                "parent": None,
                "related": ["Science", "Technology"],
                "entities": ["student", "teacher", "course", "learning", "curriculum"]
            },
            "Arts": {
                "description": "Creative arts, literature, music, and cultural expressions",
                "parent": None,
                "related": ["Entertainment", "Culture"],
                "entities": ["artist", "painting", "music", "literature", "performance"]
            },
            "Engineering": {
                "description": "Applied sciences, construction, design, and technical solutions",
                "parent": "Science",
                "related": ["Technology", "Science"],
                "entities": ["design", "building", "system", "solution", "structure"]
            },
            "Finance": {
                "description": "Money, investments, banking, and financial markets",
                "parent": "Business",
                "related": ["Business", "Economics"],
                "entities": ["investment", "bank", "market", "trading", "portfolio"]
            },
            "Marketing": {
                "description": "Advertising, branding, promotion, and market research",
                "parent": "Business",
                "related": ["Business", "Psychology"],
                "entities": ["campaign", "brand", "audience", "advertising", "promotion"]
            },
            "Legal": {
                "description": "Law, regulations, legal proceedings, and jurisprudence",
                "parent": None,
                "related": ["Politics", "Business"],
                "entities": ["law", "court", "legal", "regulation", "compliance"]
            },
            "Politics": {
                "description": "Government, policy, elections, and political systems",
                "parent": None,
                "related": ["Legal", "Economics"],
                "entities": ["government", "policy", "election", "politician", "legislation"]
            },
            "Sports": {
                "description": "Athletics, competitions, fitness, and recreational activities",
                "parent": None,
                "related": ["Health", "Entertainment"],
                "entities": ["team", "player", "game", "competition", "training"]
            },
            "Entertainment": {
                "description": "Media, games, performances, and leisure activities",
                "parent": None,
                "related": ["Arts", "Sports"],
                "entities": ["movie", "show", "game", "entertainment", "media"]
            },
            "Philosophy": {
                "description": "Philosophical thought, ethics, logic, and existential questions",
                "parent": None,
                "related": ["Psychology", "Religion"],
                "entities": ["philosophy", "ethics", "morality", "logic", "existence"]
            },
            "Psychology": {
                "description": "Mind, behavior, mental processes, and human psychology",
                "parent": "Science",
                "related": ["Health", "Philosophy"],
                "entities": ["mind", "behavior", "emotion", "cognitive", "therapy"]
            }
        }
    
    def _initialize_domain_keywords(self) -> dict[str, list[dict[str, Any]]]:
        """Initialize domain-specific keywords"""
        return {
            "Technology": [
                {"term": "software", "weight": 1.5},
                {"term": "programming", "weight": 1.5},
                {"term": "algorithm", "weight": 1.3},
                {"term": "database", "weight": 1.2},
                {"term": "api", "weight": 1.2},
                {"term": "cloud", "weight": 1.1},
                {"term": "machine learning", "weight": 1.4},
                {"term": "artificial intelligence", "weight": 1.4},
                {"term": "cybersecurity", "weight": 1.3},
                {"term": "network", "weight": 1.0},
                {"term": "framework", "weight": 1.0},
                {"term": "development", "weight": 0.8}
            ],
            "Science": [
                {"term": "research", "weight": 1.5},
                {"term": "experiment", "weight": 1.4},
                {"term": "hypothesis", "weight": 1.3},
                {"term": "scientific", "weight": 1.2},
                {"term": "theory", "weight": 1.1},
                {"term": "discovery", "weight": 1.2},
                {"term": "analysis", "weight": 1.0},
                {"term": "data", "weight": 0.8},
                {"term": "observation", "weight": 1.1},
                {"term": "methodology", "weight": 1.2}
            ],
            "Business": [
                {"term": "business", "weight": 1.5},
                {"term": "company", "weight": 1.3},
                {"term": "strategy", "weight": 1.4},
                {"term": "market", "weight": 1.2},
                {"term": "revenue", "weight": 1.3},
                {"term": "customer", "weight": 1.1},
                {"term": "profit", "weight": 1.2},
                {"term": "management", "weight": 1.1},
                {"term": "enterprise", "weight": 1.2},
                {"term": "stakeholder", "weight": 1.1}
            ],
            "Health": [
                {"term": "health", "weight": 1.5},
                {"term": "medical", "weight": 1.4},
                {"term": "patient", "weight": 1.3},
                {"term": "treatment", "weight": 1.3},
                {"term": "diagnosis", "weight": 1.3},
                {"term": "doctor", "weight": 1.2},
                {"term": "medicine", "weight": 1.2},
                {"term": "clinical", "weight": 1.2},
                {"term": "therapy", "weight": 1.1},
                {"term": "healthcare", "weight": 1.3}
            ],
            "Education": [
                {"term": "education", "weight": 1.5},
                {"term": "learning", "weight": 1.4},
                {"term": "student", "weight": 1.3},
                {"term": "teacher", "weight": 1.3},
                {"term": "curriculum", "weight": 1.3},
                {"term": "course", "weight": 1.2},
                {"term": "academic", "weight": 1.2},
                {"term": "university", "weight": 1.1},
                {"term": "teaching", "weight": 1.2},
                {"term": "knowledge", "weight": 0.9}
            ]
        }
    
    def _initialize_domain_patterns(self) -> dict[str, list[dict[str, Any]]]:
        """Initialize domain-specific patterns"""
        return {
            "Technology": [
                {"pattern": r"\b(?:def|class|function|import|require)\s+\w+", "weight": 2.0},
                {"pattern": r"\b(?:API|SDK|REST|HTTP)\b", "weight": 1.5},
                {"pattern": r"\b\w+\(\s*\)", "weight": 1.2},
                {"pattern": r"(?:github\.com|stackoverflow\.com)", "weight": 1.5}
            ],
            "Science": [
                {"pattern": r"\b(?:p\s*[<>]\s*0\.\d+)", "weight": 2.0},
                {"pattern": r"\b(?:n\s*=\s*\d+)", "weight": 1.5},
                {"pattern": r"(?:et al\.|peer.review)", "weight": 1.8},
                {"pattern": r"\b(?:doi:|DOI:)", "weight": 2.0}
            ],
            "Business": [
                {"pattern": r"\$\d+(?:,\d{3})*(?:\.\d{2})?", "weight": 1.5},
                {"pattern": r"\b\d+%\s+(?:growth|increase|decrease)", "weight": 1.4},
                {"pattern": r"\bQ[1-4]\s+\d{4}", "weight": 1.3},
                {"pattern": r"\b(?:ROI|KPI|B2B|B2C)\b", "weight": 1.6}
            ],
            "Legal": [
                {"pattern": r"\b(?:v\.|vs\.)\s+", "weight": 2.0},
                {"pattern": r"§\s*\d+", "weight": 1.8},
                {"pattern": r"\b(?:plaintiff|defendant|court)\b", "weight": 1.6},
                {"pattern": r"\b(?:pursuant to|whereas|hereby)\b", "weight": 1.5}
            ]
        }
    
    def _initialize_domain_hierarchy(self) -> dict[str, list[str]]:
        """Initialize domain hierarchy"""
        hierarchy = {}
        
        for domain, info in self.domains.items():
            path = [domain]
            parent = info.get("parent")
            
            while parent:
                path.insert(0, parent)
                parent = self.domains.get(parent, {}).get("parent")
            
            hierarchy[domain] = path
        
        return hierarchy
    
    def get_domain_statistics(self, classifications: list[dict[str, Any]]) -> dict[str, Any]:
        """Get statistics about domain classifications"""
        if not classifications:
            return {
                "total_documents": 0,
                "domain_distribution": {},
                "avg_confidence": 0,
                "multi_domain_ratio": 0
            }
        
        # Count domain occurrences
        domain_counts = Counter()
        confidence_scores = []
        multi_domain_count = 0
        
        for classification in classifications:
            domains = classification.get("domains", [])
            scores = classification.get("confidence_scores", {})
            
            if len(domains) > 1:
                multi_domain_count += 1
            
            for domain in domains:
                domain_counts[domain] += 1
                if domain in scores:
                    confidence_scores.append(scores[domain])
        
        return {
            "total_documents": len(classifications),
            "domain_distribution": dict(domain_counts),
            "avg_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            "multi_domain_ratio": multi_domain_count / len(classifications) if classifications else 0,
            "top_domains": domain_counts.most_common(5)
        }