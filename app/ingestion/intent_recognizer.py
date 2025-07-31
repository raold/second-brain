"""
Intent recognition component for understanding user intent in content
"""

from app.utils.logging_config import get_logger
logger = get_logger(__name__)


class IntentRecognizer:
    """Recognize user intent from text content"""

    def __init__(self, enable_sentiment: bool = True):
        """
        Initialize intent recognizer

        Args:
            enable_sentiment: Whether to perform sentiment analysis
        """
        self.enable_sentiment = enable_sentiment and TEXTBLOB_AVAILABLE
        self.nlp = None

        # Initialize intent patterns
        self.intent_patterns = self._initialize_intent_patterns()

        # Initialize action item patterns
        self.action_patterns = self._initialize_action_patterns()

        # Initialize urgency indicators
        self.urgency_indicators = self._initialize_urgency_indicators()

        # Initialize transformer model for better intent classification
        self.transformer_model = None
        self.use_transformer = False

        if SPACY_AVAILABLE:
            try:
                # Try to load transformer model first
                try:
                    self.nlp = spacy.load("en_core_web_trf")
                    self.use_transformer = True
                    logger.info("Loaded SpaCy transformer model for intent recognition")
                except OSError:
                    # Fall back to large model
                    try:
                        self.nlp = spacy.load("en_core_web_lg")
                        logger.info("Loaded SpaCy large model for intent recognition")
                    except OSError:
                        # Fall back to small model
                        self.nlp = spacy.load("en_core_web_sm")
                        logger.info("Loaded SpaCy small model for intent recognition")
            except Exception as e:
                logger.warning(f"Failed to load SpaCy model: {e}")

        # Try to load transformer-based classifier
        try:
            from transformers import pipeline
            self.transformer_classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=-1  # CPU, set to 0 for GPU
            )
            self.intent_labels = [intent.value for intent in IntentType]
            logger.info("Loaded transformer classifier for intent recognition")
        except Exception as e:
            logger.warning(f"Failed to load transformer classifier: {e}")
            self.transformer_classifier = None

    def recognize_intent(self, text: str) -> Intent | None:
        """
        Recognize the primary intent from text

        Args:
            text: Input text

        Returns:
            Recognized intent or None
        """
        # Detect intent type
        intent_type, confidence = self._detect_intent_type(text)

        if not intent_type:
            # Default to statement if no clear intent
            intent_type = IntentType.STATEMENT
            confidence = 0.5

        # Extract action items
        action_items = self._extract_action_items(text)

        # Calculate urgency
        urgency = self._calculate_urgency(text)

        # Analyze sentiment
        sentiment = None
        if self.enable_sentiment:
            sentiment = self._analyze_sentiment(text)

        return Intent(
            type=intent_type,
            confidence=confidence,
            action_items=action_items,
            urgency=urgency,
            sentiment=sentiment
        )

    def _detect_intent_type(self, text: str) -> tuple[IntentType | None, float]:
        """Detect the primary intent type from text"""
        text_lower = text.lower().strip()

        # Use transformer classifier if available
        if self.transformer_classifier:
            try:
                result = self.transformer_classifier(
                    text[:512],  # Limit text length
                    candidate_labels=self.intent_labels,
                    multi_label=False
                )

                # Get top prediction
                top_label = result["labels"][0]
                top_score = result["scores"][0]

                # Map to IntentType
                for intent_type in IntentType:
                    if intent_type.value == top_label:
                        # Combine with pattern matching for better accuracy
                        pattern_intent, pattern_conf = self._detect_intent_pattern_based(text_lower)
                        if pattern_intent == intent_type:
                            # Boost confidence when both methods agree
                            return intent_type, min(0.95, top_score * 1.2)
                        else:
                            # Average when they disagree
                            return intent_type, top_score * 0.8

            except Exception as e:
                logger.debug(f"Transformer classification failed: {e}")

        # Fall back to pattern-based detection
        return self._detect_intent_pattern_based(text_lower)

    def _detect_intent_pattern_based(self, text_lower: str) -> tuple[IntentType | None, float]:
        """Pattern-based intent detection (original method)"""
        # Track scores for each intent type
        intent_scores = defaultdict(float)

        # Pattern matching
        for intent_type, patterns in self.intent_patterns.items():
            for pattern_info in patterns:
                pattern = pattern_info["pattern"]
                weight = pattern_info.get("weight", 1.0)

                if pattern_info.get("is_regex", True):
                    matches = re.findall(pattern, text_lower)
                    if matches:
                        intent_scores[intent_type] += len(matches) * weight
                else:
                    # Simple string matching
                    if pattern in text_lower:
                        intent_scores[intent_type] += weight

        # Analyze sentence structure if SpaCy available
        if self.nlp:
            structure_intent, structure_confidence = self._analyze_sentence_structure(text_lower)
            if structure_intent:
                intent_scores[structure_intent] += structure_confidence * 2

        # Special checks
        if text_lower.strip().endswith("?"):
            intent_scores[IntentType.QUESTION] += 2.0

        if any(text_lower.strip().startswith(prefix.lower()) for prefix in ["TODO:", "FIXME:", "NOTE:"]):
            intent_scores[IntentType.TODO] += 3.0

        # Find highest scoring intent
        if not intent_scores:
            return None, 0.0

        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        intent_type = best_intent[0]

        # Calculate confidence based on score and uniqueness
        max_score = best_intent[1]
        total_score = sum(intent_scores.values())

        # Confidence is higher when one intent dominates
        if total_score > 0:
            confidence = min(0.95, (max_score / total_score) * (max_score / 5))
        else:
            confidence = 0.5

        return intent_type, confidence

    def _analyze_sentence_structure(self, text: str) -> tuple[IntentType | None, float]:
        """Analyze sentence structure using SpaCy"""
        try:
            doc = self.nlp(text[:1000])  # Limit text length

            # Analyze each sentence
            sentence_intents = []

            for sent in doc.sents:
                # Check for question structure
                if any(token.tag_ in ["WDT", "WP", "WP$", "WRB"] for token in sent):
                    sentence_intents.append((IntentType.QUESTION, 0.8))

                # Check for imperative (command) structure
                if sent[0].pos_ == "VERB" and sent[0].dep_ == "ROOT":
                    sentence_intents.append((IntentType.TODO, 0.7))

                # Check for modal verbs (planning, decision)
                modal_verbs = [token for token in sent if token.tag_ == "MD"]
                if modal_verbs:
                    if any(modal.text.lower() in ["should", "must", "need"] for modal in modal_verbs):
                        sentence_intents.append((IntentType.DECISION, 0.6))
                    elif any(modal.text.lower() in ["will", "would", "might"] for modal in modal_verbs):
                        sentence_intents.append((IntentType.PLANNING, 0.6))

            # Return most common intent
            if sentence_intents:
                # Count occurrences
                intent_counts = defaultdict(float)
                for intent, conf in sentence_intents:
                    intent_counts[intent] += conf

                best_intent = max(intent_counts.items(), key=lambda x: x[1])
                avg_confidence = best_intent[1] / len(sentence_intents)
                return best_intent[0], avg_confidence

        except Exception as e:
            logger.debug(f"Error in sentence structure analysis: {e}")

        return None, 0.0

    def _extract_action_items(self, text: str) -> list[str]:
        """Extract action items from text"""
        action_items = []

        # Split into sentences
        sentences = re.split(r'[.!?]+', text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check against action patterns
            is_action = False
            for pattern in self.action_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    is_action = True
                    break

            if is_action:
                # Clean up the action item
                action = sentence

                # Remove common prefixes
                for prefix in ["TODO:", "FIXME:", "ACTION:", "TASK:", "- ", "* ", "• "]:
                    if action.upper().startswith(prefix.upper()):
                        action = action[len(prefix):].strip()
                        break

                # Add to list if not too long
                if len(action) < 200:
                    action_items.append(action)

        # Also check for bulleted/numbered lists
        list_items = re.findall(r'(?:^|\n)\s*[-*•]\s*(.+)', text)
        for item in list_items:
            item = item.strip()
            if len(item) < 200 and item not in action_items:
                # Check if it looks like an action
                if any(word in item.lower() for word in ["need", "should", "must", "will", "todo"]):
                    action_items.append(item)

        # Deduplicate while preserving order
        seen = set()
        unique_items = []
        for item in action_items:
            if item.lower() not in seen:
                seen.add(item.lower())
                unique_items.append(item)

        return unique_items[:10]  # Limit to 10 action items

    def _calculate_urgency(self, text: str) -> float:
        """Calculate urgency score from text"""
        text_lower = text.lower()
        urgency_score = 0.5  # Default neutral urgency

        # Check for urgency indicators
        for indicator, weight in self.urgency_indicators["high"].items():
            if indicator in text_lower:
                urgency_score += weight

        for indicator, weight in self.urgency_indicators["low"].items():
            if indicator in text_lower:
                urgency_score -= weight

        # Check for deadline mentions
        deadline_patterns = [
            r'\b(?:by|before|until)\s+(?:tomorrow|today|tonight|end of day|eod|cob)\b',
            r'\bdeadline\s*:?\s*\d',
            r'\bdue\s+(?:date|by|on)\b',
            r'\b\d+\s*(?:hours?|days?|weeks?)\s+(?:left|remaining)\b'
        ]

        for pattern in deadline_patterns:
            if re.search(pattern, text_lower):
                urgency_score += 0.2

        # Check for priority mentions
        if re.search(r'\b(?:high|highest|critical)\s+priority\b', text_lower):
            urgency_score += 0.3
        elif re.search(r'\blow\s+priority\b', text_lower):
            urgency_score -= 0.2

        # Normalize to 0-1 range
        return max(0.0, min(1.0, urgency_score))

    def _analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of text"""
        if not TEXTBLOB_AVAILABLE:
            return 0.0

        try:
            blob = TextBlob(text)
            # TextBlob returns polarity in range [-1, 1]
            return float(blob.sentiment.polarity)
        except Exception as e:
            logger.debug(f"Error in sentiment analysis: {e}")
            return 0.0

    def _initialize_intent_patterns(self) -> dict[IntentType, list[dict[str, Any]]]:
        """Initialize patterns for intent detection"""
        return {
            IntentType.QUESTION: [
                {"pattern": r'\b(?:what|when|where|who|why|how|which|whose)\b', "weight": 1.5},
                {"pattern": r'\b(?:can|could|would|should|is|are|does|do|did)\s+\w+\s*\?', "weight": 2.0},
                {"pattern": r'\b(?:explain|describe|define|clarify)\b', "weight": 1.2},
                {"pattern": r'\?$', "weight": 2.5, "is_regex": False},
            ],
            IntentType.TODO: [
                {"pattern": r'\b(?:todo|task|action|need to|must|should)\b', "weight": 1.5},
                {"pattern": r'\b(?:complete|finish|implement|create|build|fix)\b', "weight": 1.2},
                {"pattern": r'^(?:todo|fixme|task|action)\s*:', "weight": 3.0},
                {"pattern": r'\b(?:remember to|don\'t forget to|make sure to)\b', "weight": 1.8},
            ],
            IntentType.IDEA: [
                {"pattern": r'\b(?:idea|thought|concept|proposal|suggestion)\b', "weight": 1.5},
                {"pattern": r'\b(?:what if|how about|consider|imagine|suppose)\b', "weight": 1.3},
                {"pattern": r'\b(?:could|might|maybe|perhaps|possibly)\b', "weight": 0.8},
                {"pattern": r'^(?:idea|thought|proposal)\s*:', "weight": 2.5},
            ],
            IntentType.DECISION: [
                {"pattern": r'\b(?:decide|decision|choose|choice|option)\b', "weight": 1.8},
                {"pattern": r'\b(?:pros and cons|trade-?off|versus|vs\.?)\b', "weight": 1.5},
                {"pattern": r'\b(?:conclude|determined|resolved|agreed)\b', "weight": 1.4},
                {"pattern": r'\b(?:will|going to|plan to)\b', "weight": 1.0},
            ],
            IntentType.LEARNING: [
                {"pattern": r'\b(?:learn|study|understand|research|explore)\b', "weight": 1.5},
                {"pattern": r'\b(?:tutorial|guide|documentation|course|lesson)\b', "weight": 1.3},
                {"pattern": r'\b(?:how to|tips|tricks|best practice)\b', "weight": 1.4},
                {"pattern": r'\b(?:discovered|found out|realized|understood)\b', "weight": 1.2},
            ],
            IntentType.REFERENCE: [
                {"pattern": r'\b(?:reference|link|url|source|citation)\b', "weight": 1.5},
                {"pattern": r'https?://', "weight": 2.0},
                {"pattern": r'\b(?:see|refer to|check|look at)\b', "weight": 1.0},
                {"pattern": r'\b(?:documentation|docs|manual|spec)\b', "weight": 1.2},
            ],
            IntentType.REFLECTION: [
                {"pattern": r'\b(?:reflect|think|thought|consider|ponder)\b', "weight": 1.3},
                {"pattern": r'\b(?:feel|felt|believe|opinion|perspective)\b', "weight": 1.2},
                {"pattern": r'\b(?:retrospective|review|assessment|evaluation)\b', "weight": 1.5},
                {"pattern": r'\b(?:lesson learned|takeaway|insight)\b', "weight": 1.4},
            ],
            IntentType.PLANNING: [
                {"pattern": r'\b(?:plan|planning|schedule|timeline|roadmap)\b', "weight": 1.8},
                {"pattern": r'\b(?:milestone|deadline|target|goal|objective)\b', "weight": 1.5},
                {"pattern": r'\b(?:next steps|action plan|strategy)\b', "weight": 1.6},
                {"pattern": r'\b(?:will|going to|intend to|aim to)\b', "weight": 1.0},
            ],
            IntentType.PROBLEM: [
                {"pattern": r'\b(?:problem|issue|bug|error|failure)\b', "weight": 1.8},
                {"pattern": r'\b(?:broken|failed|not working|doesn\'t work)\b', "weight": 1.6},
                {"pattern": r'\b(?:challenge|obstacle|difficulty|blocker)\b', "weight": 1.4},
                {"pattern": r'\b(?:help|stuck|confused|unsure)\b', "weight": 1.2},
            ],
            IntentType.SOLUTION: [
                {"pattern": r'\b(?:solution|solve|fix|resolve|workaround)\b', "weight": 1.8},
                {"pattern": r'\b(?:answer|approach|method|technique)\b', "weight": 1.3},
                {"pattern": r'\b(?:works|working|fixed|resolved)\b', "weight": 1.4},
                {"pattern": r'\b(?:recommendation|suggest|advise)\b', "weight": 1.2},
            ],
        }

    def _initialize_action_patterns(self) -> list[str]:
        """Initialize patterns for action item detection"""
        return [
            r'\b(?:todo|task|action|fixme)\s*:',
            r'\b(?:need to|must|should|have to|required to)\b',
            r'\b(?:don\'t forget to|remember to|make sure to)\b',
            r'\b(?:complete|finish|implement|create|build|fix|update|review)\b',
            r'^[-*•]\s*(?:need|must|should|will)',
            r'\b(?:action item|next step|follow up)\b',
            r'\b(?:assign|assigned to|responsible for)\b',
        ]

    def _initialize_urgency_indicators(self) -> dict[str, dict[str, float]]:
        """Initialize urgency indicators and their weights"""
        return {
            "high": {
                "urgent": 0.3,
                "asap": 0.3,
                "immediately": 0.3,
                "critical": 0.25,
                "emergency": 0.3,
                "today": 0.2,
                "now": 0.2,
                "right away": 0.25,
                "time sensitive": 0.25,
                "high priority": 0.2,
                "deadline": 0.15,
                "overdue": 0.25,
            },
            "low": {
                "whenever": 0.2,
                "no rush": 0.25,
                "low priority": 0.2,
                "someday": 0.15,
                "eventually": 0.15,
                "when you can": 0.2,
                "not urgent": 0.25,
                "back burner": 0.2,
            }
        }

    def get_intent_statistics(self, intents: list[Intent]) -> dict[str, Any]:
        """Get statistics about recognized intents"""
        if not intents:
            return {
                "total_intents": 0,
                "intent_distribution": {},
                "avg_confidence": 0,
                "avg_urgency": 0,
                "total_action_items": 0,
                "sentiment_stats": {}
            }

        # Intent type distribution
        type_counts = defaultdict(int)
        for intent in intents:
            type_counts[intent.type.value] += 1

        # Calculate averages
        avg_confidence = sum(i.confidence for i in intents) / len(intents)

        urgencies = [i.urgency for i in intents if i.urgency is not None]
        avg_urgency = sum(urgencies) / len(urgencies) if urgencies else 0

        # Action items
        total_actions = sum(len(i.action_items) for i in intents)

        # Sentiment statistics
        sentiments = [i.sentiment for i in intents if i.sentiment is not None]
        sentiment_stats = {}
        if sentiments:
            sentiment_stats = {
                "avg_sentiment": sum(sentiments) / len(sentiments),
                "positive": len([s for s in sentiments if s > 0.1]),
                "negative": len([s for s in sentiments if s < -0.1]),
                "neutral": len([s for s in sentiments if -0.1 <= s <= 0.1]),
            }

        return {
            "total_intents": len(intents),
            "intent_distribution": dict(type_counts),
            "avg_confidence": avg_confidence,
            "avg_urgency": avg_urgency,
            "total_action_items": total_actions,
            "sentiment_stats": sentiment_stats
        }
