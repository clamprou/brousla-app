import os
import json
import uuid
import asyncio
import base64
import shutil
import traceback
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Query, UploadFile, File, Form, Body
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn

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

PREFERENCES_PATH = os.path.join(DATA_DIR, 'preferences.json')
HISTORY_PATH = os.path.join(DATA_DIR, 'history.json')
WORKFLOW_STATE_PATH = os.path.join(DATA_DIR, 'workflow_state.json')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(WORKFLOWS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)


# Lifespan event handlers (replaces deprecated on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup workflow scheduler"""
    try:
        # Startup
        def get_workflows():
            return _get_workflows_cache()
        
        def get_state(workflow_id: str):
            return _get_workflow_state(workflow_id)
        
        def update_state(workflow_id: str, updates: dict):
            _update_workflow_state(workflow_id, updates)
        
        def exec_workflow(workflow: dict, workflow_id: str):
            """Execute workflow with current ComfyUI settings"""
            prefs = _read_json(PREFERENCES_PATH, {})
            comfyui_url = prefs.get('comfyUiServer', 'http://127.0.0.1:8188')
            comfyui_path = prefs.get('comfyuiPath')
            return execute_workflow(
                workflow=workflow,
                workflow_id=workflow_id,
                comfyui_url=comfyui_url,
                comfyui_path=comfyui_path,
                update_state_callback=update_state
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

# Configure logging to suppress access logs for /workflows/status and /workflows/sync
# We'll create a custom filter for uvicorn access logger
class SuppressStatusLogFilter(logging.Filter):
    def filter(self, record):
        message = str(record.getMessage())
        # Suppress logs for frequently polled endpoints
        return "/workflows/status" not in message and "/workflows/sync" not in message

# Apply the filter to uvicorn access logger
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.addFilter(SuppressStatusLogFilter())


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


# Workflow State Management Functions
def _get_workflow_state(workflow_id: str) -> dict:
    """Get state for a specific workflow"""
    state = _read_json(WORKFLOW_STATE_PATH, {})
    if workflow_id not in state:
        # Initialize with default state
        state[workflow_id] = {
            "isActive": False,
            "isRunning": False,
            "lastExecutionTime": None,
            "nextExecutionTime": None,
            "lastPromptId": None,
            "executionCount": 0
        }
        _write_json(WORKFLOW_STATE_PATH, state)
    return state[workflow_id]


def _update_workflow_state(workflow_id: str, updates: dict) -> dict:
    """Update state for a specific workflow"""
    state = _read_json(WORKFLOW_STATE_PATH, {})
    if workflow_id not in state:
        _get_workflow_state(workflow_id)  # Initialize if needed
    
    state[workflow_id].update(updates)
    _write_json(WORKFLOW_STATE_PATH, state)
    return state[workflow_id]


def _get_all_workflow_states() -> dict:
    """Get states for all workflows"""
    return _read_json(WORKFLOW_STATE_PATH, {})


# In-memory storage for workflows (synced from frontend)
_workflows_cache = []


def _set_workflows_cache(workflows: list):
    """Update the workflows cache"""
    global _workflows_cache
    _workflows_cache = workflows


def _get_workflows_cache() -> list:
    """Get the workflows cache"""
    return _workflows_cache


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
) -> str:
    """Queue a ComfyUI workflow and return the prompt_id immediately"""
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
        
        return prompt_id
            
    except Exception as e:
        raise Exception(f"Failed to queue ComfyUI workflow: {str(e)}")


