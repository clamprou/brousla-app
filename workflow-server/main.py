import os
import json
import uuid
import asyncio
import base64
import shutil
import traceback
import logging
import math
from datetime import datetime
from typing import Optional, List, Dict

from fastapi import FastAPI, Query, UploadFile, File, Form, Body, Request
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
import requests

# Import ComfyUI client
from comfyui_client import ComfyUIClient

# Import workflow scheduler and executor
from workflow_scheduler import initialize_scheduler, get_scheduler
from workflow_executor import execute_workflow

# Optional: OpenAI client
try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), 'workflows')
OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), 'outputs')
STORED_WORKFLOWS_DIR = os.path.join(DATA_DIR, 'stored_workflows')
STORED_WORKFLOWS_USERS_DIR = os.path.join(STORED_WORKFLOWS_DIR, 'users')

PREFERENCES_PATH = os.path.join(DATA_DIR, 'preferences.json')
HISTORY_PATH = os.path.join(DATA_DIR, 'history.json')
PROMPT_HISTORY_PATH = os.path.join(DATA_DIR, 'prompt_history.json')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(WORKFLOWS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(STORED_WORKFLOWS_DIR, exist_ok=True)
os.makedirs(STORED_WORKFLOWS_USERS_DIR, exist_ok=True)


# Helper function to get user ID from request headers
def _get_user_id_from_request(request) -> Optional[str]:
    """Extract user ID from request headers"""
    user_id = request.headers.get('X-User-Id')
    return user_id


# Helper functions for user-scoped paths
def _get_user_stored_workflows_dir(user_id: str) -> str:
    """Get the directory for a user's stored workflows"""
    user_dir = os.path.join(STORED_WORKFLOWS_USERS_DIR, user_id)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def _get_user_stored_workflows_metadata_path(user_id: str) -> str:
    """Get the path to user's stored workflows metadata file"""
    return os.path.join(_get_user_stored_workflows_dir(user_id), 'metadata.json')


def _get_user_workflow_state_path(user_id: str) -> str:
    """Get the path to user's workflow state file"""
    return os.path.join(DATA_DIR, f'workflow_state_{user_id}.json')


# Lifespan event handlers (replaces deprecated on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup workflow scheduler"""
    try:
        # Startup
        # Scheduler callbacks that handle user-scoped workflows
        def get_workflows():
            """Get all active workflows from state files and cache, with user_id attached"""
            all_workflows = []
            
            # First, scan all workflow state files to find active workflows
            # This ensures we find workflows even if cache is empty
            data_dir = DATA_DIR
            state_files = []
            if os.path.exists(data_dir):
                for filename in os.listdir(data_dir):
                    if filename.startswith('workflow_state_') and filename.endswith('.json'):
                        state_files.append(os.path.join(data_dir, filename))
            
            active_workflow_ids_by_user = {}  # {user_id: [workflow_ids]}
            
            for state_file in state_files:
                try:
                    # Extract user_id from filename: workflow_state_{user_id}.json
                    filename = os.path.basename(state_file)
                    if filename.startswith('workflow_state_') and filename.endswith('.json'):
                        user_id = filename[len('workflow_state_'):-len('.json')]
                        
                        # Read state file
                        states = _read_json(state_file, {})
                        
                        # Find active workflows and store their state for later use
                        for workflow_id, state in states.items():
                            if state.get('isActive', False) and not state.get('isRunning', False) and not state.get('cancelled', False):
                                next_execution = state.get('nextExecutionTime')
                                # Only include workflows that are scheduled (have nextExecutionTime set)
                                # Skip workflows with nextExecutionTime=None as they're handled by activation endpoint, not scheduler
                                if next_execution is not None:
                                    if user_id not in active_workflow_ids_by_user:
                                        active_workflow_ids_by_user[user_id] = []
                                    # Store workflow_id with its state for later reference
                                    active_workflow_ids_by_user[user_id].append((workflow_id, state))
                except Exception as e:
                    logger.warning(f"Error reading state file {state_file}: {e}")
            
            # Now get workflow data from cache or stored workflows
            for user_id, workflow_items in active_workflow_ids_by_user.items():
                # Get workflows from cache - this is the source of truth for workflow configuration
                cached_workflows = _workflows_cache.get(user_id, [])
                cached_workflow_dict = {w.get('id'): w for w in cached_workflows}
                
                for workflow_item in workflow_items:
                    # Handle both tuple (workflow_id, state) and plain workflow_id for backward compatibility
                    if isinstance(workflow_item, tuple):
                        workflow_id, workflow_state = workflow_item
                    else:
                        workflow_id = workflow_item
                        workflow_state = {}
                    # Get workflow from cache
                    workflow = cached_workflow_dict.get(workflow_id)
                    
                    # If not in cache, try to load from stored workflows
                    if not workflow:
                        try:
                            # Load workflow from stored workflows
                            metadata = _get_stored_workflows_metadata(user_id)
                            workflow_meta = next((w for w in metadata.get("workflows", []) if w.get("id") == workflow_id and w.get("userId") == user_id), None)
                            
                            if workflow_meta:
                                # Load the actual workflow file
                                workflow_path = _get_stored_workflow_file_path(user_id, workflow_id)
                                if os.path.exists(workflow_path):
                                    with open(workflow_path, 'r', encoding='utf-8') as f:
                                        workflow_json = json.load(f)
                                    
                                    # Construct workflow object similar to what's in cache
                                    # We need to reconstruct the workflow format that includes concept, videoWorkflowFile, etc.
                                    # The workflow_executor requires: concept, videoWorkflowFile, schedule (optional, defaults to 60)
                                    workflow = {
                                        'id': workflow_id,
                                        'name': workflow_meta.get('name', 'Unnamed'),
                                        'userId': user_id,
                                        'videoWorkflowFile': workflow_json,  # The actual workflow JSON
                                        'concept': workflow_meta.get('name', '') or 'Workflow',  # Use name as concept
                                        'schedule': 60,  # Default schedule (workflow_executor also defaults to 60)
                                        'numberOfClips': 1  # Default to 1 clip
                                    }
                                    
                                    # Add to cache for future use
                                    if not any(w.get('id') == workflow_id for w in cached_workflows):
                                        cached_workflows.append(workflow)
                                        _set_workflows_cache(user_id, cached_workflows)
                                        # Update cached_workflow_dict so it's available for subsequent iterations
                                        cached_workflow_dict[workflow_id] = workflow
                                    
                                    logger.info(f"Loaded active workflow {workflow_id} (user {user_id}) from stored workflows")
                                else:
                                    logger.warning(f"Active workflow {workflow_id} (user {user_id}) found in metadata but file not found at {workflow_path}")
                            else:
                                # Workflow not in stored workflows - it may exist only in frontend localStorage
                                # Log detailed info to help debug
                                all_stored_ids = [w.get("id") for w in metadata.get("workflows", [])]
                                logger.warning(
                                    f"Active workflow {workflow_id} (user {user_id}) not found in cache or stored workflows. "
                                    f"Stored workflow IDs: {all_stored_ids}. "
                                    f"This workflow may exist only in frontend localStorage. "
                                    f"Frontend should sync workflows to persist them."
                                )
                        except Exception as e:
                            logger.warning(f"Error loading workflow {workflow_id} (user {user_id}) from stored workflows: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    if workflow:
                        # Verify workflow has required fields
                        if workflow.get('videoWorkflowFile'):
                            workflow_with_user = workflow.copy()
                            workflow_with_user['_scheduler_user_id'] = user_id
                            # Ensure concept exists (required by workflow executor)
                            if not workflow_with_user.get('concept'):
                                workflow_with_user['concept'] = workflow_with_user.get('name', 'Workflow')
                            # Ensure schedule exists (default to 60 if not present)
                            if not workflow_with_user.get('schedule'):
                                workflow_with_user['schedule'] = 60
                            all_workflows.append(workflow_with_user)
                        else:
                            logger.warning(f"Active workflow {workflow_id} (user {user_id}) missing required fields (videoWorkflowFile)")
                    else:
                        logger.warning(f"Active workflow {workflow_id} (user {user_id}) could not be loaded")
            
            if all_workflows:
                logger.debug(f"Scheduler found {len(all_workflows)} active workflow(s) to check")
            return all_workflows
        
        def get_state(workflow_id: str):
            """Get workflow state - extract user_id from workflow if available"""
            # This is called by scheduler with workflow_id, but we need user_id
            # We need to find the user_id by searching through all users' workflows and state files
            # First try cache
            for user_id, workflows in _workflows_cache.items():
                for workflow in workflows:
                    if workflow.get('id') == workflow_id:
                        state = _get_workflow_state(user_id, workflow_id)
                        return state
            
            # If not in cache, scan state files to find user_id
            data_dir = DATA_DIR
            if os.path.exists(data_dir):
                for filename in os.listdir(data_dir):
                    if filename.startswith('workflow_state_') and filename.endswith('.json'):
                        user_id = filename[len('workflow_state_'):-len('.json')]
                        state = _get_workflow_state(user_id, workflow_id)
                        # Check if this workflow exists in this user's state
                        if state.get('isActive') is not None or state.get('lastExecutionTime') is not None:
                            return state
            
            # If not found, return default state
            return {"isActive": False, "isRunning": False, "nextExecutionTime": None}
        
        def update_state(workflow_id: str, updates: dict):
            """Update workflow state - find user_id from workflow cache or state files"""
            # Find which user owns this workflow - first try cache
            for user_id, workflows in _workflows_cache.items():
                for workflow in workflows:
                    if workflow.get('id') == workflow_id:
                        _update_workflow_state(user_id, workflow_id, updates)
                        return
            
            # If not in cache, scan state files to find user_id
            data_dir = DATA_DIR
            if os.path.exists(data_dir):
                for filename in os.listdir(data_dir):
                    if filename.startswith('workflow_state_') and filename.endswith('.json'):
                        user_id = filename[len('workflow_state_'):-len('.json')]
                        state = _get_workflow_state(user_id, workflow_id)
                        # Check if this workflow exists in this user's state
                        if state.get('isActive') is not None or state.get('lastExecutionTime') is not None:
                            _update_workflow_state(user_id, workflow_id, updates)
                            return
            
            # If workflow not found, log warning but don't fail
            logger.warning(f"Could not find user for workflow {workflow_id} when updating state")
        
        def exec_workflow(workflow: dict, workflow_id: str):
            """Execute workflow with current ComfyUI settings"""
            # Extract user_id from workflow (set by get_workflows)
            user_id = workflow.get('_scheduler_user_id')
            if not user_id:
                # Fallback: try to find user_id from workflow's userId field
                user_id = workflow.get('userId')
            
            if not user_id:
                logger.error(f"Cannot execute workflow {workflow_id}: no user_id found")
                return {"success": False, "error": "User ID not found"}
            
            prefs = _read_json(PREFERENCES_PATH, {})
            comfyui_url = prefs.get('comfyUiServer', 'http://127.0.0.1:8188')
            comfyui_path = prefs.get('comfyuiPath')
            output_folder = prefs.get('aiWorkflowsOutputFolder')
            
            # Create callbacks that include user_id
            def update_state_cb(wf_id: str, updates: dict):
                _update_workflow_state(user_id, wf_id, updates)
            
            def get_state_cb(wf_id: str):
                return _get_workflow_state(user_id, wf_id)
            
            return execute_workflow(
                workflow=workflow,
                workflow_id=workflow_id,
                comfyui_url=comfyui_url,
                comfyui_path=comfyui_path,
                output_folder=output_folder,
                update_state_callback=update_state_cb,
                get_state_callback=get_state_cb,
                user_id=user_id
            )
        
        def get_prefs():
            return _read_json(PREFERENCES_PATH, {})
        
        scheduler = initialize_scheduler(
            get_workflows_callback=get_workflows,
            get_workflow_state_callback=get_state,
            update_workflow_state_callback=update_state,
            execute_workflow_callback=exec_workflow,
            get_preferences_callback=get_prefs
        )
        scheduler.start()
        print("Lifespan: Scheduler started, yielding control to FastAPI")
        
        yield
        
        # Shutdown
        print("Lifespan: Shutting down, stopping scheduler")
        scheduler = get_scheduler()
        if scheduler:
            scheduler.stop()
        else:
            print("Lifespan: Warning - scheduler instance not found during shutdown")
    except Exception as e:
        print(f"Lifespan error: {e}")
        import traceback
        traceback.print_exc()
        raise


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging to suppress access logs for /workflows/status, /workflows/sync, and /status/{prompt_id}
# We'll create a custom filter for uvicorn access logger
class SuppressStatusLogFilter(logging.Filter):
    def filter(self, record):
        message = str(record.getMessage())
        # Suppress logs for frequently polled endpoints
        return (
            "/workflows/status" not in message 
            and "/workflows/sync" not in message
            and "/status/" not in message  # Suppress /status/{prompt_id} endpoint logs
        )

# Apply the filter to uvicorn access logger
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.addFilter(SuppressStatusLogFilter())

# Suppress urllib3 DEBUG logs (connection pool logs)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)

# Configure logging level to DEBUG for our modules
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Set specific loggers to DEBUG
logging.getLogger("ai_agent").setLevel(logging.DEBUG)
logging.getLogger("workflow_executor").setLevel(logging.DEBUG)
logging.getLogger("workflow_scheduler").setLevel(logging.DEBUG)

# Create logger for this module
logger = logging.getLogger(__name__)


def _read_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


# Stored Workflows Management Functions (User-Scoped)
def _get_stored_workflows_metadata(user_id: str) -> dict:
    """Get metadata for all stored workflows for a specific user"""
    metadata_path = _get_user_stored_workflows_metadata_path(user_id)
    return _read_json(metadata_path, {"workflows": []})


def _save_stored_workflows_metadata(user_id: str, metadata: dict) -> None:
    """Save metadata for stored workflows for a specific user"""
    metadata_path = _get_user_stored_workflows_metadata_path(user_id)
    _write_json(metadata_path, metadata)


def _get_stored_workflow_file_path(user_id: str, workflow_id: str) -> str:
    """Get the file path for a stored workflow for a specific user"""
    user_dir = _get_user_stored_workflows_dir(user_id)
    return os.path.join(user_dir, f"{workflow_id}.json")


# ComfyUI Connection Error Detection
def _is_comfyui_connection_error(exception: Exception) -> bool:
    """Check if an exception indicates ComfyUI server is offline/not reachable"""
    error_str = str(exception).lower()
    error_type = type(exception).__name__
    
    # Check for connection-related error patterns
    connection_patterns = [
        "connection refused",
        "failed to establish a new connection",
        "max retries exceeded",
        "target machine actively refused",
        "actively refused",
        "httpconnectionpool",
        "newconnectionerror",
        "connectionerror",
        "connection aborted",
        "name or service not known",
        "nodename nor servname provided"
    ]
    
    # Check if error message contains any connection pattern
    for pattern in connection_patterns:
        if pattern in error_str:
            return True
    
    # Check exception type
    if "ConnectionError" in error_type or "ConnectionRefusedError" in error_type:
        return True
    
    # Check for requests library connection errors
    try:
        import requests
        if isinstance(exception, (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout)):
            return True
    except ImportError:
        pass
    
    return False


@app.get('/comfyui/test-connection')
def test_comfyui_connection(comfyui_url: Optional[str] = Query(default=None)):
    """Test ComfyUI server connection"""
    try:
        # Get ComfyUI URL from parameter or preferences
        if not comfyui_url:
            prefs = _read_json(PREFERENCES_PATH, {})
            comfyui_url = prefs.get('comfyUiServer', 'http://127.0.0.1:8188')
        
        # Test connection by attempting to get queue status
        client = ComfyUIClient(comfyui_url or "http://127.0.0.1:8188")
        queue_result = client.get_queue()
        
        return {
            "success": True,
            "message": "ComfyUI server is running and accessible",
            "comfyui_url": comfyui_url,
            "queue_info": queue_result
        }
    except Exception as e:
        is_offline = _is_comfyui_connection_error(e)
        return {
            "success": False,
            "message": f"Failed to connect to ComfyUI server: {str(e)}",
            "comfyui_url": comfyui_url or "http://127.0.0.1:8188",
            "isComfyUIOffline": is_offline,
            "error": str(e)
        }


@app.get('/preferences')
def get_preferences():
    return _read_json(PREFERENCES_PATH, {})


@app.post('/preferences')
def set_preferences(preferences: dict):
    _write_json(PREFERENCES_PATH, preferences)
    return {"ok": True}


@app.get('/history')
def get_history():
    return _read_json(HISTORY_PATH, [])


def _append_history(item: dict) -> None:
    history = _read_json(HISTORY_PATH, [])
    history.insert(0, item)
    _write_json(HISTORY_PATH, history)


# Workflow State Management Functions (User-Scoped)
def _get_workflow_state(user_id: str, workflow_id: str) -> dict:
    """Get state for a specific workflow for a specific user"""
    state_path = _get_user_workflow_state_path(user_id)
    state = _read_json(state_path, {})
    if workflow_id not in state:
        # Initialize with default state
        state[workflow_id] = {
            "isActive": False,
            "isRunning": False,
            "lastExecutionTime": None,
            "nextExecutionTime": None,
            "lastPromptId": None,
            "executionCount": 0,
            "executionPhase": None,  # "generating_prompts" or "executing_comfyui"
            "executionProgress": 0  # 0-100 percentage
        }
        _write_json(state_path, state)
    return state[workflow_id]


def _update_workflow_state(user_id: str, workflow_id: str, updates: dict) -> dict:
    """Update state for a specific workflow for a specific user"""
    state_path = _get_user_workflow_state_path(user_id)
    state = _read_json(state_path, {})
    if workflow_id not in state:
        _get_workflow_state(user_id, workflow_id)  # Initialize if needed
    
    state[workflow_id].update(updates)
    _write_json(state_path, state)
    return state[workflow_id]


def _get_all_workflow_states(user_id: str) -> dict:
    """Get states for all workflows for a specific user"""
    state_path = _get_user_workflow_state_path(user_id)
    return _read_json(state_path, {})


# AI Server Helper Functions
AI_API_BASE_URL = os.getenv('AI_API_BASE_URL', 'http://localhost:8001')


def _generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding for text using api-server API.
    
    Args:
        text: Text to generate embedding for
        
    Returns:
        Embedding vector as list of floats, or None on error
    """
    try:
        api_url = f"{AI_API_BASE_URL}/api/embeddings"
        response = requests.post(
            api_url,
            json={"text": text},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result.get("embedding")
    except Exception as e:
        logger.warning(f"Failed to generate embedding: {str(e)}")
        return None


def _generate_prompt_summary(prompts: List[str], concept: str) -> Optional[str]:
    """
    Generate summary of prompts using api-server API.
    
    Args:
        prompts: List of prompts to summarize
        concept: The concept for the prompts
        
    Returns:
        Summary string, or None on error
    """
    try:
        api_url = f"{AI_API_BASE_URL}/api/summarize-prompts"
        response = requests.post(
            api_url,
            json={"prompts": prompts, "concept": concept},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result.get("summary")
    except Exception as e:
        logger.warning(f"Failed to generate prompt summary: {str(e)}")
        return None


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Cosine similarity value between -1 and 1
    """
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must have the same length")
    
    # Calculate dot product
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    
    # Calculate magnitudes
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(a * a for a in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)


# Prompt History Management Functions
def _get_prompt_history(workflow_id: str) -> list:
    """Get prompt history for a specific workflow"""
    history = _read_json(PROMPT_HISTORY_PATH, {})
    return history.get(workflow_id, [])


def _save_prompt_history(workflow_id: str, prompts: list, concept: str) -> None:
    """Save new prompts to history for a workflow"""
    history = _read_json(PROMPT_HISTORY_PATH, {})
    
    if workflow_id not in history:
        history[workflow_id] = []
    
    # Generate summary and embedding
    summary = _generate_prompt_summary(prompts, concept)
    embedding = None
    if summary:
        # Generate embedding for concept + summary combined
        embedding_text = f"{concept}\n\n{summary}"
        embedding = _generate_embedding(embedding_text)
    
    # Create new entry
    entry = {
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "concept": concept,
        "prompts": prompts
    }
    
    # Add optional fields if available
    if summary:
        entry["summary"] = summary
    if embedding:
        entry["embedding"] = embedding
    
    # Add to history (most recent first)
    history[workflow_id].insert(0, entry)
    
    # Keep only last 10 entries per workflow (reduced from 20)
    if len(history[workflow_id]) > 10:
        history[workflow_id] = history[workflow_id][:10]
    
    _write_json(PROMPT_HISTORY_PATH, history)


def _get_relevant_prompts(workflow_id: str, concept: str, limit: int = 5) -> tuple:
    """
    Get relevant prompts using embeddings-based similarity search.
    
    Args:
        workflow_id: Workflow ID to get prompts for
        concept: Current concept to find similar prompts for
        limit: Maximum number of prompts to return (default: 5)
        
    Returns:
        Tuple of (prompts_list, summaries_list) where:
        - prompts_list: List of relevant prompts
        - summaries_list: List of summaries for those prompts (may be shorter if some entries lack summaries)
    """
    history = _get_prompt_history(workflow_id)
    
    if not history:
        return ([], [])
    
    # Generate embedding for current concept
    concept_embedding = _generate_embedding(concept)
    
    # If embedding generation failed, fallback to recent prompts
    if not concept_embedding:
        logger.warning("Failed to generate concept embedding, falling back to recent prompts")
        all_prompts = []
        summaries = []
        for entry in history[:limit]:
            if isinstance(entry, dict) and "prompts" in entry:
                all_prompts.extend(entry["prompts"])
                if "summary" in entry:
                    summaries.append(entry["summary"])
        return (all_prompts, summaries)
    
    # Calculate similarity for each entry with embedding
    entries_with_similarity = []
    for entry in history:
        if isinstance(entry, dict) and "prompts" in entry and "embedding" in entry:
            try:
                similarity = _cosine_similarity(concept_embedding, entry["embedding"])
                entries_with_similarity.append((similarity, entry))
            except Exception as e:
                logger.warning(f"Failed to calculate similarity for entry: {str(e)}")
                # Include entry with low similarity as fallback
                entries_with_similarity.append((0.0, entry))
        elif isinstance(entry, dict) and "prompts" in entry:
            # Entry without embedding - include with low priority
            entries_with_similarity.append((0.0, entry))
    
    # Sort by similarity (descending)
    entries_with_similarity.sort(key=lambda x: x[0], reverse=True)
    
    # Get top entries and flatten prompts
    all_prompts = []
    summaries = []
    for similarity, entry in entries_with_similarity[:limit]:
        if "prompts" in entry:
            all_prompts.extend(entry["prompts"])
        if "summary" in entry:
            summaries.append(entry["summary"])
    
    return (all_prompts, summaries)


def _get_recent_prompts(workflow_id: str, limit: int = 20) -> list:
    """
    Get recent prompts (flattened list) from history for a workflow.
    
    DEPRECATED: Use _get_relevant_prompts() instead for better relevance.
    Kept for backward compatibility.
    """
    history = _get_prompt_history(workflow_id)
    
    # Flatten all prompts from history entries
    all_prompts = []
    for entry in history[:limit]:
        if isinstance(entry, dict) and "prompts" in entry:
            all_prompts.extend(entry["prompts"])
    
    return all_prompts


# In-memory storage for workflows (synced from frontend) - User-scoped
_workflows_cache: Dict[str, List] = {}


def _set_workflows_cache(user_id: str, workflows: list):
    """Update the workflows cache for a specific user"""
    global _workflows_cache
    _workflows_cache[user_id] = workflows


def _get_workflows_cache(user_id: str) -> list:
    """Get the workflows cache for a specific user"""
    if user_id not in _workflows_cache:
        _workflows_cache[user_id] = []
    return _workflows_cache[user_id]


def _call_llm_to_generate_workflow(prompt: str, api_key: Optional[str]) -> str:
    # For MVP: return a simple instruction string; integrate OpenAI if key provided
    if api_key and OpenAI is not None:
        try:
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You output ComfyUI workflow JSON or high-level steps."},
                    {"role": "user", "content": f"Create a workflow for: {prompt}"},
                ],
                temperature=0.2,
            )
            return resp.choices[0].message.content or ""
        except Exception:
            pass
    return f"Generate an image based on: {prompt}"


