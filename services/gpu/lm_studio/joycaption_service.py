"""
JoyCaption Integration for Advanced Image Captioning
Uses the llama-joycaption-beta model through LM Studio
"""

import asyncio
import aiohttp
import base64
import io
from PIL import Image
from typing import Optional, Dict, Any, Union
import logging

logger = logging.getLogger(__name__)


class JoyCaptionService:
    """Interface to JoyCaption model via LM Studio"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:1234"):
        self.base_url = base_url
        self.api_base = f"{base_url}/v1"
        self.model_name = "llama-joycaption-beta-one-hf-llava"
        
    async def caption_image(
        self, 
        image: Union[bytes, Image.Image],
        style: str = "descriptive",  # descriptive, artistic, technical, medical
        max_tokens: int = 300
    ) -> Dict[str, Any]:
        """Generate detailed caption for image using JoyCaption"""
        
        # Convert image to base64
        if isinstance(image, bytes):
            img = Image.open(io.BytesIO(image))
        else:
            img = image
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if too large (JoyCaption works best with standard sizes)
        max_size = 1024
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Prepare prompt based on style
        prompts = {
            "descriptive": "Provide a detailed, comprehensive description of this image.",
            "artistic": "Describe this image with artistic and creative language.",
            "technical": "Provide a technical analysis of this image's composition and elements.",
            "medical": "Describe this image focusing on any medical or clinical aspects.",
            "brief": "Provide a brief, one-sentence caption for this image."
        }
        
        prompt = prompts.get(style, prompts["descriptive"])
        
        try:
            async with aiohttp.ClientSession() as session:
                # JoyCaption expects multimodal input
                payload = {
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{img_base64}"
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                    "stream": False
                }
                
                async with session.post(
                    f"{self.api_base}/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        caption = data["choices"][0]["message"]["content"]
                        
                        return {
                            "caption": caption,
                            "style": style,
                            "image_size": img.size,
                            "tokens_used": data.get("usage", {}).get("completion_tokens", 0)
                        }
                    else:
                        error = await resp.text()
                        logger.error(f"JoyCaption failed: {error}")
                        raise Exception(f"Caption generation failed: {error}")
                        
        except Exception as e:
            logger.error(f"JoyCaption error: {e}")
            raise
    
    async def batch_caption(
        self,
        images: list,
        style: str = "descriptive"
    ) -> list:
        """Caption multiple images"""
        results = []
        for image in images:
            try:
                result = await self.caption_image(image, style)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to caption image: {e}")
                results.append({"error": str(e)})
        return results
    
    async def extract_text_from_image(
        self,
        image: Union[bytes, Image.Image]
    ) -> str:
        """Extract any text visible in the image"""
        prompt = "Extract and transcribe all text visible in this image. If no text is present, respond with 'No text found'."
        
        result = await self.caption_image(image, style="technical")
        
        # Also ask specifically for text
        if isinstance(image, bytes):
            img = Image.open(io.BytesIO(image))
        else:
            img = image
            
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{img_base64}"
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    "max_tokens": 500,
                    "temperature": 0.3,  # Lower temperature for accuracy
                    "stream": False
                }
                
                async with session.post(
                    f"{self.api_base}/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        return "Failed to extract text"
        except:
            return result["caption"]  # Fall back to regular caption
    
    async def analyze_document_image(
        self,
        image: Union[bytes, Image.Image]
    ) -> Dict[str, Any]:
        """Specialized analysis for document images"""
        
        # Get multiple perspectives
        tasks = [
            self.caption_image(image, "descriptive"),
            self.extract_text_from_image(image)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        caption_result = results[0] if not isinstance(results[0], Exception) else {"caption": "Error generating caption"}
        ocr_text = results[1] if not isinstance(results[1], Exception) else "Error extracting text"
        
        return {
            "description": caption_result.get("caption", ""),
            "extracted_text": ocr_text,
            "image_size": caption_result.get("image_size", (0, 0)),
            "analysis_complete": True
        }


# Test function
async def test_joycaption():
    """Test JoyCaption integration"""
    service = JoyCaptionService()
    
    print("Testing JoyCaption Integration")
    print("=" * 50)
    
    # Create a test image
    from PIL import Image, ImageDraw, ImageFont
    
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw some shapes and text
    draw.rectangle([50, 50, 200, 200], fill='blue')
    draw.ellipse([250, 50, 400, 200], fill='red')
    draw.text((100, 300), "JoyCaption Test Image", fill='black')
    draw.text((100, 350), "Second Brain v5.0", fill='green')
    
    # Test captioning
    print("\n1. Testing image captioning...")
    result = await service.caption_image(img, style="descriptive")
    print(f"Caption: {result['caption']}")
    
    print("\n2. Testing text extraction...")
    text = await service.extract_text_from_image(img)
    print(f"Extracted text: {text}")
    
    print("\n3. Testing document analysis...")
    analysis = await service.analyze_document_image(img)
    print(f"Analysis: {analysis}")


if __name__ == "__main__":
    asyncio.run(test_joycaption())