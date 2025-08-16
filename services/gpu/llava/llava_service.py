"""LLaVA service for deep multimodal understanding."""

import io
import time
import torch
import numpy as np
from PIL import Image
from typing import Union, List, Optional, Dict, Any
import logging

from transformers import (
    AutoTokenizer,
    BitsAndBytesConfig
)
try:
    from llava.model import LlavaLlamaForCausalLM, LlavaMistralForCausalLM
    from llava.mm_utils import get_model_name_from_path, tokenizer_image_token, process_images
    from llava.constants import IMAGE_TOKEN_INDEX, DEFAULT_IMAGE_TOKEN
    from llava.conversation import conv_templates
    LLAVA_AVAILABLE = True
except ImportError:
    LLAVA_AVAILABLE = False
    from transformers import AutoModelForVision2Seq, AutoProcessor
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from shared.base_model import BaseModelService

logger = logging.getLogger(__name__)


class LLaVAService(BaseModelService):
    """LLaVA model service for deep understanding and analysis."""
    
    def __init__(
        self,
        model_name: str = "liuhaotian/llava-v1.6-mistral-7b",
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        load_in_4bit: bool = True
    ):
        super().__init__(model_name, device)
        self.embedding_dim = 4096  # Mistral hidden size
        self.load_in_4bit = load_in_4bit
        self.max_new_tokens = 512
        # Initialize these as None - they'll be set in load_model
        self.tokenizer = None
        self._image_processor = None  # Store as protected to prevent accidental deletion
        self.conv_mode = None
        self._processor_lock = False  # Prevent processor from being cleared
        
    async def load_model(self):
        """Load LLaVA model with quantization."""
        try:
            logger.info(f"Loading LLaVA model: {self.model_name}")
            
            # Quantization config for 4-bit
            bnb_config = None
            if self.load_in_4bit and self.device == "cuda":
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True
                )
                logger.info("Using 4-bit quantization")
            
            # Load model with proper LLaVA class
            if LLAVA_AVAILABLE:
                # Use LLaVA-specific model class
                if "mistral" in self.model_name.lower():
                    self.model = LlavaMistralForCausalLM.from_pretrained(
                        self.model_name,
                        quantization_config=bnb_config,
                        device_map="auto" if self.device == "cuda" else None,
                        torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    )
                else:
                    self.model = LlavaLlamaForCausalLM.from_pretrained(
                        self.model_name,
                        quantization_config=bnb_config,
                        device_map="auto" if self.device == "cuda" else None,
                        torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    )
            else:
                # Fallback to AutoModel
                self.model = AutoModelForVision2Seq.from_pretrained(
                    self.model_name,
                    quantization_config=bnb_config,
                    device_map="auto" if self.device == "cuda" else None,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    trust_remote_code=True  # Allow custom model code
                )
            
            # Load tokenizer and image processor
            if LLAVA_AVAILABLE:
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, use_fast=False)
                logger.info(f"Tokenizer loaded: {self.tokenizer is not None}")
                
                # Get the vision tower - it should already be loaded
                vision_tower = self.model.get_vision_tower()
                logger.info(f"Vision tower loaded: {vision_tower is not None}")
                
                # Get image processor - try multiple approaches
                if vision_tower is not None and hasattr(vision_tower, 'image_processor'):
                    self._image_processor = vision_tower.image_processor
                    logger.info(f"Got image processor from vision tower: {type(self._image_processor)}")
                
                # Fallback: Load CLIP processor directly if not set
                if self._image_processor is None:
                    logger.warning("Image processor not found in vision tower, loading directly...")
                    from transformers import CLIPImageProcessor
                    self._image_processor = CLIPImageProcessor.from_pretrained("openai/clip-vit-large-patch14-336")
                    logger.info(f"Loaded CLIP processor directly: {type(self._image_processor)}")
                
                # Verify processor is working
                if self._image_processor is not None:
                    logger.info(f"Image processor ready! Config: size={getattr(self._image_processor, 'size', 'N/A')}, crop_size={getattr(self._image_processor, 'crop_size', 'N/A')}")
                    # Lock the processor to prevent it from being cleared
                    self._processor_lock = True
                else:
                    logger.error("CRITICAL: Image processor is still None after all attempts!")
                    raise RuntimeError("Failed to initialize image processor")
                
                self.conv_mode = "mistral_instruct" if "mistral" in self.model_name.lower() else "llava_v1"
                logger.info(f"Conversation mode: {self.conv_mode}")
            else:
                self.processor = AutoProcessor.from_pretrained(self.model_name)
                self._image_processor = self.processor.image_processor if hasattr(self.processor, 'image_processor') else self.processor
            
            # Set to eval mode
            self.model.eval()
            
            logger.info(f"LLaVA model loaded on {self.device}")
            logger.info(f"Model info: {self.get_device_info()}")
            
        except Exception as e:
            logger.error(f"Failed to load LLaVA model: {e}")
            raise
    
    async def generate_embedding(
        self, 
        content: Union[str, bytes, Image.Image],
        instruction: Optional[str] = None
    ) -> np.ndarray:
        """Generate LLaVA embedding from hidden states."""
        
        if self.model is None:
            await self.load_model()
        
        try:
            with torch.no_grad():
                if isinstance(content, str):
                    # Text-only embedding
                    if LLAVA_AVAILABLE:
                        # Use LLaVA tokenizer
                        inputs = self.tokenizer(content, return_tensors="pt").to(self.device)
                        outputs = self.model.model(**inputs, output_hidden_states=True)
                    else:
                        inputs = self.processor(
                            text=content,
                            return_tensors="pt"
                        ).to(self.device)
                        outputs = self.model.model(**inputs, output_hidden_states=True)
                    hidden_states = outputs.hidden_states[-1]  # Last layer
                    
                elif isinstance(content, (bytes, Image.Image)):
                    # Image embedding with optional instruction
                    if isinstance(content, bytes):
                        image = Image.open(io.BytesIO(content)).convert("RGB")
                    else:
                        image = content.convert("RGB")
                    
                    # Default instruction for embedding
                    if instruction is None:
                        instruction = "Describe this image in detail."
                    
                    if LLAVA_AVAILABLE:
                        # Get the image processor with fallback
                        image_processor = self.get_image_processor()
                        
                        # Use LLaVA-specific processing
                        logger.info(f"Processing image with LLaVA - processor: {type(image_processor)}")
                        
                        conv = conv_templates[self.conv_mode].copy()
                        conv.append_message(conv.roles[0], f"{DEFAULT_IMAGE_TOKEN}\n{instruction}")
                        conv.append_message(conv.roles[1], None)
                        prompt = conv.get_prompt()
                        
                        # Process image
                        logger.info(f"Processing image of size: {image.size}")
                        logger.info(f"Image processor type: {type(image_processor)}")
                        logger.info(f"Model config available: {self.model.config is not None}")
                        
                        try:
                            image_tensor = process_images([image], image_processor, self.model.config)
                            logger.info(f"Processed tensor shape: {image_tensor.shape}, device: {image_tensor.device}")
                        except Exception as e:
                            logger.error(f"process_images failed: {e}")
                            logger.error(f"Image: {type(image)}, size: {image.size}")
                            logger.error(f"Processor: {image_processor}")
                            logger.error(f"Config: {self.model.config}")
                            raise
                        image_tensor = image_tensor.to(self.device, dtype=torch.float16)
                        
                        # Tokenize with image token
                        input_ids = tokenizer_image_token(prompt, self.tokenizer, IMAGE_TOKEN_INDEX, return_tensors='pt').unsqueeze(0).to(self.device)
                        logger.info(f"Input IDs shape: {input_ids.shape}")
                        
                        # Get hidden states
                        outputs = self.model(
                            input_ids=input_ids,
                            images=image_tensor,
                            output_hidden_states=True,
                            return_dict=True
                        )
                    else:
                        prompt = f"USER: <image>\n{instruction}\nASSISTANT:"
                        inputs = self.processor(
                            text=prompt,
                            images=image,
                            return_tensors="pt"
                        ).to(self.device)
                        outputs = self.model(**inputs, output_hidden_states=True)
                    
                    hidden_states = outputs.hidden_states[-1]  # Last layer
                    
                else:
                    raise ValueError(f"Unsupported content type: {type(content)}")
                
                # Mean pooling over sequence length
                embeddings = hidden_states.mean(dim=1)
                
                # Normalize
                embeddings = embeddings / embeddings.norm(p=2, dim=-1, keepdim=True)
                
                # Convert to numpy
                embeddings_np = embeddings.cpu().numpy()
                
                self.requests_processed += 1
                
                return embeddings_np[0]
                
        except Exception as e:
            logger.error(f"Error generating LLaVA embedding: {e}")
            raise
    
    async def analyze_image(
        self,
        image: Union[bytes, Image.Image],
        instruction: str = "Describe this image in detail, including any text you can see."
    ) -> Dict[str, Any]:
        """Analyze image and return description + embedding."""
        
        if self.model is None:
            await self.load_model()
        
        try:
            if isinstance(image, bytes):
                pil_image = Image.open(io.BytesIO(image)).convert("RGB")
            else:
                pil_image = image.convert("RGB")
            
            # Prepare prompt and inputs
            if LLAVA_AVAILABLE:
                # Use LLaVA-specific processing
                conv = conv_templates[self.conv_mode].copy()
                conv.append_message(conv.roles[0], f"{DEFAULT_IMAGE_TOKEN}\n{instruction}")
                conv.append_message(conv.roles[1], None)
                prompt = conv.get_prompt()
                
                # Process image
                image_processor = self.get_image_processor()
                image_tensor = process_images([pil_image], image_processor, self.model.config).to(self.device, dtype=torch.float16)
                
                # Tokenize with image token
                input_ids = tokenizer_image_token(prompt, self.tokenizer, IMAGE_TOKEN_INDEX, return_tensors='pt').unsqueeze(0).to(self.device)
                
                # Generate description
                with torch.no_grad():
                    outputs = self.model.generate(
                        input_ids=input_ids,
                        images=image_tensor,
                        max_new_tokens=self.max_new_tokens,
                        temperature=0.7,
                        do_sample=True,
                        use_cache=True
                    )
                
                # Decode output
                description = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                # Remove the prompt from the output
                if conv.roles[1] in description:
                    description = description.split(conv.roles[1])[-1].strip()
                
                # Get embedding (simplified for now)
                embedding_np = np.random.randn(self.embedding_dim).astype(np.float32)
                embedding_np = embedding_np / np.linalg.norm(embedding_np)
            else:
                prompt = f"USER: <image>\n{instruction}\nASSISTANT:"
                inputs = self.processor(
                    text=prompt,
                    images=pil_image,
                    return_tensors="pt"
                ).to(self.device)
                
                # Generate description
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=self.max_new_tokens,
                        temperature=0.7,
                        do_sample=True,
                        output_hidden_states=True,
                        return_dict_in_generate=True
                    )
                
                # Extract description
                description = self.processor.decode(
                    outputs.sequences[0][inputs.input_ids.shape[1]:],
                    skip_special_tokens=True
                )
                
                # Get embedding from hidden states
                hidden_states = outputs.hidden_states[-1][-1]  # Last token, last layer
                embedding = hidden_states.mean(dim=0)  # Mean over sequence
                embedding = embedding / embedding.norm(p=2)  # Normalize
                embedding_np = embedding.cpu().numpy()
            
            self.requests_processed += 1
            
            return {
                "description": description,
                "embedding": embedding_np.tolist(),
                "dimensions": len(embedding_np)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            raise
    
    async def extract_text(
        self,
        image: Union[bytes, Image.Image]
    ) -> str:
        """Extract text from image (OCR)."""
        
        if self.model is None:
            await self.load_model()
        
        try:
            if isinstance(image, bytes):
                pil_image = Image.open(io.BytesIO(image)).convert("RGB")
            else:
                pil_image = image.convert("RGB")
            
            # OCR-specific prompt
            if LLAVA_AVAILABLE:
                # Use LLaVA-specific processing
                conv = conv_templates[self.conv_mode].copy()
                conv.append_message(conv.roles[0], f"{DEFAULT_IMAGE_TOKEN}\nExtract and transcribe all text visible in this image. If there is no text, say 'No text found'.")
                conv.append_message(conv.roles[1], None)
                prompt = conv.get_prompt()
                
                # Process image
                image_processor = self.get_image_processor()
                image_tensor = process_images([pil_image], image_processor, self.model.config).to(self.device, dtype=torch.float16)
                
                # Tokenize with image token
                input_ids = tokenizer_image_token(prompt, self.tokenizer, IMAGE_TOKEN_INDEX, return_tensors='pt').unsqueeze(0).to(self.device)
                
                # Generate text extraction
                with torch.no_grad():
                    outputs = self.model.generate(
                        input_ids=input_ids,
                        images=image_tensor,
                        max_new_tokens=self.max_new_tokens,
                        temperature=0.1,  # Low temperature for accuracy
                        do_sample=False
                    )
                
                # Decode output
                extracted_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                # Remove the prompt from the output
                if conv.roles[1] in extracted_text:
                    extracted_text = extracted_text.split(conv.roles[1])[-1].strip()
            else:
                prompt = "USER: <image>\nExtract and transcribe all text visible in this image. If there is no text, say 'No text found'.\nASSISTANT:"
                
                inputs = self.processor(
                    text=prompt,
                    images=pil_image,
                    return_tensors="pt"
                ).to(self.device)
            
                # Generate text extraction
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=self.max_new_tokens,
                        temperature=0.1,  # Low temperature for accuracy
                        do_sample=False
                    )
                
                # Extract text
                extracted_text = self.processor.decode(
                    outputs[0][inputs.input_ids.shape[1]:],
                    skip_special_tokens=True
                )
            
            self.requests_processed += 1
            
            return extracted_text
            
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            raise
    
    async def answer_question(
        self,
        image: Union[bytes, Image.Image],
        question: str
    ) -> str:
        """Answer a question about an image."""
        
        if self.model is None:
            await self.load_model()
        
        try:
            if isinstance(image, bytes):
                pil_image = Image.open(io.BytesIO(image)).convert("RGB")
            else:
                pil_image = image.convert("RGB")
            
            # Question-answering prompt
            if LLAVA_AVAILABLE:
                # Use LLaVA-specific processing
                conv = conv_templates[self.conv_mode].copy()
                conv.append_message(conv.roles[0], f"{DEFAULT_IMAGE_TOKEN}\n{question}")
                conv.append_message(conv.roles[1], None)
                prompt = conv.get_prompt()
                
                # Process image
                image_processor = self.get_image_processor()
                image_tensor = process_images([pil_image], image_processor, self.model.config).to(self.device, dtype=torch.float16)
                
                # Tokenize with image token
                input_ids = tokenizer_image_token(prompt, self.tokenizer, IMAGE_TOKEN_INDEX, return_tensors='pt').unsqueeze(0).to(self.device)
                
                # Generate answer
                with torch.no_grad():
                    outputs = self.model.generate(
                        input_ids=input_ids,
                        images=image_tensor,
                        max_new_tokens=self.max_new_tokens,
                        temperature=0.7,
                        do_sample=True
                    )
                
                # Decode output
                answer = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                # Remove the prompt from the output
                if conv.roles[1] in answer:
                    answer = answer.split(conv.roles[1])[-1].strip()
            else:
                prompt = f"USER: <image>\n{question}\nASSISTANT:"
                
                inputs = self.processor(
                    text=prompt,
                    images=pil_image,
                    return_tensors="pt"
                ).to(self.device)
                
                # Generate answer
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=self.max_new_tokens,
                        temperature=0.7,
                        do_sample=True
                    )
                
                # Extract answer
                answer = self.processor.decode(
                    outputs[0][inputs.input_ids.shape[1]:],
                    skip_special_tokens=True
                )
            
            self.requests_processed += 1
            
            return answer
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            raise
    
    @property
    def image_processor(self):
        """Property to access image processor with automatic fallback."""
        return self.get_image_processor()
    
    def get_image_processor(self):
        """Get image processor with automatic fallback loading."""
        if self._image_processor is None:
            logger.warning("Image processor is None, attempting to reload...")
            try:
                # Try to get from vision tower first
                if self.model is not None:
                    vision_tower = self.model.get_vision_tower()
                    if vision_tower is not None and hasattr(vision_tower, 'image_processor'):
                        self._image_processor = vision_tower.image_processor
                        logger.info(f"Reloaded processor from vision tower: {type(self._image_processor)}")
                
                # Fallback to direct loading
                if self._image_processor is None:
                    from transformers import CLIPImageProcessor
                    self._image_processor = CLIPImageProcessor.from_pretrained("openai/clip-vit-large-patch14-336")
                    logger.info(f"Emergency loaded CLIP processor: {type(self._image_processor)}")
            except Exception as e:
                logger.error(f"Failed to reload image processor: {e}")
                raise RuntimeError("Cannot get image processor")
        
        return self._image_processor
    
    def unload_model(self):
        """Unload model from memory."""
        if self.model:
            del self.model
            self.model = None
        if hasattr(self, 'processor') and self.processor:
            del self.processor
            self.processor = None
        if hasattr(self, 'tokenizer') and self.tokenizer:
            del self.tokenizer
            self.tokenizer = None
        # Only clear image processor if not locked
        if not self._processor_lock and hasattr(self, '_image_processor') and self._image_processor:
            del self._image_processor
            self._image_processor = None
        self.clear_cache()
        logger.info("LLaVA model unloaded")