def _queue_comfyui_workflow(
    workflow_json: dict, 
    prompt_text: str, 
    comfyui_url: str = "http://127.0.0.1:8188", 
    negative_prompt: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    steps: Optional[int] = None,
    cfg_scale: Optional[float] = None,
    fps: Optional[int] = None,
    length: Optional[int] = None,
    seed: Optional[int] = None
) -> dict:
    """Queue a ComfyUI workflow and return result dict with prompt_id and error info"""
    try:
        client = ComfyUIClient(comfyui_url)
        
        # Modify workflow to use the prompt text (positive and negative)
        modified_workflow = client.modify_workflow_prompt(workflow_json, prompt_text, negative_prompt)
        
        # Modify workflow dimensions and sampler settings (always call to ensure settings are updated)
        modified_workflow = client.modify_workflow_settings(modified_workflow, width, height, steps, cfg_scale, fps, length, seed)
        
        # For API format workflows, we need to extract the actual workflow data
        if 'workflow' in modified_workflow and isinstance(modified_workflow['workflow'], dict):
            # This is API format with 'workflow' property - extract the workflow data
            workflow_to_queue = modified_workflow['workflow']
        elif 'prompt' in modified_workflow and isinstance(modified_workflow['prompt'], dict):
            # This is ComfyUI's standard API format with 'prompt' property
            workflow_to_queue = modified_workflow['prompt']
        else:
            # This is original format - use as is
            workflow_to_queue = modified_workflow
        
        # Queue the prompt and return prompt_id immediately
        queue_result = client.queue_prompt(workflow_to_queue)
        prompt_id = queue_result["prompt_id"]
        
        return {
            "success": True,
            "prompt_id": prompt_id,
            "isComfyUIOffline": False
        }
            
    except Exception as e:
        is_offline = _is_comfyui_connection_error(e)
        return {
            "success": False,
            "error": str(e),
            "isComfyUIOffline": is_offline
        }


