"""
Preprocessing pipeline for content preparation and normalization
"""

import hashlib
import logging
import re
import unicodedata
from typing import Any

try:
    import ftfy
    FTFY_AVAILABLE = True
except ImportError:
    FTFY_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

logger = logging.getLogger(__name__)


class ContentPreprocessor:
    """Preprocess content for ingestion pipeline"""

    def __init__(self,
                 fix_encoding: bool = True,
                 remove_html: bool = True,
                 normalize_whitespace: bool = True,
                 expand_contractions: bool = True,
                 remove_urls: bool = False,
                 remove_emails: bool = False,
                 max_length: int | None = None):
        """
        Initialize preprocessor

        Args:
            fix_encoding: Fix text encoding issues
            remove_html: Remove HTML tags
            normalize_whitespace: Normalize whitespace
            expand_contractions: Expand contractions (e.g., don't -> do not)
            remove_urls: Remove URLs from text
            remove_emails: Remove email addresses
            max_length: Maximum text length (truncate if longer)
        """
        self.fix_encoding = fix_encoding and FTFY_AVAILABLE
        self.remove_html = remove_html and BS4_AVAILABLE
        self.normalize_whitespace = normalize_whitespace
        self.expand_contractions = expand_contractions
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.max_length = max_length

        # Initialize contraction map
        self.contractions = self._initialize_contractions()

        # Initialize normalization patterns
        self.normalization_patterns = self._initialize_normalization_patterns()

    def preprocess(self, text: str, metadata: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        """
        Preprocess text with all configured steps

        Args:
            text: Input text
            metadata: Optional metadata to update

        Returns:
            Tuple of preprocessed text and preprocessing metadata
        """
        original_text = text
        preprocessing_stats = {
            "original_length": len(text),
            "steps_applied": []
        }

        # Fix encoding issues
        if self.fix_encoding:
            text = self._fix_encoding(text)
            preprocessing_stats["steps_applied"].append("fix_encoding")

        # Remove HTML
        if self.remove_html:
            text, html_removed = self._remove_html(text)
            if html_removed:
                preprocessing_stats["html_removed"] = True
                preprocessing_stats["steps_applied"].append("remove_html")

        # Normalize Unicode
        text = self._normalize_unicode(text)
        preprocessing_stats["steps_applied"].append("normalize_unicode")

        # Extract and optionally remove URLs
        urls = self._extract_urls(text)
        if urls:
            preprocessing_stats["extracted_urls"] = urls
            if self.remove_urls:
                text = self._remove_urls(text)
                preprocessing_stats["steps_applied"].append("remove_urls")

        # Extract and optionally remove emails
        emails = self._extract_emails(text)
        if emails:
            preprocessing_stats["extracted_emails"] = emails
            if self.remove_emails:
                text = self._remove_emails(text)
                preprocessing_stats["steps_applied"].append("remove_emails")

        # Expand contractions
        if self.expand_contractions:
            text = self._expand_contractions(text)
            preprocessing_stats["steps_applied"].append("expand_contractions")

        # Normalize whitespace
        if self.normalize_whitespace:
            text = self._normalize_whitespace(text)
            preprocessing_stats["steps_applied"].append("normalize_whitespace")

        # Apply additional normalizations
        text = self._apply_normalizations(text)

        # Truncate if needed
        if self.max_length and len(text) > self.max_length:
            text = self._smart_truncate(text, self.max_length)
            preprocessing_stats["truncated"] = True
            preprocessing_stats["steps_applied"].append("truncate")

        # Calculate final stats
        preprocessing_stats["final_length"] = len(text)
        preprocessing_stats["length_reduction"] = len(original_text) - len(text)
        preprocessing_stats["content_hash"] = self._generate_content_hash(text)

        # Update metadata if provided
        if metadata is None:
            metadata = {}

        metadata["preprocessing"] = preprocessing_stats

        return text, metadata

    def _fix_encoding(self, text: str) -> str:
        """Fix common encoding issues"""
        if not FTFY_AVAILABLE:
            return text

        try:
            return ftfy.fix_text(text)
        except Exception as e:
            logger.warning(f"Failed to fix encoding: {e}")
            return text

    def _remove_html(self, text: str) -> tuple[str, bool]:
        """Remove HTML tags and extract text"""
        if not BS4_AVAILABLE:
            # Fallback to regex
            cleaned = re.sub(r'<[^>]+>', ' ', text)
            return cleaned, cleaned != text

        try:
            # Check if text contains HTML
            if not re.search(r'<[^>]+>', text):
                return text, False

            soup = BeautifulSoup(text, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text
            cleaned = soup.get_text()

            # Break into lines and remove leading/trailing space
            lines = (line.strip() for line in cleaned.splitlines())

            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))

            # Drop blank lines
            cleaned = ' '.join(chunk for chunk in chunks if chunk)

            return cleaned, True

        except Exception as e:
            logger.warning(f"Failed to parse HTML: {e}")
            # Fallback to regex
            cleaned = re.sub(r'<[^>]+>', ' ', text)
            return cleaned, cleaned != text

    def _normalize_unicode(self, text: str) -> str:
        """Normalize Unicode characters"""
        # Normalize to NFC form
        text = unicodedata.normalize('NFC', text)

        # Replace special quotes and dashes
        replacements = {
            '"': '"',
            ''': "'",
            ''': "'",
            '–': '-',
            '—': '-',
            '…': '...',
            '\u200b': '',  # Zero-width space
            '\xa0': ' ',   # Non-breaking space
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text

    def _extract_urls(self, text: str) -> list[str]:
        """Extract URLs from text"""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        return list(set(urls))  # Remove duplicates

    def _remove_urls(self, text: str) -> str:
        """Remove URLs from text"""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return re.sub(url_pattern, ' ', text)

    def _extract_emails(self, text: str) -> list[str]:
        """Extract email addresses from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return list(set(emails))  # Remove duplicates

    def _remove_emails(self, text: str) -> str:
        """Remove email addresses from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.sub(email_pattern, ' ', text)

    def _expand_contractions(self, text: str) -> str:
        """Expand contractions in text"""
        for contraction, expansion in self.contractions.items():
            # Case-insensitive replacement
            pattern = re.compile(re.escape(contraction), re.IGNORECASE)
            text = pattern.sub(expansion, text)

        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text"""
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)

        # Replace multiple newlines with double newline
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    def _apply_normalizations(self, text: str) -> str:
        """Apply additional text normalizations"""
        for pattern_info in self.normalization_patterns:
            pattern = pattern_info["pattern"]
            replacement = pattern_info["replacement"]
            text = re.sub(pattern, replacement, text)

        return text

    def _smart_truncate(self, text: str, max_length: int) -> str:
        """Truncate text intelligently at sentence boundary"""
        if len(text) <= max_length:
            return text

        # Try to truncate at sentence boundary
        truncated = text[:max_length]

        # Find last sentence ending
        sentence_ends = ['.', '!', '?', '\n']
        last_end = -1

        for end in sentence_ends:
            pos = truncated.rfind(end)
            if pos > last_end:
                last_end = pos

        if last_end > max_length * 0.8:  # If we found a good ending
            return text[:last_end + 1].strip()

        # Otherwise, truncate at word boundary
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:
            return text[:last_space].strip() + '...'

        # Last resort: hard truncate
        return text[:max_length - 3].strip() + '...'

    def _generate_content_hash(self, text: str) -> str:
        """Generate hash of content for deduplication"""
        return hashlib.md5(text.encode()).hexdigest()

    def _initialize_contractions(self) -> dict[str, str]:
        """Initialize contraction mappings"""
        return {
            "don't": "do not",
            "won't": "will not",
            "can't": "cannot",
            "n't": " not",
            "'re": " are",
            "'ve": " have",
            "'ll": " will",
            "'d": " would",
            "'m": " am",
            "it's": "it is",
            "he's": "he is",
            "she's": "she is",
            "that's": "that is",
            "what's": "what is",
            "where's": "where is",
            "who's": "who is",
            "how's": "how is",
            "let's": "let us",
            "there's": "there is",
            "here's": "here is",
        }

    def _initialize_normalization_patterns(self) -> list[dict[str, str]]:
        """Initialize text normalization patterns"""
        return [
            # Remove extra punctuation
            {"pattern": r'([.!?])\1+', "replacement": r'\1'},

            # Normalize ellipsis
            {"pattern": r'\.{2,}', "replacement": '...'},

            # Remove hashtags (optional)
            # {"pattern": r'#\w+', "replacement": ''},

            # Normalize numbers with commas
            {"pattern": r'(\d),(\d{3})', "replacement": r'\1\2'},

            # Fix spacing around punctuation
            {"pattern": r'\s+([.,!?;:])', "replacement": r'\1'},
            {"pattern": r'([.,!?;:])\s*([.,!?;:])', "replacement": r'\1\2'},

            # Remove control characters
            {"pattern": r'[\x00-\x1f\x7f-\x9f]', "replacement": ''},
        ]

    def validate_content(self, text: str) -> dict[str, Any]:
        """Validate content before processing"""
        validation_result = {
            "is_valid": True,
            "warnings": [],
            "errors": []
        }

        # Check if text is empty
        if not text or not text.strip():
            validation_result["is_valid"] = False
            validation_result["errors"].append("Content is empty")
            return validation_result

        # Check minimum length
        if len(text.strip()) < 10:
            validation_result["warnings"].append("Content is very short")

        # Check if text is mostly numbers
        digit_ratio = sum(c.isdigit() for c in text) / len(text)
        if digit_ratio > 0.8:
            validation_result["warnings"].append("Content is mostly numeric")

        # Check if text is mostly special characters
        special_ratio = sum(not c.isalnum() and not c.isspace() for c in text) / len(text)
        if special_ratio > 0.5:
            validation_result["warnings"].append("Content has high ratio of special characters")

        # Check for potential encoding issues
        try:
            text.encode('utf-8')
        except UnicodeEncodeError:
            validation_result["warnings"].append("Content may have encoding issues")

        # Check for binary content
        if '\x00' in text or '\xff' in text:
            validation_result["is_valid"] = False
            validation_result["errors"].append("Content appears to be binary")

        # Check content diversity
        unique_chars = len(set(text))
        if unique_chars < 10:
            validation_result["warnings"].append("Content has very low character diversity")

        return validation_result

    def detect_language(self, text: str) -> str:
        """Simple language detection based on common patterns"""
        # This is a very basic implementation
        # In production, use a proper language detection library

        # Check for common English words
        english_words = ["the", "is", "and", "to", "of", "in", "for", "with"]
        english_count = sum(1 for word in english_words if f" {word} " in text.lower())

        if english_count >= 3:
            return "en"

        # Check for other language indicators
        if re.search(r'[à-ÿÀ-Ÿ]', text):  # French/Spanish/etc
            return "european"

        if re.search(r'[\u4e00-\u9fff]', text):  # Chinese
            return "zh"

        if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):  # Japanese
            return "ja"

        if re.search(r'[\u0400-\u04ff]', text):  # Cyrillic
            return "cyrillic"

        return "unknown"

    def segment_content(self, text: str, segment_type: str = "sentence") -> list[str]:
        """Segment content into smaller units"""
        if segment_type == "sentence":
            # Simple sentence segmentation
            sentences = re.split(r'(?<=[.!?])\s+', text)
            return [s.strip() for s in sentences if s.strip()]

        elif segment_type == "paragraph":
            # Split by double newlines
            paragraphs = re.split(r'\n\s*\n', text)
            return [p.strip() for p in paragraphs if p.strip()]

        elif segment_type == "line":
            # Split by single newlines
            lines = text.split('\n')
            return [l.strip() for l in lines if l.strip()]

        else:
            raise ValueError(f"Unknown segment type: {segment_type}")

    def get_preprocessing_statistics(self, original_text: str, processed_text: str) -> dict[str, Any]:
        """Get detailed statistics about preprocessing"""
        return {
            "original_length": len(original_text),
            "processed_length": len(processed_text),
            "length_reduction": len(original_text) - len(processed_text),
            "reduction_percentage": (1 - len(processed_text) / len(original_text)) * 100 if original_text else 0,
            "original_lines": len(original_text.splitlines()),
            "processed_lines": len(processed_text.splitlines()),
            "original_words": len(original_text.split()),
            "processed_words": len(processed_text.split()),
            "original_unique_words": len(set(original_text.lower().split())),
            "processed_unique_words": len(set(processed_text.lower().split())),
            "avg_word_length": sum(len(w) for w in processed_text.split()) / len(processed_text.split()) if processed_text.split() else 0,
            "detected_language": self.detect_language(processed_text)
        }
