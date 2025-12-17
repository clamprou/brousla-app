"""
AI Agent module for generating prompts for multi-clip workflows.

Integrates with the AI LLM agent from api-server to generate diverse,
contextual prompts for each clip based on the concept and number of clips.
"""
import os
import json
import requests
import logging
from typing import List, Optional

# Configure logging
logger = logging.getLogger(__name__)

# API configuration - can be overridden via environment variable
AI_API_BASE_URL = os.getenv('AI_API_BASE_URL', 'http://localhost:8001')


def generate_prompts(
    concept: str, 
    numberOfClips: int, 
    previous_prompts: Optional[List[str]] = None,
    previous_summaries: Optional[List[str]] = None,
    user_id: Optional[str] = None
) -> List[str]:
    """
    Generate prompts for each clip based on the concept and number of clips.
    
    This function calls the AI LLM agent from api-server to generate
    diverse, contextual prompts for each clip. If the API call fails, an error
    will be raised with details about what went wrong.
    
    Args:
        concept: The base concept/prompt for the workflow
        numberOfClips: Number of clips to generate
        previous_prompts: Optional list of previous prompts to avoid similarity (backward compatibility)
        previous_summaries: Optional list of previous generation summaries to avoid similarity (preferred)
        
    Returns:
        List of prompts, one for each clip. Each prompt is distinct but related
        to the concept, creating a cohesive narrative flow.
    
    Raises:
        ValueError: If numberOfClips < 1 or concept is empty
        ConnectionError: If unable to connect to the AI API
        requests.exceptions.HTTPError: If the API returns an error status code
        RuntimeError: If the API response is invalid or unexpected
    """
    if numberOfClips < 1:
        raise ValueError("numberOfClips must be at least 1")
    
    if not concept or not concept.strip():
        raise ValueError("concept cannot be empty")
    
    api_url = f"{AI_API_BASE_URL}/api/generate-prompts"
    payload = {
        "concept": concept.strip(),
        "number_of_clips": numberOfClips
    }
    
    # Prefer summaries over full prompts for efficiency
    if previous_summaries:
        payload["previous_summaries"] = previous_summaries
    elif previous_prompts:
        # Fallback to previous prompts for backward compatibility
        payload["previous_prompts"] = previous_prompts
    
    # Debug logging: Log the full request details
    logger.debug("=" * 80)
    logger.debug("AI AGENT REQUEST - Sending to ChatGPT Agent")
    logger.debug("=" * 80)
    logger.debug(f"API URL: {api_url}")
    logger.debug(f"Request Method: POST")
    logger.debug(f"Request Payload (JSON):")
    logger.debug(json.dumps(payload, indent=2))
    logger.debug(f"Request Headers: Content-Type: application/json")
    logger.debug(f"Timeout: 30 seconds")
    logger.debug("=" * 80)
    
    logger.info(f"Requesting prompts from AI agent: {api_url}")
    
    try:
        headers = {"Content-Type": "application/json"}
        if user_id:
            headers["X-User-Id"] = user_id
        
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=30  # 30 second timeout
        )
        
        # Debug logging: Log the response details
        logger.debug("=" * 80)
        logger.debug("AI AGENT RESPONSE - Received from ChatGPT Agent")
        logger.debug("=" * 80)
        logger.debug(f"Response Status Code: {response.status_code}")
        logger.debug(f"Response Headers: {dict(response.headers)}")
        try:
            response_json = response.json()
            logger.debug(f"Response Body (JSON):")
            logger.debug(json.dumps(response_json, indent=2))
        except:
            logger.debug(f"Response Body (Raw): {response.text[:500]}")
        logger.debug("=" * 80)
        
        # Raise an exception for HTTP error status codes
        response.raise_for_status()
        
        # Parse response
        try:
            result = response.json()
        except ValueError as e:
            raise RuntimeError(
                f"AI agent returned invalid JSON response. "
                f"Response status: {response.status_code}, "
                f"Response text: {response.text[:200]}"
            ) from e
        
        prompts = result.get('prompts', [])
        
        # Validate prompts
        if not prompts:
            raise RuntimeError(
                f"AI agent returned empty prompts list. "
                f"Response: {result}"
            )
        
        if not isinstance(prompts, list):
            raise RuntimeError(
                f"AI agent returned invalid prompts format. "
                f"Expected list, got {type(prompts)}. "
                f"Response: {result}"
            )
        
        if len(prompts) != numberOfClips:
            raise RuntimeError(
                f"AI agent returned incorrect number of prompts. "
                f"Expected {numberOfClips}, got {len(prompts)}. "
                f"Prompts: {prompts}"
            )
        
        # Validate all prompts are strings
        if not all(isinstance(p, str) and p.strip() for p in prompts):
            raise RuntimeError(
                f"AI agent returned invalid prompt format. "
                f"All prompts must be non-empty strings. "
                f"Prompts: {prompts}"
            )
        
        logger.info(f"Successfully generated {len(prompts)} prompts from AI agent")
        return prompts
    
    except requests.exceptions.ConnectionError as e:
        error_msg = (
            f"Failed to connect to AI agent at {AI_API_BASE_URL}. "
            f"Please ensure the api-server is running and accessible. "
            f"Error: {str(e)}"
        )
        logger.error(error_msg)
        raise ConnectionError(error_msg) from e
    
    except requests.exceptions.Timeout as e:
        error_msg = (
            f"Request to AI agent timed out after 30 seconds. "
            f"API URL: {api_url}. "
            f"Error: {str(e)}"
        )
        logger.error(error_msg)
        raise ConnectionError(error_msg) from e
    
    except requests.exceptions.HTTPError as e:
        error_msg = (
            f"AI agent returned HTTP error {response.status_code}. "
            f"API URL: {api_url}. "
            f"Response: {response.text[:500]}"
        )
        logger.error(error_msg)
        raise requests.exceptions.HTTPError(error_msg, response=response) from e
    
    except requests.exceptions.RequestException as e:
        error_msg = (
            f"Request to AI agent failed. "
            f"API URL: {api_url}. "
            f"Error: {str(e)}"
        )
        logger.error(error_msg)
        raise ConnectionError(error_msg) from e