def _queue_comfyui_image_to_video(workflow_json: dict, image_data: bytes, image_filename: str, comfyui_url: str = "http://127.0.0.1:8188", comfyui_path: Optional[str] = None, positive_prompt: Optional[str] = None, negative_prompt: Optional[str] = None, fps: Optional[int] = None, steps: Optional[int] = None, length: Optional[int] = None, seed: Optional[int] = None) -> dict:
    """Queue a ComfyUI image-to-video workflow and return result dict with prompt_id and error info"""
    try:
        client = ComfyUIClient(comfyui_url)
        
        if not comfyui_path or not os.path.exists(comfyui_path):
            return {
                "success": False,
                "error": "ComfyUI path not configured. Please set ComfyUI folder path in settings.",
                "isComfyUIOffline": False
            }
        
        # Upload image to ComfyUI input directory
        input_dir = os.path.join(comfyui_path, 'ComfyUI', 'input')
        os.makedirs(input_dir, exist_ok=True)
        
        input_path = os.path.join(input_dir, image_filename)
        with open(input_path, 'wb') as f:
            f.write(image_data)
        
        print(f"Uploaded image to ComfyUI input: {input_path}")
        
        # First modify workflow to use the uploaded image
        modified_workflow = client.modify_workflow_image_input(workflow_json, image_data, image_filename)
        
        # Then modify prompts if provided
        if positive_prompt or negative_prompt:
            modified_workflow = client.modify_workflow_prompt(modified_workflow, positive_prompt or "", negative_prompt)
        
        # Modify workflow settings (fps, steps, length, seed)
        modified_workflow = client.modify_workflow_settings(modified_workflow, None, None, steps, None, fps, length, seed)
        
        # For API format workflows, we need to extract the actual workflow data
        if 'workflow' in modified_workflow and isinstance(modified_workflow['workflow'], dict):
            # This is API format with 'workflow' property - extract the workflow data
            workflow_to_queue = modified_workflow['workflow']
        elif 'prompt' in modified_workflow and isinstance(modified_workflow['prompt'], dict):
            # This is ComfyUI's standard API format with 'prompt' property
            workflow_to_queue = modified_workflow['prompt']
        else:
            # This is original format - use as is
            workflow_to_queue = modified_workflow
        
        # Queue the prompt and return prompt_id immediately
        queue_result = client.queue_prompt(workflow_to_queue)
        prompt_id = queue_result["prompt_id"]
        
        return {
            "success": True,
            "prompt_id": prompt_id,
            "isComfyUIOffline": False
        }
            
    except Exception as e:
        is_offline = _is_comfyui_connection_error(e)
        return {
            "success": False,
            "error": str(e),
            "isComfyUIOffline": is_offline
        }


