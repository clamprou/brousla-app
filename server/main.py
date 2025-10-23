import os
import json
import uuid
import asyncio
import base64
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn

# Import ComfyUI client
from comfyui_client import ComfyUIClient

# Optional: OpenAI client
try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), 'workflows')
OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), 'outputs')

PREFERENCES_PATH = os.path.join(DATA_DIR, 'preferences.json')
HISTORY_PATH = os.path.join(DATA_DIR, 'history.json')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(WORKFLOWS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def _execute_comfyui_workflow(workflow_json: dict, prompt_text: str, comfyui_url: str = "http://127.0.0.1:8188") -> str:
    """Execute a ComfyUI workflow with the given prompt - handles both API and original formats"""
    try:
        client = ComfyUIClient(comfyui_url)
        
        # Modify workflow to use the prompt text
        modified_workflow = client.modify_workflow_prompt(workflow_json, prompt_text)
        
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
        
        # Queue the prompt
        queue_result = client.queue_prompt(workflow_to_queue)
        prompt_id = queue_result["prompt_id"]
        
        # Wait for completion
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(client.wait_for_completion(prompt_id))
        finally:
            loop.close()
        
        # Download the generated images
        if result["images"]:
            image_info = result["images"][0]  # Get first image
            image_data = client.get_image(
                image_info["filename"],
                image_info.get("subfolder", ""),
                image_info.get("type", "output")
            )
            
            # Save image to outputs directory
            output_filename = f"{uuid.uuid4().hex}_{image_info['filename']}"
            output_path = os.path.join(OUTPUTS_DIR, output_filename)
            
            with open(output_path, 'wb') as f:
                f.write(image_data)
            
            return output_path
        else:
            raise Exception("No images generated")
            
    except Exception as e:
        # Create error file
        error_filename = f"error_{uuid.uuid4().hex}.txt"
        error_path = os.path.join(OUTPUTS_DIR, error_filename)
        with open(error_path, 'w', encoding='utf-8') as f:
            f.write(f"ComfyUI Error: {str(e)}\n")
            f.write(f"Prompt: {prompt_text}\n")
        return error_path


def _execute_comfyui_image_to_video(workflow_json: dict, image_data: bytes, image_filename: str, comfyui_url: str = "http://127.0.0.1:8188") -> str:
    """Execute a ComfyUI workflow for image-to-video generation - handles both API and original formats"""
    try:
        client = ComfyUIClient(comfyui_url)
        
        # Upload image to ComfyUI input directory
        input_dir = os.path.join(os.path.dirname(__file__), 'comfyui_inputs')
        os.makedirs(input_dir, exist_ok=True)
        
        input_path = os.path.join(input_dir, image_filename)
        with open(input_path, 'wb') as f:
            f.write(image_data)
        
        # Modify workflow to use the uploaded image
        modified_workflow = client.modify_workflow_image_input(workflow_json, image_data, image_filename)
        
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
        
        # Queue the prompt
        queue_result = client.queue_prompt(workflow_to_queue)
        prompt_id = queue_result["prompt_id"]
        
        # Wait for completion
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(client.wait_for_completion(prompt_id, timeout=600))  # Longer timeout for video
        finally:
            loop.close()
        
        # Download the generated video/images
        if result["images"]:
            output_info = result["images"][0]  # Get first output
            output_data = client.get_image(
                output_info["filename"],
                output_info.get("subfolder", ""),
                output_info.get("type", "output")
            )
            
            # Save output to outputs directory
            output_filename = f"{uuid.uuid4().hex}_{output_info['filename']}"
            output_path = os.path.join(OUTPUTS_DIR, output_filename)
            
            with open(output_path, 'wb') as f:
                f.write(output_data)
            
            return output_path
        else:
            raise Exception("No output generated")
            
    except Exception as e:
        # Create error file
        error_filename = f"error_{uuid.uuid4().hex}.txt"
        error_path = os.path.join(OUTPUTS_DIR, error_filename)
        with open(error_path, 'w', encoding='utf-8') as f:
            f.write(f"ComfyUI Image-to-Video Error: {str(e)}\n")
            f.write(f"Image: {image_filename}\n")
        return error_path


@app.post('/generate_image')
async def generate_image(
    workflow_file: UploadFile = File(...),
    prompt: str = Form(...),
    comfyui_url: str = Form(default="http://127.0.0.1:8188")
):
    """Generate an image using ComfyUI workflow"""
    try:
        # Read workflow file
        workflow_content = await workflow_file.read()
        workflow_json = json.loads(workflow_content.decode('utf-8'))
        
        # Execute workflow
        result_path = _execute_comfyui_workflow(workflow_json, prompt, comfyui_url)
        
        # Add to history
        item = {
            'id': uuid.uuid4().hex,
            'type': 'image_generation',
            'prompt': prompt,
            'workflow_file': workflow_file.filename,
            'resultPath': result_path,
            'createdAt': datetime.utcnow().isoformat() + 'Z',
        }
        _append_history(item)
        
        return {
            'success': True,
            'resultPath': result_path,
            'message': 'Image generated successfully'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to generate image'
        }


@app.post('/generate_video')
async def generate_video(
    workflow_file: UploadFile = File(...),
    prompt: str = Form(...),
    comfyui_url: str = Form(default="http://127.0.0.1:8188")
):
    """Generate a video using ComfyUI workflow"""
    try:
        # Read workflow file
        workflow_content = await workflow_file.read()
        workflow_json = json.loads(workflow_content.decode('utf-8'))
        
        # Execute workflow
        result_path = _execute_comfyui_workflow(workflow_json, prompt, comfyui_url)
        
        # Add to history
        item = {
            'id': uuid.uuid4().hex,
            'type': 'video_generation',
            'prompt': prompt,
            'workflow_file': workflow_file.filename,
            'resultPath': result_path,
            'createdAt': datetime.utcnow().isoformat() + 'Z',
        }
        _append_history(item)
        
        return {
            'success': True,
            'resultPath': result_path,
            'message': 'Video generated successfully'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to generate video'
        }


@app.post('/generate_image_to_video')
async def generate_image_to_video(
    workflow_file: UploadFile = File(...),
    image_file: UploadFile = File(...),
    comfyui_url: str = Form(default="http://127.0.0.1:8188")
):
    """Generate a video from an image using ComfyUI workflow"""
    try:
        # Read workflow file
        workflow_content = await workflow_file.read()
        workflow_json = json.loads(workflow_content.decode('utf-8'))
        
        # Read image file
        image_content = await image_file.read()
        
        # Execute workflow
        result_path = _execute_comfyui_image_to_video(
            workflow_json, 
            image_content, 
            image_file.filename, 
            comfyui_url
        )
        
        # Add to history
        item = {
            'id': uuid.uuid4().hex,
            'type': 'image_to_video',
            'image_file': image_file.filename,
            'workflow_file': workflow_file.filename,
            'resultPath': result_path,
            'createdAt': datetime.utcnow().isoformat() + 'Z',
        }
        _append_history(item)
        
        return {
            'success': True,
            'resultPath': result_path,
            'message': 'Video generated successfully from image'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to generate video from image'
        }


@app.get('/file')
def get_file(path: str = Query(..., description="Absolute or server-relative path to serve")):
    # Security: restrict to OUTPUTS_DIR
    abs_path = os.path.abspath(path)
    if not abs_path.startswith(os.path.abspath(OUTPUTS_DIR)):
        return {"error": "Access denied"}
    return FileResponse(abs_path)


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8000)


