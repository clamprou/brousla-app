"""
Workflow execution logic for AI Workflows.
Handles execution of text-to-video and image-to-video workflows via ComfyUI.
Supports multi-clip workflows with FFMPEG concatenation.
"""
import os
import json
import time
import shutil
import subprocess
import tempfile
import requests
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from ai_agent import generate_prompts


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
        workflow: Workflow data dict with concept, videoWorkflowFile, imageWorkflowFile, schedule, numberOfClips
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
        numberOfClips = workflow.get('numberOfClips', 1)
        
        # Extract advanced settings
        advanced_settings = {
            'negativePrompt': workflow.get('negativePrompt', ''),
            'width': workflow.get('width', ''),
            'height': workflow.get('height', ''),
            'fps': workflow.get('fps', ''),
            'steps': workflow.get('steps', ''),
            'length': workflow.get('length', ''),
            'seed': workflow.get('seed', '')
        }
        
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
                numberOfClips=numberOfClips,
                advanced_settings=advanced_settings,
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
                numberOfClips=numberOfClips,
                advanced_settings=advanced_settings,
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
    numberOfClips: int = 1,
    advanced_settings: Optional[Dict] = None,
    update_state_callback=None,
    get_state_callback=None
) -> Dict:
    """Execute a text-to-video workflow"""
    try:
        # Get prompts from AI agent
        prompts = generate_prompts(concept, numberOfClips)
        
        if numberOfClips == 1:
            # Single clip workflow - use existing flow
            return _execute_single_text_to_video_clip(
                workflow_id=workflow_id,
                prompt=prompts[0],
                video_workflow=video_workflow,
                comfyui_url=comfyui_url,
                comfyui_path=comfyui_path,
                output_folder=output_folder,
                schedule_minutes=schedule_minutes,
                advanced_settings=advanced_settings or {},
                update_state_callback=update_state_callback,
                get_state_callback=get_state_callback
            )
        else:
            # Multi-clip workflow - generate sequentially then concatenate
            return _execute_multi_clip_text_to_video(
                workflow_id=workflow_id,
                prompts=prompts,
                video_workflow=video_workflow,
                comfyui_url=comfyui_url,
                comfyui_path=comfyui_path,
                output_folder=output_folder,
                schedule_minutes=schedule_minutes,
                advanced_settings=advanced_settings or {},
                update_state_callback=update_state_callback,
                get_state_callback=get_state_callback
            )
    
    except Exception as e:
        if update_state_callback:
            update_state_callback(workflow_id, {
                "isRunning": False
            })
        raise e


def _execute_single_text_to_video_clip(
    workflow_id: str,
    prompt: str,
    video_workflow: Dict,
    comfyui_url: str,
    comfyui_path: Optional[str],
    output_folder: Optional[str],
    schedule_minutes: int,
    advanced_settings: Optional[Dict] = None,
    update_state_callback=None,
    get_state_callback=None
) -> Dict:
    """Execute a single text-to-video clip"""
    try:
        advanced_settings = advanced_settings or {}
        # Create proper FormData for multipart/form-data
        files = {
            'workflow_file': (video_workflow.get('fileName', 'workflow.json'), json.dumps(video_workflow.get('json', {})), 'application/json')
        }
        data = {
            'prompt': prompt,
            'comfyui_url': comfyui_url
        }
        
        # Add advanced settings if provided
        if advanced_settings.get('negativePrompt'):
            data['negative_prompt'] = advanced_settings['negativePrompt']
        if advanced_settings.get('width'):
            data['width'] = advanced_settings['width']
        if advanced_settings.get('height'):
            data['height'] = advanced_settings['height']
        if advanced_settings.get('fps'):
            data['fps'] = advanced_settings['fps']
        if advanced_settings.get('steps'):
            data['steps'] = advanced_settings['steps']
        if advanced_settings.get('length'):
            data['length'] = advanced_settings['length']
        if advanced_settings.get('seed'):
            data['seed'] = advanced_settings['seed']
        
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
        
        # Poll for completion
        _poll_for_completion(prompt_id, comfyui_url, timeout=600)  # 10 minutes for video
        
        # Get result and copy to output folder if specified
        if output_folder:
            _copy_video_to_output_folder(
                prompt_id=prompt_id,
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
            "prompt_id": prompt_id,
            "message": "Text-to-video workflow completed successfully"
        }
    
    except Exception as e:
        if update_state_callback:
            update_state_callback(workflow_id, {
                "isRunning": False
            })
        raise e