def _get_comfyui_result(prompt_id: str, comfyui_url: str = "http://127.0.0.1:8188", comfyui_path: Optional[str] = None) -> dict:
    """Get the result of a completed ComfyUI workflow - returns path to file"""
    try:
        client = ComfyUIClient(comfyui_url)
        
        # Wait for completion - use simple polling instead of WebSocket
        import time
        timeout = 300  # 5 minutes
        start_time = time.time()
        result = None
        
        while time.time() - start_time < timeout:
            try:
                history = client.get_history(prompt_id)
                if prompt_id in history:
                    # Execution completed, get the result from history
                    prompt_data = history[prompt_id]
                    outputs = prompt_data.get("outputs", {})
                    
                    result = {
                        "prompt_id": prompt_id,
                        "status": "completed",
                        "outputs": outputs,
                        "images": []
                    }
                    
                    # Extract image information
                    for node_id, node_output in outputs.items():
                        if "images" in node_output:
                            for img_info in node_output["images"]:
                                result["images"].append({
                                    "filename": img_info["filename"],
                                    "subfolder": img_info.get("subfolder", ""),
                                    "type": img_info.get("type", "output")
                                })
                    break
                time.sleep(2)  # Poll every 2 seconds
            except Exception as e:
                print(f"Polling error: {e}")
                time.sleep(2)
        
        if not result:
            raise TimeoutError(f"ComfyUI execution timed out after {timeout} seconds")
        
        # Extract output file information
        if result.get("images") and len(result["images"]) > 0:
            output_info = result["images"][0]  # Get first output
            filename = output_info.get("filename")
            subfolder = output_info.get("subfolder", "")
            
            if not filename:
                raise Exception("Output image has no filename")
            
            # Return the filename and subfolder - simple approach
            if comfyui_path and os.path.exists(comfyui_path):
                # Construct path to ComfyUI output directory
                comfyui_output_dir = os.path.join(comfyui_path, "ComfyUI", "output")
                if subfolder:
                    comfyui_output_dir = os.path.join(comfyui_output_dir, subfolder)
                
                source_path = os.path.join(comfyui_output_dir, filename)
                
                if os.path.exists(source_path):
                    # Return just the filename - server will handle the path
                    return {
                        "filename": filename,
                        "subfolder": subfolder
                    }
                else:
                    raise Exception(f"ComfyUI output file not found at {source_path}")
            
            # If no ComfyUI path provided, throw error - user must configure ComfyUI path
            raise Exception("ComfyUI path not configured. Please set ComfyUI folder path in settings. Go to Settings page and click 'Select ComfyUI Folder'.")
        else:
            raise Exception(f"No output generated. Result structure: {result}")
            
    except Exception as e:
        import traceback
        print(f"ERROR in _get_comfyui_result: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise e


@app.post('/generate_image')
async def generate_image(
    workflow_file: UploadFile = File(...),
    prompt: str = Form(...),
    negative_prompt: str = Form(default=""),
    width: str = Form(default=""),
    height: str = Form(default=""),
    steps: str = Form(default=""),
    cfg_scale: str = Form(default=""),
    seed: str = Form(default=""),
    comfyui_url: str = Form(default="http://127.0.0.1:8188")
):
    """Queue an image generation workflow and return prompt_id immediately"""
    try:
        print(f"Received parameters: width='{width}', height='{height}', steps='{steps}', cfg_scale='{cfg_scale}', seed='{seed}'")
        
        # Read workflow file
        workflow_content = await workflow_file.read()
        workflow_json = json.loads(workflow_content.decode('utf-8'))
        
        # Parse and validate numeric parameters
        width_int = None
        height_int = None
        steps_int = None
        cfg_scale_float = None
        seed_int = None
        
        try:
            if width and width.strip():
                width_int = int(width)
        except ValueError:
            pass
        
        try:
            if height and height.strip():
                height_int = int(height)
        except ValueError:
            pass
        
        try:
            if steps and steps.strip():
                steps_int = int(steps)
        except ValueError:
            pass
        
        try:
            if cfg_scale and cfg_scale.strip():
                cfg_scale_float = float(cfg_scale)
        except ValueError:
            pass
        
        try:
            if seed and seed.strip():
                seed_int = int(seed)
        except ValueError:
            pass
        
        print(f"Parsed parameters: width={width_int}, height={height_int}, steps={steps_int}, cfg_scale={cfg_scale_float}, seed={seed_int}")
        
        # Queue workflow and get result
        queue_result = _queue_comfyui_workflow(
            workflow_json, 
            prompt, 
            comfyui_url, 
            negative_prompt if negative_prompt else None,
            width_int,
            height_int,
            steps_int,
            cfg_scale_float,
            None,  # fps
            None,  # length
            seed_int
        )
        
        if queue_result.get('success'):
            return {
                'success': True,
                'prompt_id': queue_result['prompt_id'],
                'message': 'Image generation started'
            }
        else:
            return {
                'success': False,
                'error': queue_result.get('error', 'Unknown error'),
                'message': 'Failed to start image generation',
                'isComfyUIOffline': queue_result.get('isComfyUIOffline', False)
            }
        
    except Exception as e:
        is_offline = _is_comfyui_connection_error(e)
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to start image generation',
            'isComfyUIOffline': is_offline
        }