def _queue_comfyui_image_to_video(workflow_json: dict, image_data: bytes, image_filename: str, comfyui_url: str = "http://127.0.0.1:8188", comfyui_path: Optional[str] = None, positive_prompt: Optional[str] = None, negative_prompt: Optional[str] = None, fps: Optional[int] = None, steps: Optional[int] = None, length: Optional[int] = None, seed: Optional[int] = None) -> str:
    """Queue a ComfyUI image-to-video workflow and return the prompt_id immediately"""
    try:
        client = ComfyUIClient(comfyui_url)
        
        if not comfyui_path or not os.path.exists(comfyui_path):
            raise Exception("ComfyUI path not configured. Please set ComfyUI folder path in settings.")
        
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
        
        return prompt_id
            
    except Exception as e:
        raise Exception(f"Failed to queue ComfyUI image-to-video workflow: {str(e)}")


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
        
        # Queue workflow and get prompt_id immediately
        prompt_id = _queue_comfyui_workflow(
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
        
        return {
            'success': True,
            'prompt_id': prompt_id,
            'message': 'Image generation started'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to start image generation'
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
        
        # Queue workflow and get prompt_id immediately
        prompt_id = _queue_comfyui_workflow(
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
        
        return {
            'success': True,
            'prompt_id': prompt_id,
            'message': 'Video generation started'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to start video generation'
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
        
        # Queue workflow and get prompt_id immediately
        prompt_id = _queue_comfyui_image_to_video(
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
        
        return {
            'success': True,
            'prompt_id': prompt_id,
            'message': 'Image-to-video generation started'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to start image-to-video generation'
        }


@app.get('/status/{prompt_id}')
def get_generation_status(prompt_id: str, comfyui_url: str = Query(default="http://127.0.0.1:8188")):
    """Get the current status of a generation request"""
    try:
        client = ComfyUIClient(comfyui_url)
        progress_info = client.get_prompt_progress(prompt_id)
        
        return {
            'success': True,
            'prompt_id': prompt_id,
            'status': progress_info['status'],
            'progress': progress_info.get('progress', 0),
            'message': progress_info['message']
        }
        
    except Exception as e:
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




# Workflow API Endpoints
@app.post('/workflows/sync')
def sync_workflows(workflows: list = Body(...)):
    """Sync workflow list from frontend"""
    _set_workflows_cache(workflows)
    return {"ok": True, "count": len(workflows)}


@app.post('/workflows/{workflow_id}/activate')
def activate_workflow(workflow_id: str):
    """Activate a workflow and start immediate execution"""
    try:
        state = _get_workflow_state(workflow_id)
        
        # Only activate if not already running
        if state.get('isRunning', False):
            return {
                "success": False,
                "error": "Cannot activate workflow that is currently running"
            }
        
        # Set workflow to active and clear nextExecutionTime to trigger immediate execution
        _update_workflow_state(workflow_id, {
            "isActive": True,
            "nextExecutionTime": None  # Set to None so scheduler executes immediately
        })
        
        # Find workflow to trigger immediate execution
        workflows = _get_workflows_cache()
        workflow = next((w for w in workflows if w.get('id') == workflow_id), None)
        
        if not workflow:
            return {
                "success": False,
                "error": "Workflow not found"
            }
        
        # Get ComfyUI settings
        prefs = _read_json(PREFERENCES_PATH, {})
        comfyui_url = prefs.get('comfyUiServer', 'http://127.0.0.1:8188')
        comfyui_path = prefs.get('comfyuiPath')
        
        # Execute immediately in background thread
        import threading
        def execute():
            try:
                execute_workflow(
                    workflow=workflow,
                    workflow_id=workflow_id,
                    comfyui_url=comfyui_url,
                    comfyui_path=comfyui_path,
                    update_state_callback=_update_workflow_state
                )
            except Exception as e:
                print(f"Workflow activation execution error: {e}")
                import traceback
                traceback.print_exc()
                _update_workflow_state(workflow_id, {"isRunning": False})
        
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


@app.post('/workflows/{workflow_id}/deactivate')
def deactivate_workflow(workflow_id: str):
    """Deactivate a workflow (will stop scheduling after current execution finishes)"""
    try:
        _update_workflow_state(workflow_id, {
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


@app.get('/workflows/{workflow_id}/status')
def get_workflow_status(workflow_id: str):
    """Get status for a specific workflow"""
    try:
        state = _get_workflow_state(workflow_id)
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
def get_all_workflows_status():
    """Get status for all workflows"""
    try:
        states = _get_all_workflow_states()
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
def execute_workflow_manual(workflow_id: str):
    """Manually execute a workflow (for testing, bypasses schedule)"""
    try:
        # Find workflow
        workflows = _get_workflows_cache()
        workflow = next((w for w in workflows if w.get('id') == workflow_id), None)
        
        if not workflow:
            return {
                "success": False,
                "error": "Workflow not found"
            }
        
        state = _get_workflow_state(workflow_id)
        if state.get('isRunning', False):
            return {
                "success": False,
                "error": "Workflow is already running"
            }
        
        # Get ComfyUI settings
        prefs = _read_json(PREFERENCES_PATH, {})
        comfyui_url = prefs.get('comfyUiServer', 'http://127.0.0.1:8188')
        comfyui_path = prefs.get('comfyuiPath')
        
        # Execute in background
        import threading
        def execute():
            try:
                execute_workflow(
                    workflow=workflow,
                    workflow_id=workflow_id,
                    comfyui_url=comfyui_url,
                    comfyui_path=comfyui_path,
                    update_state_callback=_update_workflow_state
                )
            except Exception as e:
                print(f"Manual execution error: {e}")
                _update_workflow_state(workflow_id, {"isRunning": False})
        
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


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8000)


