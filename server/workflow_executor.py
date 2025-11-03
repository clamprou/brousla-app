"""
Workflow execution logic for AI Workflows.
Handles execution of text-to-video and image-to-video workflows via ComfyUI.
"""
import os
import json
import time
import shutil
import requests
from typing import Dict, Optional
from datetime import datetime, timedelta


def execute_workflow(
    workflow: Dict,
    workflow_id: str,
    comfyui_url: str = "http://127.0.0.1:8188",
    comfyui_path: Optional[str] = None,
    output_folder: Optional[str] = None,
    update_state_callback=None,
    get_state_callback=None
) -> Dict:
    """
    Execute a workflow based on its type.
    
    Args:
        workflow: Workflow data dict with concept, videoWorkflowFile, imageWorkflowFile, schedule
        workflow_id: Unique workflow identifier
        comfyui_url: ComfyUI server URL
        comfyui_path: Path to ComfyUI installation
        output_folder: Path to folder where final videos should be saved
        update_state_callback: Function to call for state updates (workflow_id, updates_dict)
    
    Returns:
        Dict with success status and execution details
    """
    try:
        # Determine workflow type
        is_image_to_video = workflow.get('imageWorkflowFile') is not None
        
        concept = workflow.get('concept', '')
        video_workflow = workflow.get('videoWorkflowFile')
        image_workflow = workflow.get('imageWorkflowFile')
        schedule_minutes = workflow.get('schedule', 60)
        
        if not concept or not video_workflow:
            raise Exception("Workflow missing required fields: concept or videoWorkflowFile")
        
        if is_image_to_video and not image_workflow:
            raise Exception("Image-to-video workflow missing imageWorkflowFile")
        
        # Update state: set isRunning=True
        if update_state_callback:
            update_state_callback(workflow_id, {
                "isRunning": True,
                "lastExecutionTime": datetime.utcnow().isoformat() + 'Z'
            })
        
        if is_image_to_video:
            # Sequential execution: image first, then video
            # Type assertion: image_workflow is guaranteed to be non-None here due to earlier check
            if not image_workflow:
                raise Exception("Image-to-video workflow missing imageWorkflowFile")
            return _execute_image_to_video_workflow(
                workflow_id=workflow_id,
                concept=concept,
                image_workflow=image_workflow,
                video_workflow=video_workflow,
                comfyui_url=comfyui_url,
                comfyui_path=comfyui_path,
                output_folder=output_folder,
                schedule_minutes=schedule_minutes,
                update_state_callback=update_state_callback,
                get_state_callback=get_state_callback
            )
        else:
            # Text-to-video workflow
            return _execute_text_to_video_workflow(
                workflow_id=workflow_id,
                concept=concept,
                video_workflow=video_workflow,
                comfyui_url=comfyui_url,
                comfyui_path=comfyui_path,
                output_folder=output_folder,
                schedule_minutes=schedule_minutes,
                update_state_callback=update_state_callback,
                get_state_callback=get_state_callback
            )
    
    except Exception as e:
        # Update state: set isRunning=False on error
        if update_state_callback:
            update_state_callback(workflow_id, {
                "isRunning": False
            })
        return {
            "success": False,
            "error": str(e),
            "workflow_id": workflow_id
        }


def _execute_text_to_video_workflow(
    workflow_id: str,
    concept: str,
    video_workflow: Dict,
    comfyui_url: str,
    comfyui_path: Optional[str],
    output_folder: Optional[str],
    schedule_minutes: int,
    update_state_callback=None,
    get_state_callback=None
) -> Dict:
    """Execute a text-to-video workflow"""
    try:
        # Step 1: Queue video generation
        form_data = {
            'workflow_file': (None, json.dumps(video_workflow.get('json', {})), 'application/json'),
            'prompt': (None, concept),
            'comfyui_url': (None, comfyui_url)
        }
        
        # Create proper FormData for multipart/form-data
        files = {
            'workflow_file': (video_workflow.get('fileName', 'workflow.json'), json.dumps(video_workflow.get('json', {})), 'application/json')
        }
        data = {
            'prompt': concept,
            'comfyui_url': comfyui_url
        }
        
        # Use requests to call the generate_video endpoint
        response = requests.post(
            f'http://127.0.0.1:8000/generate_video',
            files=files,
            data=data,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to start video generation: {response.status_code}")
        
        result = response.json()
        if not result.get('success'):
            raise Exception(f"Video generation failed: {result.get('error', 'Unknown error')}")
        
        prompt_id = result.get('prompt_id')
        
        # Update state with prompt_id
        if update_state_callback:
            update_state_callback(workflow_id, {
                "lastPromptId": prompt_id
            })
        
        # Step 2: Poll for completion
        _poll_for_completion(prompt_id, comfyui_url, timeout=600)  # 10 minutes for video
        
        # Step 3: Get result and copy to output folder if specified
        if output_folder:
            _copy_video_to_output_folder(
                prompt_id=prompt_id,
                workflow_id=workflow_id,
                comfyui_url=comfyui_url,
                comfyui_path=comfyui_path,
                output_folder=output_folder
            )
        
        # Step 4: Update state after completion
        next_execution = datetime.utcnow() + timedelta(minutes=schedule_minutes)
        if update_state_callback:
            # Get current execution count and increment
            from main import _get_workflow_state
            current_state = _get_workflow_state(workflow_id)
            current_count = current_state.get('executionCount', 0)
            
            update_state_callback(workflow_id, {
                "isRunning": False,
                "executionCount": current_count + 1,
                "nextExecutionTime": next_execution.isoformat() + 'Z'
            })
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "prompt_id": prompt_id,
            "message": "Text-to-video workflow completed successfully"
        }
    
    except Exception as e:
        if update_state_callback:
            update_state_callback(workflow_id, {
                "isRunning": False
            })
        raise e