def _execute_multi_clip_text_to_video(
    workflow_id: str,
    prompts: List[str],
    video_workflow: Dict,
    comfyui_url: str,
    comfyui_path: Optional[str],
    output_folder: Optional[str],
    schedule_minutes: int,
    advanced_settings: Optional[Dict] = None,
    update_state_callback=None,
    get_state_callback=None
) -> Dict:
    """Execute multiple text-to-video clips sequentially, then concatenate"""
    temp_dir = None
    clip_paths = []
    advanced_settings = advanced_settings or {}
    
    try:
        # Create temporary directory for intermediate clips
        temp_dir = tempfile.mkdtemp(prefix=f'workflow_{workflow_id}_')
        
        # Generate clips sequentially
        for clip_index, prompt in enumerate(prompts, start=1):
            print(f"Generating clip {clip_index}/{len(prompts)}: {prompt[:50]}...")
            
            # Create proper FormData for multipart/form-data
            files = {
                'workflow_file': (video_workflow.get('fileName', 'workflow.json'), json.dumps(video_workflow.get('json', {})), 'application/json')
            }
            data = {
                'prompt': prompt,
                'comfyui_url': comfyui_url
            }
            
            # Add advanced settings if provided
            if advanced_settings.get('negativePrompt'):
                data['negative_prompt'] = advanced_settings['negativePrompt']
            if advanced_settings.get('width'):
                data['width'] = advanced_settings['width']
            if advanced_settings.get('height'):
                data['height'] = advanced_settings['height']
            if advanced_settings.get('fps'):
                data['fps'] = advanced_settings['fps']
            if advanced_settings.get('steps'):
                data['steps'] = advanced_settings['steps']
            if advanced_settings.get('length'):
                data['length'] = advanced_settings['length']
            if advanced_settings.get('seed'):
                data['seed'] = advanced_settings['seed']
            
            # Queue video generation
            response = requests.post(
                f'http://127.0.0.1:8000/generate_video',
                files=files,
                data=data,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to start video generation for clip {clip_index}: {response.status_code}")
            
            result = response.json()
            if not result.get('success'):
                raise Exception(f"Video generation failed for clip {clip_index}: {result.get('error', 'Unknown error')}")
            
            prompt_id = result.get('prompt_id')
            
            # Update state with prompt_id
            if update_state_callback:
                update_state_callback(workflow_id, {
                    "lastPromptId": prompt_id
                })
            
            # Poll for completion
            _poll_for_completion(prompt_id, comfyui_url, timeout=600)  # 10 minutes for video
            
            # Download the generated video to temp directory
            clip_path = _download_clip_to_temp(
                prompt_id=prompt_id,
                workflow_id=workflow_id,
                clip_index=clip_index,
                temp_dir=temp_dir,
                comfyui_url=comfyui_url,
                comfyui_path=comfyui_path
            )
            
            clip_paths.append(clip_path)
            print(f"Clip {clip_index}/{len(prompts)} completed: {clip_path}")
        
        # Concatenate all clips
        if output_folder:
            os.makedirs(output_folder, exist_ok=True)
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            file_ext = os.path.splitext(clip_paths[0])[1] if clip_paths else '.mp4'
            output_filename = f"{timestamp}_{workflow_id[:8]}{file_ext}"
            final_output_path = os.path.join(output_folder, output_filename)
            
            print(f"Concatenating {len(clip_paths)} clips into {final_output_path}")
            _concatenate_videos(clip_paths, final_output_path)
            print(f"Successfully concatenated videos to {final_output_path}")
        
        # Clean up intermediate files
        _cleanup_temp_files(clip_paths, temp_dir)
        
        # Update state after completion
        next_execution = datetime.utcnow() + timedelta(minutes=schedule_minutes)
        if update_state_callback:
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
            "num_clips": len(prompts),
            "message": f"Multi-clip text-to-video workflow completed successfully ({len(prompts)} clips)"
        }
    
    except Exception as e:
        # Clean up on error
        _cleanup_temp_files(clip_paths, temp_dir)
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
    numberOfClips: int = 1,
    advanced_settings: Optional[Dict] = None,
    update_state_callback=None,
    get_state_callback=None
) -> Dict:
    """Execute an image-to-video workflow (generate image first, then video)"""
    try:
        # Get prompts from AI agent for video generation
        prompts = generate_prompts(concept, numberOfClips)
        
        if numberOfClips == 1:
            # Single clip workflow - use existing flow
            return _execute_single_image_to_video_clip(
                workflow_id=workflow_id,
                concept=concept,
                prompt=prompts[0],
                image_workflow=image_workflow,
                video_workflow=video_workflow,
                comfyui_url=comfyui_url,
                comfyui_path=comfyui_path,
                output_folder=output_folder,
                schedule_minutes=schedule_minutes,
                advanced_settings=advanced_settings or {},
                update_state_callback=update_state_callback,
                get_state_callback=get_state_callback
            )
        else:
            # Multi-clip workflow - generate one image, then multiple videos sequentially
            return _execute_multi_clip_image_to_video(
                workflow_id=workflow_id,
                concept=concept,
                prompts=prompts,
                image_workflow=image_workflow,
                video_workflow=video_workflow,
                comfyui_url=comfyui_url,
                comfyui_path=comfyui_path,
                output_folder=output_folder,
                schedule_minutes=schedule_minutes,
                advanced_settings=advanced_settings or {},
                update_state_callback=update_state_callback,
                get_state_callback=get_state_callback
            )
    
    except Exception as e:
        if update_state_callback:
            update_state_callback(workflow_id, {
                "isRunning": False
            })
        raise e


