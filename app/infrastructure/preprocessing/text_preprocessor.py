"""
Text preprocessing utilities for NLP pipelines
"""

import logging
import re
import unicodedata
from typing import Any, Optional

from app.infrastructure.preprocessing.pipeline import (
    PipelineBuilder,
    PipelineContext,
    PipelineStep,
    PreprocessingStage,
)

logger = logging.getLogger(__name__)


class TextNormalizationStep(PipelineStep[str, str]):
    """Advanced text normalization"""
    
    def __init__(
        self,
        lowercase: bool = True,
        remove_accents: bool = True,
        expand_contractions: bool = True,
        remove_urls: bool = True,
        remove_emails: bool = True,
        remove_phone_numbers: bool = True,
        remove_numbers: bool = False,
        remove_punctuation: bool = False,
        name: str = "text_normalization"
    ):
        super().__init__(name=name, stage=PreprocessingStage.NORMALIZATION)
        self.lowercase = lowercase
        self.remove_accents = remove_accents
        self.expand_contractions = expand_contractions
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.remove_phone_numbers = remove_phone_numbers
        self.remove_numbers = remove_numbers
        self.remove_punctuation = remove_punctuation
        
        # Contraction mapping
        self.contractions = {
            "ain't": "is not",
            "aren't": "are not",
            "can't": "cannot",
            "couldn't": "could not",
            "didn't": "did not",
            "doesn't": "does not",
            "don't": "do not",
            "hadn't": "had not",
            "hasn't": "has not",
            "haven't": "have not",
            "he'd": "he would",
            "he'll": "he will",
            "he's": "he is",
            "i'd": "i would",
            "i'll": "i will",
            "i'm": "i am",
            "i've": "i have",
            "isn't": "is not",
            "it's": "it is",
            "let's": "let us",
            "mightn't": "might not",
            "mustn't": "must not",
            "shan't": "shall not",
            "she'd": "she would",
            "she'll": "she will",
            "she's": "she is",
            "shouldn't": "should not",
            "that's": "that is",
            "there's": "there is",
            "they'd": "they would",
            "they'll": "they will",
            "they're": "they are",
            "they've": "they have",
            "we'd": "we would",
            "we're": "we are",
            "we've": "we have",
            "weren't": "were not",
            "what'll": "what will",
            "what're": "what are",
            "what's": "what is",
            "what've": "what have",
            "where's": "where is",
            "who'd": "who would",
            "who'll": "who will",
            "who're": "who are",
            "who's": "who is",
            "who've": "who have",
            "won't": "will not",
            "wouldn't": "would not",
            "you'd": "you would",
            "you'll": "you will",
            "you're": "you are",
            "you've": "you have"
        }
        
    async def process(self, data: str, context: PipelineContext) -> str:
        """Normalize text"""
        text = data
        
        # Remove URLs
        if self.remove_urls:
            text = re.sub(r'https?://\S+|www\.\S+', '', text)
            
        # Remove emails
        if self.remove_emails:
            text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
            
        # Remove phone numbers
        if self.remove_phone_numbers:
            text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '', text)
            text = re.sub(r'\(\d{3}\)\s*\d{3}[-.]?\d{4}', '', text)
            
        # Expand contractions
        if self.expand_contractions:
            for contraction, expansion in self.contractions.items():
                text = re.sub(r'\b' + contraction + r'\b', expansion, text, flags=re.IGNORECASE)
                
        # Convert to lowercase
        if self.lowercase:
            text = text.lower()
            
        # Remove accents
        if self.remove_accents:
            text = ''.join(
                c for c in unicodedata.normalize('NFD', text)
                if unicodedata.category(c) != 'Mn'
            )
            
        # Remove numbers
        if self.remove_numbers:
            text = re.sub(r'\d+', '', text)
            
        # Remove punctuation
        if self.remove_punctuation:
            text = re.sub(r'[^\w\s]', '', text)
            
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text


class TokenizationStep(PipelineStep[str, list[str]]):
    """Tokenize text into words or sentences"""
    
    def __init__(
        self,
        level: str = "word",  # "word" or "sentence"
        min_token_length: int = 1,
        max_token_length: int = 50,
        name: str = "tokenization"
    ):
        super().__init__(name=name, stage=PreprocessingStage.TRANSFORMATION)
        self.level = level
        self.min_token_length = min_token_length
        self.max_token_length = max_token_length
        
    async def process(self, data: str, context: PipelineContext) -> list[str]:
        """Tokenize text"""
        if self.level == "sentence":
            # Simple sentence tokenization
            sentences = re.split(r'[.!?]+', data)
            return [s.strip() for s in sentences if s.strip()]
        else:
            # Word tokenization
            words = data.split()
            # Filter by length
            return [
                w for w in words
                if self.min_token_length <= len(w) <= self.max_token_length
            ]


class StopwordRemovalStep(PipelineStep[list[str], list[str]]):
    """Remove stopwords from token list"""
    
    def __init__(self, stopwords: Optional[set[str]] = None, name: str = "stopword_removal"):
        super().__init__(name=name, stage=PreprocessingStage.CLEANING)
        
        # Default English stopwords
        self.stopwords = stopwords or {
            'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're",
            "you've", "you'll", "you'd", 'your', 'yours', 'yourself', 'yourselves', 'he',
            'him', 'his', 'himself', 'she', "she's", 'her', 'hers', 'herself', 'it',
            "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves',
            'what', 'which', 'who', 'whom', 'this', 'that', "that'll", 'these', 'those',
            'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if',
            'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with',
            'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off',
            'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when',
            'where', 'why', 'how', 'all', 'both', 'each', 'few', 'more', 'most', 'other',
            'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
            'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't", 'should',
            "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren',
            "aren't", 'couldn', "couldn't", 'didn', "didn't", 'doesn', "doesn't", 'hadn',
            "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn',
            "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't",
            'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won', "won't",
            'wouldn', "wouldn't"
        }
        
    async def process(self, data: list[str], context: PipelineContext) -> list[str]:
        """Remove stopwords"""
        return [token for token in data if token.lower() not in self.stopwords]