def _execute_image_to_video_workflow(
    workflow_id: str,
    concept: str,
    image_workflow: Dict,
    video_workflow: Dict,
    comfyui_url: str,
    comfyui_path: Optional[str],
    output_folder: Optional[str],
    schedule_minutes: int,
    update_state_callback=None,
    get_state_callback=None
) -> Dict:
    """Execute an image-to-video workflow (generate image first, then video)"""
    try:
        # Step 1: Generate image
        image_files = {
            'workflow_file': (image_workflow.get('fileName', 'image_workflow.json'), json.dumps(image_workflow.get('json', {})), 'application/json')
        }
        image_data = {
            'prompt': concept,
            'comfyui_url': comfyui_url
        }
        
        response = requests.post(
            f'http://127.0.0.1:8000/generate_image',
            files=image_files,
            data=image_data,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to start image generation: {response.status_code}")
        
        result = response.json()
        if not result.get('success'):
            raise Exception(f"Image generation failed: {result.get('error', 'Unknown error')}")
        
        image_prompt_id = result.get('prompt_id')
        
        # Poll for image completion
        _poll_for_completion(image_prompt_id, comfyui_url, timeout=300)  # 5 minutes for image
        
        # Get image result
        result_response = requests.get(
            f'http://127.0.0.1:8000/result/{image_prompt_id}',
            params={
                'comfyui_url': comfyui_url,
                'comfyui_path': comfyui_path or ''
            },
            timeout=30
        )
        
        if result_response.status_code != 200:
            raise Exception(f"Failed to get image result: {result_response.status_code}")
        
        image_result = result_response.json()
        if not image_result.get('success'):
            raise Exception(f"Failed to get image result: {image_result.get('error', 'Unknown error')}")
        
        # Download the generated image
        image_filename = image_result.get('filename')
        image_subfolder = image_result.get('subfolder', '')
        
        if not image_filename:
            raise Exception("No image filename returned")
        
        # Download image from ComfyUI
        image_url = f'http://127.0.0.1:8000/comfyui-file'
        params = {
            'filename': image_filename,
            'subfolder': image_subfolder,
            'comfyui_path': comfyui_path or ''
        }
        
        image_response = requests.get(image_url, params=params, timeout=60)
        if image_response.status_code != 200:
            raise Exception(f"Failed to download generated image: {image_response.status_code}")
        
        image_data_bytes = image_response.content
        
        # Step 2: Generate video from image
        video_files = {
            'workflow_file': (video_workflow.get('fileName', 'video_workflow.json'), json.dumps(video_workflow.get('json', {})), 'application/json'),
            'image_file': (image_filename, image_data_bytes, 'image/png')
        }
        video_form_data = {
            'comfyui_url': comfyui_url,
            'comfyui_path': comfyui_path or ''
        }
        
        video_response = requests.post(
            f'http://127.0.0.1:8000/generate_image_to_video',
            files=video_files,
            data=video_form_data,
            timeout=30
        )
        
        if video_response.status_code != 200:
            raise Exception(f"Failed to start video generation: {video_response.status_code}")
        
        video_result = video_response.json()
        if not video_result.get('success'):
            raise Exception(f"Video generation failed: {video_result.get('error', 'Unknown error')}")
        
        video_prompt_id = video_result.get('prompt_id')
        
        # Update state with prompt_id
        if update_state_callback:
            update_state_callback(workflow_id, {
                "lastPromptId": video_prompt_id
            })
        
        # Poll for video completion
        _poll_for_completion(video_prompt_id, comfyui_url, timeout=600)  # 10 minutes for video
        
        # Get result and copy to output folder if specified
        if output_folder:
            _copy_video_to_output_folder(
                prompt_id=video_prompt_id,
                workflow_id=workflow_id,
                comfyui_url=comfyui_url,
                comfyui_path=comfyui_path,
                output_folder=output_folder
            )
        
        # Update state after completion
        next_execution = datetime.utcnow() + timedelta(minutes=schedule_minutes)
        if update_state_callback:
            # Get current execution count and increment
            from main import _get_workflow_state
            current_state = _get_workflow_state(workflow_id)
            current_count = current_state.get('executionCount', 0)
            
            update_state_callback(workflow_id, {
                "isRunning": False,
                "executionCount": current_count + 1,
                "nextExecutionTime": next_execution.isoformat() + 'Z'
            })
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "image_prompt_id": image_prompt_id,
            "video_prompt_id": video_prompt_id,
            "message": "Image-to-video workflow completed successfully"
        }
    
    except Exception as e:
        if update_state_callback:
            update_state_callback(workflow_id, {
                "isRunning": False
            })
        raise e