def _execute_single_image_to_video_clip(
    workflow_id: str,
    concept: str,
    prompt: str,
    image_workflow: Dict,
    video_workflow: Dict,
    comfyui_url: str,
    comfyui_path: Optional[str],
    output_folder: Optional[str],
    schedule_minutes: int,
    advanced_settings: Optional[Dict] = None,
    update_state_callback=None,
    get_state_callback=None
) -> Dict:
    """Execute a single image-to-video clip"""
    try:
        advanced_settings = advanced_settings or {}
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
        
        # Add advanced settings for video generation (no width/height for image-to-video)
        if advanced_settings.get('negativePrompt'):
            video_form_data['negative_prompt'] = advanced_settings['negativePrompt']
        if advanced_settings.get('fps'):
            video_form_data['fps'] = advanced_settings['fps']
        if advanced_settings.get('steps'):
            video_form_data['steps'] = advanced_settings['steps']
        if advanced_settings.get('length'):
            video_form_data['length'] = advanced_settings['length']
        if advanced_settings.get('seed'):
            video_form_data['seed'] = advanced_settings['seed']
        
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


def _execute_multi_clip_image_to_video(
    workflow_id: str,
    concept: str,
    prompts: List[str],
    image_workflow: Dict,
    video_workflow: Dict,
    comfyui_url: str,
    comfyui_path: Optional[str],
    output_folder: Optional[str],
    schedule_minutes: int,
    advanced_settings: Optional[Dict] = None,
    update_state_callback=None,
    get_state_callback=None
) -> Dict:
    """Execute multiple image-to-video clips sequentially, then concatenate"""
    temp_dir = None
    clip_paths = []
    advanced_settings = advanced_settings or {}
    
    try:
        # Step 1: Generate one image from the base concept
        print(f"Generating base image for {len(prompts)} clips...")
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
        print(f"Base image downloaded: {image_filename}")
        
        # Step 2: Generate multiple video clips sequentially using the same image
        temp_dir = tempfile.mkdtemp(prefix=f'workflow_{workflow_id}_')
        
        for clip_index, prompt in enumerate(prompts, start=1):
            print(f"Generating clip {clip_index}/{len(prompts)}: {prompt[:50]}...")
            
            # Generate video from image
            video_files = {
                'workflow_file': (video_workflow.get('fileName', 'video_workflow.json'), json.dumps(video_workflow.get('json', {})), 'application/json'),
                'image_file': (image_filename, image_data_bytes, 'image/png')
            }
            video_form_data = {
                'comfyui_url': comfyui_url,
                'comfyui_path': comfyui_path or ''
            }
            
            # Add advanced settings for video generation (no width/height for image-to-video)
            if advanced_settings.get('negativePrompt'):
                video_form_data['negative_prompt'] = advanced_settings['negativePrompt']
            if advanced_settings.get('fps'):
                video_form_data['fps'] = advanced_settings['fps']
            if advanced_settings.get('steps'):
                video_form_data['steps'] = advanced_settings['steps']
            if advanced_settings.get('length'):
                video_form_data['length'] = advanced_settings['length']
            if advanced_settings.get('seed'):
                video_form_data['seed'] = advanced_settings['seed']
            
            video_response = requests.post(
                f'http://127.0.0.1:8000/generate_image_to_video',
                files=video_files,
                data=video_form_data,
                timeout=30
            )
            
            if video_response.status_code != 200:
                raise Exception(f"Failed to start video generation for clip {clip_index}: {video_response.status_code}")
            
            video_result = video_response.json()
            if not video_result.get('success'):
                raise Exception(f"Video generation failed for clip {clip_index}: {video_result.get('error', 'Unknown error')}")
            
            video_prompt_id = video_result.get('prompt_id')
            
            # Update state with prompt_id
            if update_state_callback:
                update_state_callback(workflow_id, {
                    "lastPromptId": video_prompt_id
                })
            
            # Poll for video completion
            _poll_for_completion(video_prompt_id, comfyui_url, timeout=600)  # 10 minutes for video
            
            # Download the generated video to temp directory
            clip_path = _download_clip_to_temp(
                prompt_id=video_prompt_id,
                workflow_id=workflow_id,
                clip_index=clip_index,
                temp_dir=temp_dir,
                comfyui_url=comfyui_url,
                comfyui_path=comfyui_path
            )
            
            clip_paths.append(clip_path)
            print(f"Clip {clip_index}/{len(prompts)} completed: {clip_path}")
        
        # Concatenate all clips
        if output_folder:
            os.makedirs(output_folder, exist_ok=True)
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            file_ext = os.path.splitext(clip_paths[0])[1] if clip_paths else '.mp4'
            output_filename = f"{timestamp}_{workflow_id[:8]}{file_ext}"
            final_output_path = os.path.join(output_folder, output_filename)
            
            print(f"Concatenating {len(clip_paths)} clips into {final_output_path}")
            _concatenate_videos(clip_paths, final_output_path)
            print(f"Successfully concatenated videos to {final_output_path}")
        
        # Clean up intermediate files
        _cleanup_temp_files(clip_paths, temp_dir)
        
        # Update state after completion
        next_execution = datetime.utcnow() + timedelta(minutes=schedule_minutes)
        if update_state_callback:
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
            "num_clips": len(prompts),
            "message": f"Multi-clip image-to-video workflow completed successfully ({len(prompts)} clips)"
        }
    
    except Exception as e:
        # Clean up on error
        _cleanup_temp_files(clip_paths, temp_dir)
        if update_state_callback:
            update_state_callback(workflow_id, {
                "isRunning": False
            })
        raise e