class LemmatizerStep(PipelineStep[list[str], list[str]]):
    """Lemmatize tokens (requires spaCy)"""
    
    def __init__(self, name: str = "lemmatization"):
        super().__init__(name=name, stage=PreprocessingStage.TRANSFORMATION)
        self.nlp = None
        
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
        except:
            logger.warning("spaCy not available for lemmatization")
            
    async def process(self, data: list[str], context: PipelineContext) -> list[str]:
        """Lemmatize tokens"""
        if not self.nlp:
            context.add_warning("Lemmatization skipped - spaCy not available")
            return data
            
        # Process tokens
        doc = self.nlp(" ".join(data))
        return [token.lemma_ for token in doc]


class TextChunkingStep(PipelineStep[str, list[str]]):
    """Chunk text into smaller pieces"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separator: str = " ",
        name: str = "text_chunking"
    ):
        super().__init__(name=name, stage=PreprocessingStage.TRANSFORMATION)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator
        
    async def process(self, data: str, context: PipelineContext) -> list[str]:
        """Chunk text"""
        if len(data) <= self.chunk_size:
            return [data]
            
        chunks = []
        words = data.split(self.separator)
        
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word) + len(self.separator)
            
            if current_size + word_size > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(self.separator.join(current_chunk))
                
                # Start new chunk with overlap
                if self.chunk_overlap > 0:
                    # Calculate how many words to keep for overlap
                    overlap_words = []
                    overlap_size = 0
                    
                    for w in reversed(current_chunk):
                        overlap_size += len(w) + len(self.separator)
                        if overlap_size <= self.chunk_overlap:
                            overlap_words.append(w)
                        else:
                            break
                            
                    current_chunk = list(reversed(overlap_words))
                    current_size = sum(len(w) + len(self.separator) for w in current_chunk)
                else:
                    current_chunk = []
                    current_size = 0
                    
            current_chunk.append(word)
            current_size += word_size
            
        # Add last chunk
        if current_chunk:
            chunks.append(self.separator.join(current_chunk))
            
        return chunks


class LanguageDetectionStep(PipelineStep[str, dict]):
    """Detect language of text"""
    
    def __init__(self, name: str = "language_detection"):
        super().__init__(name=name, stage=PreprocessingStage.ENRICHMENT)
        self.detector = None
        
        try:
            from langdetect import detect, detect_langs
            self.detect = detect
            self.detect_langs = detect_langs
        except ImportError:
            logger.warning("langdetect not available for language detection")
            
    async def process(self, data: str, context: PipelineContext) -> dict:
        """Detect language and add to metadata"""
        result = {"text": data}
        
        if not self.detect:
            context.add_warning("Language detection skipped - langdetect not available")
            result["language"] = "unknown"
            result["language_confidence"] = 0.0
        else:
            try:
                # Detect language
                lang = self.detect(data)
                result["language"] = lang
                
                # Get confidence scores
                langs = self.detect_langs(data)
                if langs:
                    result["language_confidence"] = langs[0].prob
                else:
                    result["language_confidence"] = 0.0
                    
            except Exception as e:
                context.add_warning(f"Language detection failed: {e}")
                result["language"] = "unknown"
                result["language_confidence"] = 0.0
                
        return result


# Pre-built text preprocessing pipelines

def create_basic_text_pipeline(name: str = "basic_text_pipeline"):
    """Create basic text preprocessing pipeline"""
    return (
        PipelineBuilder[str](name=name)
        .add_step(TextNormalizationStep(
            lowercase=True,
            remove_urls=True,
            remove_emails=True,
            expand_contractions=True
        ))
        .clean(remove_html=True, remove_extra_spaces=True)
        .build()
    )


def create_nlp_pipeline(name: str = "nlp_pipeline"):
    """Create NLP preprocessing pipeline"""
    return (
        PipelineBuilder[str](name=name)
        .add_step(TextNormalizationStep(
            lowercase=True,
            remove_urls=True,
            remove_emails=True,
            expand_contractions=True,
            remove_accents=True
        ))
        .clean(remove_html=True, remove_extra_spaces=True)
        .add_step(TokenizationStep())
        .add_step(StopwordRemovalStep())
        .add_step(LemmatizerStep())
        .build()
    )


def create_document_pipeline(
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    name: str = "document_pipeline"
):
    """Create document preprocessing pipeline"""
    return (
        PipelineBuilder[str](name=name)
        .add_step(LanguageDetectionStep())
        .transform(lambda d: d["text"])  # Extract text from dict
        .add_step(TextNormalizationStep(
            lowercase=False,  # Preserve case for documents
            remove_urls=True,
            remove_emails=True,
            expand_contractions=True
        ))
        .clean(remove_html=True, remove_extra_spaces=True)
        .add_step(TextChunkingStep(chunk_size=chunk_size, chunk_overlap=chunk_overlap))
        .build()
    )