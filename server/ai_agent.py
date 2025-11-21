"""
AI Agent module for generating prompts for multi-clip workflows.

Integrates with the AI LLM agent from brousla-app-server to generate diverse,
contextual prompts for each clip based on the concept and number of clips.
"""
import os
import requests
import logging
from typing import List

# Configure logging
logger = logging.getLogger(__name__)

# API configuration - can be overridden via environment variable
AI_API_BASE_URL = os.getenv('AI_API_BASE_URL', 'http://localhost:8001')


def generate_prompts(concept: str, numberOfClips: int) -> List[str]:
    """
    Generate prompts for each clip based on the concept and number of clips.
    
    This function calls the AI LLM agent from brousla-app-server to generate
    diverse, contextual prompts for each clip. If the API call fails, it falls
    back to returning identical prompts (the concept repeated).
    
    Args:
        concept: The base concept/prompt for the workflow
        numberOfClips: Number of clips to generate
        
    Returns:
        List of prompts, one for each clip. Each prompt is distinct but related
        to the concept, creating a cohesive narrative flow.
    
    Note:
        If the AI service is unavailable, falls back to returning the concept
        repeated for all clips (backward compatibility).
    """
    if numberOfClips < 1:
        raise ValueError("numberOfClips must be at least 1")
    
    if not concept or not concept.strip():
        raise ValueError("concept cannot be empty")
    
    # Try to get prompts from AI agent
    try:
        api_url = f"{AI_API_BASE_URL}/api/generate-prompts"
        payload = {
            "concept": concept.strip(),
            "number_of_clips": numberOfClips
        }
        
        logger.info(f"Requesting prompts from AI agent: {api_url}")
        response = requests.post(
            api_url,
            json=payload,
            timeout=30  # 30 second timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            prompts = result.get('prompts', [])
            
            # Validate prompts
            if prompts and isinstance(prompts, list) and len(prompts) == numberOfClips:
                logger.info(f"Successfully generated {len(prompts)} prompts from AI agent")
                return prompts
            else:
                logger.warning(
                    f"AI agent returned invalid prompts: expected {numberOfClips}, "
                    f"got {len(prompts) if prompts else 0}. Falling back to concept repetition."
                )
        else:
            logger.warning(
                f"AI agent returned status {response.status_code}: {response.text}. "
                "Falling back to concept repetition."
            )
    
    except requests.exceptions.RequestException as e:
        logger.warning(
            f"Failed to connect to AI agent at {AI_API_BASE_URL}: {e}. "
            "Falling back to concept repetition."
        )
    except Exception as e:
        logger.error(f"Unexpected error while generating prompts: {e}. Falling back to concept repetition.")
    
    # Fallback: return identical prompts for all clips (backward compatibility)
    logger.info(f"Using fallback: returning concept repeated {numberOfClips} times")
    return [concept.strip()] * numberOfClips

