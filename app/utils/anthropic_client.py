"""Anthropic Client Configuration

This module provides a singleton Anthropic client instance that can be used
throughout the application for Claude AI features.
"""

import os
from functools import lru_cache
from typing import Optional

from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# Global client instance
_anthropic_client = None

# Check if Anthropic is available
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None
    logger.warning("anthropic package not installed. Install with: pip install anthropic")


@lru_cache(maxsize=1)
def get_anthropic_client() -> Optional["anthropic.Anthropic"]:
    """Get the singleton Anthropic client instance.
    
    Returns:
        Anthropic client instance or None if not available
    """
    global _anthropic_client
    
    if not ANTHROPIC_AVAILABLE:
        return None
    
    if _anthropic_client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set, Anthropic client will not be available")
            return None
        
        try:
            _anthropic_client = anthropic.Anthropic(api_key=api_key)
            logger.info("Anthropic client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            return None
    
    return _anthropic_client


def create_claude_completion(
    prompt: str,
    model: str = "claude-3-opus-20240229",
    max_tokens: int = 1024,
    temperature: float = 0.7,
    **kwargs
) -> Optional[str]:
    """Create a completion using Claude.
    
    Args:
        prompt: The prompt to send to Claude
        model: The model to use (default: claude-3-opus)
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        **kwargs: Additional parameters for the API
        
    Returns:
        The completion text or None if failed
    """
    client = get_anthropic_client()
    if not client:
        logger.warning("Anthropic client not available, returning None")
        return None
    
    try:
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "user", "content": prompt}
            ],
            **kwargs
        )
        return message.content[0].text
    except Exception as e:
        error_msg = str(e)
        if "credit balance is too low" in error_msg:
            logger.error(
                "Anthropic API requires credits. Note: Claude Pro/Max subscriptions "
                "are separate from API credits. Add API credits at: "
                "https://console.anthropic.com/settings/billing"
            )
        else:
            logger.error(f"Failed to create Claude completion: {e}")
        return None


def analyze_with_claude(
    content: str,
    analysis_type: str = "general",
    model: str = "claude-3-opus-20240229"
) -> Optional[dict]:
    """Analyze content using Claude for specific insights.
    
    Args:
        content: The content to analyze
        analysis_type: Type of analysis (general, code, summary, etc.)
        model: The Claude model to use
        
    Returns:
        Analysis results as a dict or None if failed
    """
    prompts = {
        "general": f"Analyze the following content and provide key insights:\n\n{content}",
        "code": f"Analyze this code and identify patterns, issues, and improvements:\n\n{content}",
        "summary": f"Provide a concise summary of the following:\n\n{content}",
        "topics": f"Extract the main topics and themes from this content:\n\n{content}",
        "questions": f"Generate thoughtful questions based on this content:\n\n{content}"
    }
    
    prompt = prompts.get(analysis_type, prompts["general"])
    
    result = create_claude_completion(
        prompt=prompt,
        model=model,
        temperature=0.5,  # Lower temperature for analysis tasks
        max_tokens=2048
    )
    
    if result:
        return {
            "analysis_type": analysis_type,
            "model": model,
            "result": result
        }
    return None


def compare_ai_models(
    prompt: str,
    openai_client=None,
    anthropic_client=None
) -> dict:
    """Compare responses from OpenAI and Anthropic models.
    
    Args:
        prompt: The prompt to send to both models
        openai_client: OpenAI client instance
        anthropic_client: Anthropic client instance
        
    Returns:
        Dict with responses from both models
    """
    results = {}
    
    # Get Claude response
    if anthropic_client or get_anthropic_client():
        claude_response = create_claude_completion(prompt)
        results["claude"] = claude_response
    
    # Get GPT response if OpenAI client provided
    if openai_client:
        try:
            gpt_response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024
            )
            results["gpt"] = gpt_response.choices[0].message.content
        except Exception as e:
            logger.error(f"Failed to get GPT response: {e}")
            results["gpt"] = None
    
    return results


# Example usage for Second Brain features
def generate_memory_insights(memory_content: str) -> Optional[dict]:
    """Generate AI-powered insights for a memory using Claude.
    
    Args:
        memory_content: The memory content to analyze
        
    Returns:
        Dict with various insights or None
    """
    client = get_anthropic_client()
    if not client:
        return None
    
    try:
        # Create a comprehensive prompt for memory analysis
        prompt = f"""Analyze this memory and provide structured insights:

Memory Content:
{memory_content}

Please provide:
1. Key topics and themes
2. Important entities mentioned (people, places, concepts)
3. Potential connections to other knowledge areas
4. Questions this memory raises
5. A brief summary (2-3 sentences)

Format your response as a structured analysis."""

        response = create_claude_completion(
            prompt=prompt,
            model="claude-3-opus-20240229",
            temperature=0.3,  # Low temperature for consistent analysis
            max_tokens=1500
        )
        
        if response:
            return {
                "raw_analysis": response,
                "model": "claude-3-opus-20240229",
                "timestamp": os.popen('date').read().strip()
            }
    except Exception as e:
        logger.error(f"Failed to generate memory insights: {e}")
    
    return None