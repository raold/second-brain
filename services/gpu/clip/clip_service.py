"""CLIP service for fast multimodal embeddings."""

import io
import time
import torch
import numpy as np
from PIL import Image
from typing import Union, List, Optional
import logging

from transformers import CLIPProcessor, CLIPModel
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from shared.base_model import BaseModelService

logger = logging.getLogger(__name__)


class CLIPService(BaseModelService):
    """CLIP model service for text and image embeddings."""
    
    def __init__(
        self,
        model_name: str = "openai/clip-vit-large-patch14",
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
    ):
        super().__init__(model_name, device)
        self.embedding_dim = 768  # ViT-L/14 dimension
        
    async def load_model(self):
        """Load CLIP model and processor."""
        try:
            logger.info(f"Loading CLIP model: {self.model_name}")
            
            # Load with automatic device mapping
            self.model = CLIPModel.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
            ).to(self.device)
            
            self.processor = CLIPProcessor.from_pretrained(self.model_name)
            
            # Set to eval mode
            self.model.eval()
            
            logger.info(f"CLIP model loaded on {self.device}")
            logger.info(f"Model info: {self.get_device_info()}")
            
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            raise
    
    async def generate_embedding(
        self, 
        content: Union[str, bytes, Image.Image]
    ) -> np.ndarray:
        """Generate CLIP embedding for text or image."""
        
        if self.model is None:
            await self.load_model()
        
        try:
            with torch.no_grad():
                if isinstance(content, str):
                    # Text embedding
                    inputs = self.processor(
                        text=content,
                        return_tensors="pt",
                        padding=True,
                        truncation=True,
                        max_length=77
                    ).to(self.device)
                    
                    embeddings = self.model.get_text_features(**inputs)
                    
                elif isinstance(content, (bytes, Image.Image)):
                    # Image embedding
                    if isinstance(content, bytes):
                        image = Image.open(io.BytesIO(content)).convert("RGB")
                    else:
                        image = content.convert("RGB")
                    
                    inputs = self.processor(
                        images=image,
                        return_tensors="pt"
                    ).to(self.device)
                    
                    embeddings = self.model.get_image_features(**inputs)
                    
                else:
                    raise ValueError(f"Unsupported content type: {type(content)}")
                
                # Normalize embeddings
                embeddings = embeddings / embeddings.norm(p=2, dim=-1, keepdim=True)
                
                # Convert to numpy
                embeddings_np = embeddings.cpu().numpy()
                
                self.requests_processed += 1
                
                return embeddings_np[0]  # Return first item for single input
                
        except Exception as e:
            logger.error(f"Error generating CLIP embedding: {e}")
            raise
    
    async def generate_batch_embeddings(
        self,
        contents: List[Union[str, bytes, Image.Image]],
        batch_size: int = 8
    ) -> List[np.ndarray]:
        """Generate embeddings for multiple inputs."""
        
        if self.model is None:
            await self.load_model()
        
        embeddings = []
        
        # Process in batches
        for i in range(0, len(contents), batch_size):
            batch = contents[i:i + batch_size]
            
            # Separate text and images
            texts = [c for c in batch if isinstance(c, str)]
            images = [c for c in batch if not isinstance(c, str)]
            
            batch_embeddings = []
            
            with torch.no_grad():
                # Process texts
                if texts:
                    inputs = self.processor(
                        text=texts,
                        return_tensors="pt",
                        padding=True,
                        truncation=True,
                        max_length=77
                    ).to(self.device)
                    
                    text_embeddings = self.model.get_text_features(**inputs)
                    text_embeddings = text_embeddings / text_embeddings.norm(p=2, dim=-1, keepdim=True)
                    batch_embeddings.extend(text_embeddings.cpu().numpy())
                
                # Process images
                if images:
                    pil_images = []
                    for img in images:
                        if isinstance(img, bytes):
                            pil_images.append(Image.open(io.BytesIO(img)).convert("RGB"))
                        else:
                            pil_images.append(img.convert("RGB"))
                    
                    inputs = self.processor(
                        images=pil_images,
                        return_tensors="pt"
                    ).to(self.device)
                    
                    image_embeddings = self.model.get_image_features(**inputs)
                    image_embeddings = image_embeddings / image_embeddings.norm(p=2, dim=-1, keepdim=True)
                    batch_embeddings.extend(image_embeddings.cpu().numpy())
            
            embeddings.extend(batch_embeddings)
            
        self.requests_processed += len(contents)
        
        return embeddings
    
    async def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """Compute cosine similarity between embeddings."""
        return float(np.dot(embedding1, embedding2))
    
    def unload_model(self):
        """Unload model from memory."""
        if self.model:
            del self.model
            self.model = None
        if self.processor:
            del self.processor
            self.processor = None
        self.clear_cache()
        logger.info("CLIP model unloaded")