def _download_clip_to_temp(
    prompt_id: str,
    workflow_id: str,
    clip_index: int,
    temp_dir: str,
    comfyui_url: str,
    comfyui_path: Optional[str]
) -> str:
    """
    Download a generated video clip to temporary directory.
    
    Args:
        prompt_id: ComfyUI prompt ID for the completed video generation
        workflow_id: Workflow identifier
        clip_index: Index of the clip (1-based)
        temp_dir: Temporary directory to store the clip
        comfyui_url: ComfyUI server URL
        comfyui_path: Path to ComfyUI installation
    
    Returns:
        Path to the downloaded clip file
    """
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
        raise Exception(f"Failed to get result for prompt {prompt_id}: {result_response.status_code}")
    
    result = result_response.json()
    if not result.get('success'):
        raise Exception(f"Failed to get result for prompt {prompt_id}: {result.get('error', 'Unknown error')}")
    
    filename = result.get('filename')
    subfolder = result.get('subfolder', '')
    
    if not filename:
        raise Exception(f"No filename in result for prompt {prompt_id}")
    
    # Construct source path in ComfyUI output directory
    if not comfyui_path or not os.path.exists(comfyui_path):
        raise Exception(f"ComfyUI path not configured or invalid: {comfyui_path}")
    
    comfyui_output_dir = os.path.join(comfyui_path, "ComfyUI", "output")
    if subfolder:
        comfyui_output_dir = os.path.join(comfyui_output_dir, subfolder)
    
    source_path = os.path.join(comfyui_output_dir, filename)
    
    if not os.path.exists(source_path):
        raise Exception(f"Video file not found at {source_path}")
    
    # Create output filename for clip
    file_ext = os.path.splitext(filename)[1]
    clip_filename = f"clip_{clip_index:03d}{file_ext}"
    dest_path = os.path.join(temp_dir, clip_filename)
    
    # Copy file to temp directory
    shutil.copy2(source_path, dest_path)
    
    return dest_path