@app.post('/generate_video')
async def generate_video(
    workflow_file: UploadFile = File(...),
    prompt: str = Form(...),
    negative_prompt: str = Form(default=""),
    width: str = Form(default=""),
    height: str = Form(default=""),
    fps: str = Form(default=""),
    steps: str = Form(default=""),
    length: str = Form(default=""),
    seed: str = Form(default=""),
    comfyui_url: str = Form(default="http://127.0.0.1:8188")
):
    """Queue a video generation workflow and return prompt_id immediately"""
    try:
        # Read workflow file
        workflow_content = await workflow_file.read()
        workflow_json = json.loads(workflow_content.decode('utf-8'))
        
        # Parse and validate numeric parameters
        width_int = None
        height_int = None
        fps_int = None
        steps_int = None
        length_int = None
        seed_int = None
        
        try:
            if width and width.strip():
                width_int = int(width)
        except ValueError:
            pass
        
        try:
            if height and height.strip():
                height_int = int(height)
        except ValueError:
            pass
        
        try:
            if fps and fps.strip():
                fps_int = int(fps)
        except ValueError:
            pass
        
        try:
            if steps and steps.strip():
                steps_int = int(steps)
        except ValueError:
            pass
        
        try:
            if length and length.strip():
                length_int = int(length)
        except ValueError:
            pass
        
        try:
            if seed and seed.strip():
                seed_int = int(seed)
        except ValueError:
            pass
        
        print(f"Parsed video parameters: width={width_int}, height={height_int}, fps={fps_int}, steps={steps_int}, length={length_int}, seed={seed_int}")
        
        # Queue workflow and get result
        queue_result = _queue_comfyui_workflow(
            workflow_json, 
            prompt, 
            comfyui_url, 
            negative_prompt if negative_prompt else None,
            width_int,
            height_int,
            steps_int,
            None,  # cfg_scale
            fps_int,
            length_int,
            seed_int
        )
        
        if queue_result.get('success'):
            return {
                'success': True,
                'prompt_id': queue_result['prompt_id'],
                'message': 'Video generation started'
            }
        else:
            return {
                'success': False,
                'error': queue_result.get('error', 'Unknown error'),
                'message': 'Failed to start video generation',
                'isComfyUIOffline': queue_result.get('isComfyUIOffline', False)
            }
        
    except Exception as e:
        is_offline = _is_comfyui_connection_error(e)
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to start video generation',
            'isComfyUIOffline': is_offline
        }


@app.post('/generate_image_to_video')
async def generate_image_to_video(
    workflow_file: UploadFile = File(...),
    image_file: UploadFile = File(...),
    positive_prompt: str = Form(default=""),
    negative_prompt: str = Form(default=""),
    fps: str = Form(default=""),
    steps: str = Form(default=""),
    length: str = Form(default=""),
    seed: str = Form(default=""),
    comfyui_url: str = Form(default="http://127.0.0.1:8188"),
    comfyui_path: str = Form(default=None)
):
    """Queue an image-to-video generation workflow and return prompt_id immediately"""
    try:
        # Read workflow file
        workflow_content = await workflow_file.read()
        workflow_json = json.loads(workflow_content.decode('utf-8'))
        
        # Read image file
        image_content = await image_file.read()
        
        # Parse and validate numeric parameters
        fps_int = None
        steps_int = None
        length_int = None
        seed_int = None
        
        try:
            if fps and fps.strip():
                fps_int = int(fps)
        except ValueError:
            pass
        
        try:
            if steps and steps.strip():
                steps_int = int(steps)
        except ValueError:
            pass
        
        try:
            if length and length.strip():
                length_int = int(length)
        except ValueError:
            pass
        
        try:
            if seed and seed.strip():
                seed_int = int(seed)
        except ValueError:
            pass
        
        print(f"Parsed image-to-video parameters: fps={fps_int}, steps={steps_int}, length={length_int}, seed={seed_int}")
        
        # Ensure filename is not None (provide default if missing)
        image_filename = image_file.filename or "image.png"
        
        # Queue workflow and get result
        queue_result = _queue_comfyui_image_to_video(
            workflow_json, 
            image_content, 
            image_filename, 
            comfyui_url,
            comfyui_path,
            positive_prompt if positive_prompt else None,
            negative_prompt if negative_prompt else None,
            fps_int,
            steps_int,
            length_int,
            seed_int
        )
        
        if queue_result.get('success'):
            return {
                'success': True,
                'prompt_id': queue_result['prompt_id'],
                'message': 'Image-to-video generation started'
            }
        else:
            return {
                'success': False,
                'error': queue_result.get('error', 'Unknown error'),
                'message': 'Failed to start image-to-video generation',
                'isComfyUIOffline': queue_result.get('isComfyUIOffline', False)
            }
        
    except Exception as e:
        is_offline = _is_comfyui_connection_error(e)
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to start image-to-video generation',
            'isComfyUIOffline': is_offline
        }