def _poll_for_completion(prompt_id: str, comfyui_url: str, timeout: int = 300) -> None:
    """Poll ComfyUI for workflow completion"""
    start_time = time.time()
    poll_interval = 2  # Poll every 2 seconds
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(
                f'http://127.0.0.1:8000/status/{prompt_id}',
                params={'comfyui_url': comfyui_url},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    status = result.get('status')
                    if status == 'completed':
                        return  # Success
                    elif status == 'error':
                        raise Exception(f"ComfyUI execution error: {result.get('message', 'Unknown error')}")
                    # Otherwise, continue polling
        
        except requests.exceptions.RequestException:
            pass  # Continue polling on network errors
        
        time.sleep(poll_interval)
    
    raise TimeoutError(f"Workflow execution timed out after {timeout} seconds")


def _copy_video_to_output_folder(
    prompt_id: str,
    workflow_id: str,
    comfyui_url: str,
    comfyui_path: Optional[str],
    output_folder: Optional[str]
) -> None:
    """
    Copy the generated video file from ComfyUI output directory to user-specified output folder.
    
    Args:
        prompt_id: ComfyUI prompt ID for the completed video generation
        workflow_id: Workflow identifier for filename generation
        comfyui_url: ComfyUI server URL
        comfyui_path: Path to ComfyUI installation
        output_folder: Path to folder where video should be saved
    """
    if not output_folder:
        return
    
    try:
        # Get the result from the backend
        result_response = requests.get(
            f'http://127.0.0.1:8000/result/{prompt_id}',
            params={
                'comfyui_url': comfyui_url,
                'comfyui_path': comfyui_path or ''
            },
            timeout=30
        )
        
        if result_response.status_code != 200:
            print(f"Warning: Failed to get result for prompt {prompt_id}: {result_response.status_code}")
            return
        
        result = result_response.json()
        if not result.get('success'):
            print(f"Warning: Failed to get result for prompt {prompt_id}: {result.get('error', 'Unknown error')}")
            return
        
        filename = result.get('filename')
        subfolder = result.get('subfolder', '')
        
        if not filename:
            print(f"Warning: No filename in result for prompt {prompt_id}")
            return
        
        # Construct source path in ComfyUI output directory
        if not comfyui_path or not os.path.exists(comfyui_path):
            print(f"Warning: ComfyUI path not configured or invalid: {comfyui_path}")
            return
        
        comfyui_output_dir = os.path.join(comfyui_path, "ComfyUI", "output")
        if subfolder:
            comfyui_output_dir = os.path.join(comfyui_output_dir, subfolder)
        
        source_path = os.path.join(comfyui_output_dir, filename)
        
        if not os.path.exists(source_path):
            print(f"Warning: Video file not found at {source_path}")
            return
        
        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Generate unique filename: timestamp_workflowid_originalname
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        file_ext = os.path.splitext(filename)[1]
        output_filename = f"{timestamp}_{workflow_id[:8]}{file_ext}"
        dest_path = os.path.join(output_folder, output_filename)
        
        # Copy file to output folder
        shutil.copy2(source_path, dest_path)
        print(f"Successfully copied video to {dest_path}")
        
    except Exception as e:
        print(f"Error copying video to output folder: {str(e)}")
        # Don't raise exception - workflow should still be considered successful
        # even if copying fails