def _concatenate_videos(video_paths: List[str], output_path: str) -> None:
    """
    Concatenate multiple video files using FFMPEG.
    
    Args:
        video_paths: List of paths to video files to concatenate
        output_path: Path where the concatenated video should be saved
    
    Raises:
        Exception: If FFMPEG is not found or concatenation fails
    """
    if not video_paths:
        raise Exception("No video files to concatenate")
    
    # Check if FFMPEG is available
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise Exception("FFMPEG not found. Please install FFMPEG and ensure it's in your system PATH.")
    
    # Create a temporary file list for FFMPEG concat demuxer
    concat_file = output_path + '.concat.txt'
    try:
        with open(concat_file, 'w', encoding='utf-8') as f:
            for video_path in video_paths:
                # Escape single quotes and use absolute path
                abs_path = os.path.abspath(video_path).replace("'", "'\\''")
                f.write(f"file '{abs_path}'\n")
        
        # Run FFMPEG concat command
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',
            '-y',  # Overwrite output file if it exists
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Verify output file was created
        if not os.path.exists(output_path):
            raise Exception(f"FFMPEG concatenation completed but output file not found: {output_path}")
        
    finally:
        # Clean up concat file
        if os.path.exists(concat_file):
            try:
                os.remove(concat_file)
            except Exception:
                pass  # Ignore cleanup errors


def _cleanup_temp_files(clip_paths: List[str], temp_dir: Optional[str]) -> None:
    """
    Clean up temporary files and directory.
    
    Args:
        clip_paths: List of clip file paths to delete
        temp_dir: Temporary directory to remove
    """
    try:
        # Delete individual clip files
        for clip_path in clip_paths:
            if clip_path and os.path.exists(clip_path):
                try:
                    os.remove(clip_path)
                except Exception as e:
                    print(f"Warning: Failed to delete clip file {clip_path}: {e}")
        
        # Remove temporary directory if it's empty
        if temp_dir and os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except Exception as e:
                print(f"Warning: Failed to remove temp directory {temp_dir}: {e}")
    except Exception as e:
        print(f"Warning: Error during cleanup: {e}")


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