@app.get('/status/{prompt_id}')
def get_generation_status(prompt_id: str, comfyui_url: str = Query(default="http://127.0.0.1:8188")):
    """Get the current status of a generation request"""
    try:
        client = ComfyUIClient(comfyui_url)
        progress_info = client.get_prompt_progress(prompt_id)
        
        # Ensure progress_info is not None and is a dict
        if not progress_info or not isinstance(progress_info, dict):
            return {
                'success': False,
                'prompt_id': prompt_id,
                'status': 'error',
                'progress': 0,
                'message': 'Failed to get progress information'
            }
        
        return {
            'success': True,
            'prompt_id': prompt_id,
            'status': progress_info.get('status', 'unknown'),
            'progress': progress_info.get('progress', 0),
            'message': progress_info.get('message', 'Unknown status')
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Error checking status for prompt {prompt_id}: {e}")
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'prompt_id': prompt_id,
            'status': 'error',
            'progress': 0,
            'message': f'Error checking status: {str(e)}'
        }


@app.get('/result/{prompt_id}')
def get_generation_result(
    prompt_id: str, 
    comfyui_url: str = Query(default="http://127.0.0.1:8188"),
    comfyui_path: Optional[str] = Query(default=None)
):
    """Get the result of a completed generation request"""
    try:
        # Get the result info (returns dict with filename and subfolder)
        result_info = _get_comfyui_result(prompt_id, comfyui_url, comfyui_path)
        print(f"Result info: {result_info}")
        print(f"Result info type: {type(result_info)}")
        
        # Extract filename and subfolder from the result
        if not isinstance(result_info, dict):
            raise Exception(f"Unexpected result format: {result_info}")
        
        filename = result_info.get("filename")
        subfolder = result_info.get("subfolder", "")
        
        print(f"Extracted filename: {filename}, subfolder: {subfolder}")
        
        if not filename:
            raise Exception("No filename returned from ComfyUI result")
        
        # Return the filename and subfolder - client will construct simple URL
        result_data = {
            'filename': filename,
            'subfolder': subfolder
        }
        
        # Add to history
        item = {
            'id': uuid.uuid4().hex,
            'type': 'generation_result',
            'prompt_id': prompt_id,
            'filename': filename,
            'subfolder': subfolder,
            'createdAt': datetime.utcnow().isoformat() + 'Z',
        }
        _append_history(item)
        
        return {
            'success': True,
            'prompt_id': prompt_id,
            'filename': filename,
            'subfolder': subfolder,
            'message': 'Generation completed successfully'
        }
        
    except Exception as e:
        return {
            'success': False,
            'prompt_id': prompt_id,
            'error': str(e),
            'message': 'Failed to get generation result'
        }


