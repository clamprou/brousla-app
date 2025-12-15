import json
import requests
import websockets
import asyncio
import uuid
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class ComfyUIClient:
    def __init__(self, server_url: str = "http://127.0.0.1:8188"):
        self.server_url = server_url.rstrip('/')
        self.ws_url = self.server_url.replace('http', 'ws')
        
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def queue_prompt(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """Queue a prompt for execution in ComfyUI"""
        try:
            response = requests.post(
                f"{self.server_url}/prompt",
                json={"prompt": prompt},
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to queue prompt: {e}")
            raise Exception(f"Failed to queue ComfyUI prompt: {e}")
    
    def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """Get execution history for a prompt"""
        try:
            response = requests.get(
                f"{self.server_url}/history/{prompt_id}",
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            # Ensure we return a dict, not None
            if data is None:
                return {}
            return data if isinstance(data, dict) else {}
        except requests.exceptions.RequestException as e:
            logger.debug(f"Failed to get history for prompt {prompt_id}: {e}")
            # Return empty dict instead of raising, so status check can continue
            return {}
    
    def get_prompt_status(self, prompt_id: str) -> Dict[str, Any]:
        """Get the current status of a prompt execution"""
        try:
            # Check if prompt is in history (completed)
            try:
                history = self.get_history(prompt_id)
                if history and isinstance(history, dict) and prompt_id in history:
                    return {
                        "status": "completed",
                        "prompt_id": prompt_id,
                        "message": "Execution completed successfully"
                    }
            except Exception as e:
                logger.debug(f"Could not check history for prompt {prompt_id}: {e}")
            
            # Check if prompt is in queue (running)
            try:
                queue = self.get_queue()
                if queue and isinstance(queue, dict):
                    queue_pending = queue.get("queue_pending", [])
                    queue_running = queue.get("queue_running", [])
                    
                    # Check pending queue
                    if isinstance(queue_pending, list):
                        for item in queue_pending:
                            if isinstance(item, (list, tuple)) and len(item) > 1:
                                if item[1] == prompt_id:
                                    return {
                                        "status": "pending",
                                        "prompt_id": prompt_id,
                                        "message": "Waiting in queue",
                                        "position": queue_pending.index(item) + 1
                                    }
                    
                    # Check running queue
                    if isinstance(queue_running, list):
                        for item in queue_running:
                            if isinstance(item, (list, tuple)) and len(item) > 1:
                                if item[1] == prompt_id:
                                    return {
                                        "status": "running",
                                        "prompt_id": prompt_id,
                                        "message": "Currently executing"
                                    }
            except Exception as e:
                logger.debug(f"Could not check queue for prompt {prompt_id}: {e}")
            
            # Prompt not found in any queue or history
            return {
                "status": "not_found",
                "prompt_id": prompt_id,
                "message": "Prompt not found"
            }
            
        except Exception as e:
            logger.error(f"Failed to get prompt status: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "prompt_id": prompt_id,
                "message": f"Error checking status: {str(e)}"
            }
    
    def get_prompt_progress(self, prompt_id: str) -> Dict[str, Any]:
        """Get detailed progress information for a prompt"""
        try:
            status = self.get_prompt_status(prompt_id)
            
            # Ensure status is a dict
            if not isinstance(status, dict):
                return {
                    "status": "error",
                    "prompt_id": prompt_id,
                    "progress": 0,
                    "message": "Invalid status response"
                }
            
            status_value = status.get("status", "unknown")
            
            if status_value == "completed":
                # Get execution result
                try:
                    result = self._get_execution_result(prompt_id)
                except Exception as e:
                    logger.debug(f"Could not get execution result: {e}")
                    result = None
                return {
                    "status": "completed",
                    "prompt_id": prompt_id,
                    "progress": 100,
                    "message": "Execution completed",
                    "result": result
                }
            elif status_value == "running":
                # For running status, we'll use a simple approach without trying to get real-time progress
                # since ComfyUI's progress endpoint may not be available or reliable
                return {
                    "status": "running",
                    "prompt_id": prompt_id,
                    "progress": 0,  # We'll just show "running" status without percentage
                    "message": "Currently executing workflow"
                }
            elif status_value == "pending":
                return {
                    "status": "pending",
                    "prompt_id": prompt_id,
                    "progress": 10,
                    "message": f"Waiting in queue (position {status.get('position', '?')})"
                }
            else:
                # Return the status dict as-is, but ensure it has required fields
                return {
                    "status": status_value,
                    "prompt_id": prompt_id,
                    "progress": 0,
                    "message": status.get("message", "Unknown status")
                }
                
        except Exception as e:
            logger.error(f"Failed to get prompt progress: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "prompt_id": prompt_id,
                "progress": 0,
                "message": f"Error getting progress: {str(e)}"
            }
    
    def _get_realtime_progress(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """Get real-time progress from ComfyUI's progress endpoint"""
        try:
            response = requests.get(
                f"{self.server_url}/progress",
                headers=self._get_headers(),
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            
            # ComfyUI progress endpoint returns different formats:
            # Format 1: {"running": [[prompt_id, node_id, value, max], ...]}
            # Format 2: {"running": [{"prompt_id": ..., "value": ..., "max": ...}, ...]}
            # Format 3: Direct dict with value/max
            
            if isinstance(data, dict):
                # Check for "running" key
                if "running" in data:
                    running = data["running"]
                    if isinstance(running, list) and len(running) > 0:
                        # Check each item in the running list
                        for item in running:
                            if item is None:
                                continue
                            
                            # Format 1: List format [prompt_id, node_id, value, max, ...]
                            if isinstance(item, list) and len(item) > 0:
                                try:
                                    if item[0] == prompt_id:
                                        # Found our prompt, get progress info
                                        # ComfyUI progress format: [prompt_id, node_id, value, max, ...]
                                        if len(item) >= 4:
                                            value = item[2] if isinstance(item[2], (int, float)) else 0
                                            max_val = item[3] if isinstance(item[3], (int, float)) else 1.0
                                            return {
                                                "value": value,
                                                "max": max_val
                                            }
                                except (IndexError, TypeError) as e:
                                    logger.debug(f"Error parsing progress item: {e}")
                                    continue
                            
                            # Format 2: Dict format {"prompt_id": ..., "value": ..., "max": ...}
                            elif isinstance(item, dict):
                                if item.get("prompt_id") == prompt_id:
                                    return {
                                        "value": item.get("value", 0),
                                        "max": item.get("max", 1.0)
                                    }
                
                # Format 3: Direct dict with value/max (for current execution)
                if "value" in data and "max" in data:
                    # Check if this is for our prompt_id (might not have prompt_id in this format)
                    return {
                        "value": data.get("value", 0),
                        "max": data.get("max", 1.0)
                    }
            
            return None
        except Exception as e:
            logger.debug(f"Error getting real-time progress: {e}")
            return None
    
    def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        """Download an image from ComfyUI"""
        try:
            url = f"{self.server_url}/view"
            params = {
                "filename": filename,
                "subfolder": subfolder,
                "type": folder_type
            }
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get image: {e}")
            raise Exception(f"Failed to download image from ComfyUI: {e}")
    
    def get_queue(self) -> Dict[str, Any]:
        """Get current queue status"""
        try:
            response = requests.get(
                f"{self.server_url}/queue",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get queue: {e}")
            raise Exception(f"Failed to get ComfyUI queue: {e}")
    
    def interrupt(self) -> bool:
        """Interrupt current execution"""
        try:
            response = requests.post(
                f"{self.server_url}/interrupt",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to interrupt: {e}")
            return False
    
    async def wait_for_completion(self, prompt_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for prompt completion using WebSocket"""
        try:
            async with websockets.connect(f"{self.ws_url}/ws?clientId={uuid.uuid4()}") as websocket:
                start_time = asyncio.get_event_loop().time()
                
                while True:
                    # Check timeout
                    if asyncio.get_event_loop().time() - start_time > timeout:
                        raise TimeoutError(f"ComfyUI execution timed out after {timeout} seconds")
                    
                    # Receive message
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    
                    # Check if our prompt is complete
                    if data.get("type") == "execution_cached" or data.get("type") == "executing":
                        if data.get("data", {}).get("prompt_id") == prompt_id:
                            if data.get("type") == "execution_cached":
                                # Execution completed
                                return await self._get_execution_result(prompt_id)
                    
                    elif data.get("type") == "executed":
                        if data.get("data", {}).get("prompt_id") == prompt_id:
                            return await self._get_execution_result(prompt_id)
                    
                    elif data.get("type") == "execution_error":
                        if data.get("data", {}).get("prompt_id") == prompt_id:
                            error_msg = data.get("data", {}).get("error", {}).get("message", "Unknown error")
                            raise Exception(f"ComfyUI execution error: {error_msg}")
                            
        except websockets.exceptions.WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            # Fallback to polling
            return await self._poll_for_completion(prompt_id, timeout)
        except Exception as e:
            logger.error(f"Error waiting for completion: {e}")
            raise
    
    async def _poll_for_completion(self, prompt_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Fallback polling method for completion"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                history = self.get_history(prompt_id)
                if prompt_id in history:
                    return await self._get_execution_result(prompt_id)
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(2)
        
        raise TimeoutError(f"ComfyUI execution timed out after {timeout} seconds")
    
    async def _get_execution_result(self, prompt_id: str) -> Dict[str, Any]:
        """Get the execution result from history"""
        history = self.get_history(prompt_id)
        if not history or not isinstance(history, dict) or prompt_id not in history:
            raise Exception("Prompt not found in history")
        
        prompt_data = history[prompt_id]
        if not isinstance(prompt_data, dict):
            raise Exception("Invalid prompt data format in history")
        
        outputs = prompt_data.get("outputs", {})
        if not isinstance(outputs, dict):
            outputs = {}
        
        result = {
            "prompt_id": prompt_id,
            "status": "completed",
            "outputs": outputs,
            "images": []
        }
        
        # Extract image information
        for node_id, node_output in outputs.items():
            if isinstance(node_output, dict) and "images" in node_output:
                images = node_output["images"]
                if isinstance(images, list):
                    for img_info in images:
                        if isinstance(img_info, dict):
                            result["images"].append({
                                "filename": img_info.get("filename", ""),
                                "subfolder": img_info.get("subfolder", ""),
                                "type": img_info.get("type", "output")
                            })
        
        return result
    
    def modify_workflow_prompt(self, workflow: Dict[str, Any], positive_prompt: str, negative_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Modify workflow to update text prompts - handles API and original formats"""
        modified_workflow = json.loads(json.dumps(workflow))  # Deep copy
        
        # Handle different API formats
        if 'workflow' in modified_workflow and isinstance(modified_workflow['workflow'], dict):
            # API format with 'workflow' property
            workflow_data = modified_workflow['workflow']
        elif 'prompt' in modified_workflow and isinstance(modified_workflow['prompt'], dict):
            # ComfyUI's standard API format with 'prompt' property
            workflow_data = modified_workflow['prompt']
        else:
            # Handle original format (workflow is the root object)
            workflow_data = modified_workflow
        
        # Track nodes to update
        nodes_to_update = []
        
        # Find CLIPTextEncode nodes
        for node_id, node_data in workflow_data.items():
            if isinstance(node_data, dict) and node_data.get("class_type") in ["CLIPTextEncode", "CLIPTextEncodeSDXL"]:
                nodes_to_update.append((node_id, node_data))
        
        # Update positive prompt (first node found)
        if nodes_to_update and len(nodes_to_update) > 0:
            node_id, node_data = nodes_to_update[0]
            if "inputs" in node_data and "text" in node_data["inputs"]:
                node_data["inputs"]["text"] = positive_prompt
                print(f"Updated positive prompt in node {node_id}")
        
        # Update negative prompt (second node found, if negative_prompt is provided)
        if negative_prompt and len(nodes_to_update) > 1:
            node_id, node_data = nodes_to_update[1]
            if "inputs" in node_data and "text" in node_data["inputs"]:
                node_data["inputs"]["text"] = negative_prompt
                print(f"Updated negative prompt in node {node_id}")
        
        return modified_workflow
    
    def modify_workflow_image_input(self, workflow: Dict[str, Any], image_data: bytes, filename: str) -> Dict[str, Any]:
        """Modify workflow to use uploaded image as input - handles API and original formats"""
        modified_workflow = json.loads(json.dumps(workflow))  # Deep copy
        
        # Handle different API formats
        if 'workflow' in modified_workflow and isinstance(modified_workflow['workflow'], dict):
            # API format with 'workflow' property
            workflow_data = modified_workflow['workflow']
        elif 'prompt' in modified_workflow and isinstance(modified_workflow['prompt'], dict):
            # ComfyUI's standard API format with 'prompt' property
            workflow_data = modified_workflow['prompt']
        else:
            # Handle original format (workflow is the root object)
            workflow_data = modified_workflow
        
        # Find image input nodes and update them
        for node_id, node_data in workflow_data.items():
            if isinstance(node_data, dict):
                # Check if this is an image input node
                if node_data.get("class_type") in ["LoadImage", "LoadImageFromUrl"]:
                    if "inputs" in node_data:
                        node_data["inputs"]["image"] = filename
        
        return modified_workflow
    
    def modify_workflow_settings(self, workflow: Dict[str, Any], width: Optional[int] = None, height: Optional[int] = None, steps: Optional[int] = None, cfg_scale: Optional[float] = None, fps: Optional[int] = None, length: Optional[int] = None, seed: Optional[int] = None) -> Dict[str, Any]:
        """Modify workflow settings like dimensions, steps, CFG scale, fps, length, and seed"""
        print(f"modify_workflow_settings called with: width={width}, height={height}, steps={steps}, cfg_scale={cfg_scale}, fps={fps}, length={length}, seed={seed}")
        modified_workflow = json.loads(json.dumps(workflow))  # Deep copy
        
        # Handle different API formats
        if 'workflow' in modified_workflow and isinstance(modified_workflow['workflow'], dict):
            workflow_data = modified_workflow['workflow']
        elif 'prompt' in modified_workflow and isinstance(modified_workflow['prompt'], dict):
            workflow_data = modified_workflow['prompt']
        else:
            workflow_data = modified_workflow
        
        # Find and update nodes
        updated_count = 0
        for node_id, node_data in workflow_data.items():
            if isinstance(node_data, dict) and "inputs" in node_data:
                inputs = node_data["inputs"]
                
                # Update width in any node that has "width" parameter
                if width is not None and "width" in inputs:
                    old_width = inputs.get("width")
                    inputs["width"] = width
                    print(f"Updated width in node {node_id} ({node_data.get('class_type', 'Unknown')}) from {old_width} to {width}")
                    updated_count += 1
                
                # Update height in any node that has "height" parameter
                if height is not None and "height" in inputs:
                    old_height = inputs.get("height")
                    inputs["height"] = height
                    print(f"Updated height in node {node_id} ({node_data.get('class_type', 'Unknown')}) from {old_height} to {height}")
                    updated_count += 1
                
                # Update Sampler nodes (steps and cfg)
                if node_data.get("class_type") in ["KSampler", "KSamplerAdvanced"]:
                    if steps is not None and "steps" in inputs:
                        old_steps = inputs.get("steps")
                        inputs["steps"] = steps
                        print(f"Updated steps in node {node_id} from {old_steps} to {steps}")
                        updated_count += 1
                    if cfg_scale is not None and "cfg" in inputs:
                        old_cfg = inputs.get("cfg")
                        inputs["cfg"] = cfg_scale
                        print(f"Updated CFG scale in node {node_id} from {old_cfg} to {cfg_scale}")
                        updated_count += 1
                    if seed is not None and "seed" in inputs:
                        old_seed = inputs.get("seed")
                        inputs["seed"] = seed
                        print(f"Updated seed in node {node_id} from {old_seed} to {seed}")
                        updated_count += 1
                
                # Update FPS in any node that has "fps" parameter (video-related nodes)
                if fps is not None and "fps" in inputs:
                    old_fps = inputs.get("fps")
                    # Only update if it's a numeric value or we're explicitly setting it
                    inputs["fps"] = fps
                    print(f"Updated fps in node {node_id} ({node_data.get('class_type', 'Unknown')}) from {old_fps} to {fps}")
                    updated_count += 1
                
                # Update length/frames in any node that has frame-related parameters
                if length is not None:
                    # Try common parameter names for video length/frames
                    for frame_param in ["frames", "max_frames", "num_frames", "length", "frame_count", "total_frames"]:
                        if frame_param in inputs:
                            old_value = inputs.get(frame_param)
                            inputs[frame_param] = length
                            print(f"Updated {frame_param}/length in node {node_id} ({node_data.get('class_type', 'Unknown')}) from {old_value} to {length}")
                            updated_count += 1
                            break  # Only update the first matching parameter
                
                # Also check for seed in any node (some nodes have seed as a general parameter)
                # Skip if we already updated seed in a KSampler node above
                if seed is not None and "seed" in inputs:
                    # Check if this is a KSampler node (already handled above)
                    is_sampler_node = node_data.get("class_type") in ["KSampler", "KSamplerAdvanced"]
                    if not is_sampler_node:
                        old_seed = inputs.get("seed")
                        inputs["seed"] = seed
                        print(f"Updated seed in node {node_id} ({node_data.get('class_type', 'Unknown')}) from {old_seed} to {seed}")
                        updated_count += 1
        
        print(f"modify_workflow_settings: Updated {updated_count} setting(s)")
        return modified_workflow