@app.get('/comfyui-file')
def get_comfyui_file(
    filename: str = Query(..., description="Filename from ComfyUI output"),
    subfolder: str = Query(default="", description="Subfolder from ComfyUI output"),
    comfyui_path: str = Query(default=None, description="ComfyUI folder path")
):
    """Serve files from ComfyUI output directory"""
    if not comfyui_path:
        return {"error": "ComfyUI path not provided"}
    
    try:
        # Construct path to ComfyUI output directory
        comfyui_output_dir = os.path.join(comfyui_path, "ComfyUI", "output")
        if subfolder:
            comfyui_output_dir = os.path.join(comfyui_output_dir, subfolder)
        
        file_path = os.path.join(comfyui_output_dir, filename)
        
        print(f"Serving file from: {file_path}")
        
        if os.path.exists(file_path) and os.path.isfile(file_path):
            # Determine media type based on file extension
            if filename.lower().endswith('.mp4') or filename.lower().endswith('.webm'):
                from fastapi.responses import Response
                with open(file_path, 'rb') as f:
                    content = f.read()
                return Response(content=content, media_type="video/mp4")
            elif filename.lower().endswith('.png'):
                return FileResponse(file_path, media_type="image/png")
            elif filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
                return FileResponse(file_path, media_type="image/jpeg")
            else:
                return FileResponse(file_path)
        else:
            print(f"File not found at: {file_path}")
            return {"error": f"File not found: {file_path}"}
    except Exception as e:
        print(f"Error serving file: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {"error": str(e)}


# Stored Workflows API Endpoints
@app.get('/stored-workflows')
def get_stored_workflows(request: Request):
    """List all stored workflows with metadata for the current user"""
    try:
        user_id = _get_user_id_from_request(request)
        if not user_id:
            return {
                "success": False,
                "error": "User ID required"
            }
        
        metadata = _get_stored_workflows_metadata(user_id)
        # Filter to only include workflows with matching userId in metadata
        workflows = [w for w in metadata.get("workflows", []) if w.get("userId") == user_id]
        return {
            "success": True,
            "workflows": workflows
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post('/stored-workflows')
async def save_stored_workflow(
    request: Request,
    workflow_file: UploadFile = File(...),
    name: str = Form(default=""),
    description: str = Form(default="")
):
    """Save a new workflow for the current user"""
    try:
        user_id = _get_user_id_from_request(request)
        if not user_id:
            return {
                "success": False,
                "error": "User ID required"
            }
        
        # Read workflow file
        workflow_content = await workflow_file.read()
        workflow_json = json.loads(workflow_content.decode('utf-8'))
        
        # Generate unique ID
        workflow_id = uuid.uuid4().hex
        
        # Use provided name or fall back to filename
        workflow_name = name.strip() if name.strip() else workflow_file.filename or f"Workflow {workflow_id[:8]}"
        
        # Save workflow file
        workflow_path = _get_stored_workflow_file_path(user_id, workflow_id)
        with open(workflow_path, 'w', encoding='utf-8') as f:
            json.dump(workflow_json, f, indent=2)
        
        # Create metadata entry
        now = datetime.utcnow().isoformat() + 'Z'
        workflow_metadata = {
            "id": workflow_id,
            "name": workflow_name,
            "description": description.strip(),
            "filename": workflow_file.filename or "workflow.json",
            "uploadDate": now,
            "lastUsed": None,
            "fileSize": len(workflow_content),
            "userId": user_id  # Store userId in metadata
        }
        
        # Add to metadata
        metadata = _get_stored_workflows_metadata(user_id)
        metadata["workflows"].append(workflow_metadata)
        _save_stored_workflows_metadata(user_id, metadata)
        
        return {
            "success": True,
            "workflow": workflow_metadata
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.get('/stored-workflows/{workflow_id}')
def get_stored_workflow(workflow_id: str, request: Request):
    """Retrieve a specific workflow JSON file for the current user"""
    try:
        user_id = _get_user_id_from_request(request)
        if not user_id:
            return {
                "success": False,
                "error": "User ID required"
            }
        
        metadata = _get_stored_workflows_metadata(user_id)
        workflow_meta = next((w for w in metadata.get("workflows", []) if w["id"] == workflow_id and w.get("userId") == user_id), None)
        
        if not workflow_meta:
            return {
                "success": False,
                "error": "Workflow not found"
            }
        
        # Read workflow file
        workflow_path = _get_stored_workflow_file_path(user_id, workflow_id)
        if not os.path.exists(workflow_path):
            return {
                "success": False,
                "error": "Workflow file not found"
            }
        
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow_json = json.load(f)
        
        return {
            "success": True,
            "workflow": workflow_json,
            "metadata": workflow_meta
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.put('/stored-workflows/{workflow_id}')
def update_stored_workflow(
    workflow_id: str,
    request: Request,
    updates: dict = Body(...)
):
    """Update workflow metadata (name, description) for the current user"""
    try:
        user_id = _get_user_id_from_request(request)
        if not user_id:
            return {
                "success": False,
                "error": "User ID required"
            }
        
        metadata = _get_stored_workflows_metadata(user_id)
        workflows = metadata.get("workflows", [])
        
        workflow_index = next((i for i, w in enumerate(workflows) if w["id"] == workflow_id and w.get("userId") == user_id), None)
        
        if workflow_index is None:
            return {
                "success": False,
                "error": "Workflow not found"
            }
        
        # Update metadata
        if "name" in updates and updates["name"] is not None:
            workflows[workflow_index]["name"] = str(updates["name"]).strip()
        if "description" in updates and updates["description"] is not None:
            workflows[workflow_index]["description"] = str(updates["description"]).strip()
        
        metadata["workflows"] = workflows
        _save_stored_workflows_metadata(user_id, metadata)
        
        return {
            "success": True,
            "workflow": workflows[workflow_index]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.delete('/stored-workflows/{workflow_id}')
def delete_stored_workflow(workflow_id: str, request: Request):
    """Delete a stored workflow for the current user"""
    try:
        user_id = _get_user_id_from_request(request)
        if not user_id:
            return {
                "success": False,
                "error": "User ID required"
            }
        
        metadata = _get_stored_workflows_metadata(user_id)
        workflows = metadata.get("workflows", [])
        
        workflow_index = next((i for i, w in enumerate(workflows) if w["id"] == workflow_id and w.get("userId") == user_id), None)
        
        if workflow_index is None:
            return {
                "success": False,
                "error": "Workflow not found"
            }
        
        # Remove from metadata
        workflows.pop(workflow_index)
        metadata["workflows"] = workflows
        _save_stored_workflows_metadata(user_id, metadata)
        
        # Delete workflow file
        workflow_path = _get_stored_workflow_file_path(user_id, workflow_id)
        if os.path.exists(workflow_path):
            os.remove(workflow_path)
        
        return {
            "success": True,
            "message": "Workflow deleted"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post('/stored-workflows/{workflow_id}/use')
def mark_workflow_used(workflow_id: str, request: Request):
    """Mark workflow as used (update lastUsed timestamp) for the current user"""
    try:
        user_id = _get_user_id_from_request(request)
        if not user_id:
            return {
                "success": False,
                "error": "User ID required"
            }
        
        metadata = _get_stored_workflows_metadata(user_id)
        workflows = metadata.get("workflows", [])
        
        workflow_index = next((i for i, w in enumerate(workflows) if w["id"] == workflow_id and w.get("userId") == user_id), None)
        
        if workflow_index is None:
            return {
                "success": False,
                "error": "Workflow not found"
            }
        
        # Update lastUsed timestamp
        now = datetime.utcnow().isoformat() + 'Z'
        workflows[workflow_index]["lastUsed"] = now
        
        metadata["workflows"] = workflows
        _save_stored_workflows_metadata(user_id, metadata)
        
        return {
            "success": True,
            "workflow": workflows[workflow_index]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }




# Workflow API Endpoints
@app.post('/workflows/sync')
def sync_workflows(request: Request, workflows: list = Body(...)):
    """Sync workflow list from frontend for the current user to in-memory cache only.
    
    NOTE: This endpoint does NOT auto-save workflow files to stored workflows.
    Users must explicitly save workflow files using the "Save" button in WorkflowFileUpload component.
    """
    user_id = _get_user_id_from_request(request)
    if not user_id:
        return {"ok": False, "error": "User ID required"}
    
    # Filter workflows to ensure they belong to the user
    user_workflows = [w for w in workflows if w.get("userId") == user_id]
    
    # Save to in-memory cache only
    # NOTE: We do NOT auto-save workflow files to stored workflows here.
    # Users must explicitly save workflow files using the "Save" button in WorkflowFileUpload component.
    # Auto-saving was causing workflow files to be saved with AI workflow names instead of original filenames.
    _set_workflows_cache(user_id, user_workflows)
    
    return {"ok": True, "count": len(user_workflows)}


@app.post('/workflows/{workflow_id}/activate')
def activate_workflow(workflow_id: str, request: Request):
    """Activate a workflow and start immediate execution for the current user"""
    try:
        user_id = _get_user_id_from_request(request)
        if not user_id:
            return {
                "success": False,
                "error": "User ID required"
            }
        
        # Check subscription before activating
        try:
            api_base_url = os.getenv('AI_API_BASE_URL', 'http://localhost:8001')
            check_response = requests.post(
                f"{api_base_url}/api/subscription/check-execution-internal",
                json={"user_id": user_id},
                headers={
                    "Content-Type": "application/json"
                },
                timeout=5
            )
            
            if check_response.status_code == 200:
                check_data = check_response.json()
                if not check_data.get("can_execute", False):
                    return {
                        "success": False,
                        "error": check_data.get("message", "Subscription limit reached"),
                        "subscription_error": True
                    }
            elif check_response.status_code == 403:
                # Subscription check failed
                error_data = check_response.json() if check_response.headers.get("content-type", "").startswith("application/json") else {}
                return {
                    "success": False,
                    "error": error_data.get("detail", "Subscription limit reached"),
                    "subscription_error": True
                }
        except Exception as e:
            # If subscription check fails, log but continue (for development/testing)
            print(f"Warning: Subscription check failed: {e}")
            # In production, you might want to fail here
            # return {
            #     "success": False,
            #     "error": "Unable to verify subscription. Please try again."
            # }
        
        state = _get_workflow_state(user_id, workflow_id)
        
        # Only activate if not already running
        if state.get('isRunning', False):
            return {
                "success": False,
                "error": "Cannot activate workflow that is currently running"
            }
        
        # Find workflow to get schedule (verify it belongs to user)
        workflows = _get_workflows_cache(user_id)
        workflow = next((w for w in workflows if w.get('id') == workflow_id and w.get('userId') == user_id), None)
        
        if not workflow:
            return {
                "success": False,
                "error": "Workflow not found"
            }
        
        # Set workflow to active, set isRunning=True immediately to prevent scheduler from executing,
        # and set nextExecutionTime to None for first execution
        _update_workflow_state(user_id, workflow_id, {
            "isActive": True,
            "isRunning": True,  # Set immediately to prevent scheduler from executing
            "nextExecutionTime": None  # Set to None so first execution happens immediately
        })
        
        # Get ComfyUI settings
        prefs = _read_json(PREFERENCES_PATH, {})
        comfyui_url = prefs.get('comfyUiServer', 'http://127.0.0.1:8188')
        comfyui_path = prefs.get('comfyuiPath')
        output_folder = prefs.get('aiWorkflowsOutputFolder')
        
        # Create callbacks that include user_id
        def update_state_cb(wf_id: str, updates: dict):
            _update_workflow_state(user_id, wf_id, updates)
        
        def get_state_cb(wf_id: str):
            return _get_workflow_state(user_id, wf_id)
        
        # Execute immediately in background thread
        import threading
        def execute():
            try:
                result = execute_workflow(
                    workflow=workflow,
                    workflow_id=workflow_id,
                    comfyui_url=comfyui_url,
                    comfyui_path=comfyui_path,
                    output_folder=output_folder,
                    update_state_callback=update_state_cb,
                    get_state_callback=get_state_cb,
                    user_id=user_id
                )
                
                # Increment execution count after successful execution
                if result.get("success"):
                    try:
                        api_base_url = os.getenv('AI_API_BASE_URL', 'http://localhost:8001')
                        increment_response = requests.post(
                            f"{api_base_url}/api/subscription/increment-execution-internal",
                            json={"user_id": user_id},
                            headers={
                                "Content-Type": "application/json"
                            },
                            timeout=5
                        )
                        if increment_response.status_code != 200:
                            print(f"Warning: Failed to increment execution count: {increment_response.status_code}")
                    except Exception as e:
                        print(f"Warning: Error incrementing execution count: {e}")
            except Exception as e:
                print(f"Workflow activation execution error: {e}")
                import traceback
                traceback.print_exc()
                _update_workflow_state(user_id, workflow_id, {"isRunning": False})
        
        thread = threading.Thread(target=execute, daemon=True)
        thread.start()
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "message": "Workflow activated and execution started"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post('/workflows/deactivate-all')
def deactivate_all_workflows(request: Request):
    """Deactivate all active workflows for the current user"""
    try:
        user_id = _get_user_id_from_request(request)
        if not user_id:
            return {
                "success": False,
                "error": "User ID required"
            }
        
        # Get all workflow states for user
        states = _get_all_workflow_states(user_id)
        deactivated_count = 0
        
        # Deactivate all active workflows
        for workflow_id, state in states.items():
            if state.get('isActive', False):
                _update_workflow_state(user_id, workflow_id, {
                    "isActive": False
                })
                deactivated_count += 1
        
        return {
            "success": True,
            "message": f"Deactivated {deactivated_count} workflow(s)",
            "count": deactivated_count
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post('/workflows/{workflow_id}/deactivate')
def deactivate_workflow(workflow_id: str, request: Request):
    """Deactivate a workflow (will stop scheduling after current execution finishes) for the current user"""
    try:
        user_id = _get_user_id_from_request(request)
        if not user_id:
            return {
                "success": False,
                "error": "User ID required"
            }
        
        # Verify workflow belongs to user
        workflows = _get_workflows_cache(user_id)
        workflow = next((w for w in workflows if w.get('id') == workflow_id and w.get('userId') == user_id), None)
        if not workflow:
            return {
                "success": False,
                "error": "Workflow not found"
            }
        
        _update_workflow_state(user_id, workflow_id, {
            "isActive": False
        })
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "message": "Workflow deactivated (current execution will finish)"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post('/workflows/{workflow_id}/cancel')
def cancel_workflow(workflow_id: str, request: Request):
    """Cancel a currently running workflow execution"""
    try:
        user_id = _get_user_id_from_request(request)
        if not user_id:
            return {
                "success": False,
                "error": "User ID required"
            }
        
        state = _get_workflow_state(user_id, workflow_id)
        
        if not state.get('isRunning', False):
            return {
                "success": False,
                "error": "Workflow is not currently running"
            }
        
        # Calculate next execution time based on schedule to prevent immediate re-execution
        workflows = _get_workflows_cache(user_id)
        workflow = next((w for w in workflows if w.get('id') == workflow_id and w.get('userId') == user_id), None)
        if not workflow:
            return {
                "success": False,
                "error": "Workflow not found"
            }
        schedule_minutes = workflow.get('schedule', 60)
        
        from datetime import timedelta
        next_execution = (datetime.utcnow() + timedelta(minutes=schedule_minutes)).isoformat() + 'Z'
        
        # Set cancellation flag, stop running, and set next execution time
        _update_workflow_state(user_id, workflow_id, {
            "isRunning": False,
            "cancelled": True,
            "nextExecutionTime": next_execution  # Prevent immediate re-execution
        })
        
        # Interrupt ComfyUI execution
        try:
            prefs = _read_json(PREFERENCES_PATH, {})
            comfyui_url = prefs.get('comfyUiServer', 'http://127.0.0.1:8188')
            client = ComfyUIClient(comfyui_url)
            client.interrupt()
        except Exception as e:
            # Log but don't fail - the state is already updated
            logger.warning(f"Failed to interrupt ComfyUI: {str(e)}")
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "message": "Workflow execution cancelled"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.get('/workflows/{workflow_id}/status')
def get_workflow_status(workflow_id: str, request: Request):
    """Get status for a specific workflow for the current user"""
    try:
        user_id = _get_user_id_from_request(request)
        if not user_id:
            return {
                "success": False,
                "error": "User ID required"
            }
        
        state = _get_workflow_state(user_id, workflow_id)
        return {
            "success": True,
            "workflow_id": workflow_id,
            "state": state
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.get('/workflows/status')
def get_all_workflows_status(request: Request):
    """Get status for all workflows for the current user"""
    try:
        user_id = _get_user_id_from_request(request)
        if not user_id:
            return {
                "success": False,
                "error": "User ID required"
            }
        
        states = _get_all_workflow_states(user_id)
        return {
            "success": True,
            "states": states
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post('/workflows/{workflow_id}/execute')
def execute_workflow_manual(workflow_id: str, request: Request):
    """Manually execute a workflow (for testing, bypasses schedule) for the current user"""
    try:
        user_id = _get_user_id_from_request(request)
        if not user_id:
            return {
                "success": False,
                "error": "User ID required"
            }
        
        # Find workflow (verify it belongs to user)
        workflows = _get_workflows_cache(user_id)
        workflow = next((w for w in workflows if w.get('id') == workflow_id and w.get('userId') == user_id), None)
        
        if not workflow:
            return {
                "success": False,
                "error": "Workflow not found"
            }
        
        state = _get_workflow_state(user_id, workflow_id)
        if state.get('isRunning', False):
            return {
                "success": False,
                "error": "Workflow is already running"
            }
        
        # Get ComfyUI settings
        prefs = _read_json(PREFERENCES_PATH, {})
        comfyui_url = prefs.get('comfyUiServer', 'http://127.0.0.1:8188')
        comfyui_path = prefs.get('comfyuiPath')
        output_folder = prefs.get('aiWorkflowsOutputFolder')
        
        # Create callbacks that include user_id
        def update_state_cb(wf_id: str, updates: dict):
            _update_workflow_state(user_id, wf_id, updates)
        
        def get_state_cb(wf_id: str):
            return _get_workflow_state(user_id, wf_id)
        
        # Execute in background
        import threading
        def execute():
            try:
                execute_workflow(
                    workflow=workflow,
                    workflow_id=workflow_id,
                    comfyui_url=comfyui_url,
                    comfyui_path=comfyui_path,
                    output_folder=output_folder,
                    update_state_callback=update_state_cb,
                    get_state_callback=get_state_cb,
                    user_id=user_id
                )
            except Exception as e:
                print(f"Manual execution error: {e}")
                _update_workflow_state(user_id, workflow_id, {"isRunning": False})
        
        thread = threading.Thread(target=execute, daemon=True)
        thread.start()
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "message": "Workflow execution started"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.get('/workflows/{workflow_id}/prompt-history')
def get_prompt_history(workflow_id: str):
    """Get prompt history for a specific workflow"""
    try:
        history = _get_prompt_history(workflow_id)
        return {
            "success": True,
            "workflow_id": workflow_id,
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.delete('/workflows/{workflow_id}/prompt-history')
def clear_prompt_history(workflow_id: str):
    """Clear prompt history for a specific workflow"""
    try:
        history = _read_json(PROMPT_HISTORY_PATH, {})
        if workflow_id in history:
            del history[workflow_id]
            _write_json(PROMPT_HISTORY_PATH, history)
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "message": "Prompt history cleared"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8000)


