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
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get history: {e}")
            raise Exception(f"Failed to get ComfyUI history: {e}")
    
    def get_prompt_status(self, prompt_id: str) -> Dict[str, Any]:
        """Get the current status of a prompt execution"""
        try:
            # Check if prompt is in history (completed)
            history = self.get_history(prompt_id)
            if prompt_id in history:
                return {
                    "status": "completed",
                    "prompt_id": prompt_id,
                    "message": "Execution completed successfully"
                }
            
            # Check if prompt is in queue (running)
            queue = self.get_queue()
            queue_pending = queue.get("queue_pending", [])
            queue_running = queue.get("queue_running", [])
            
            # Check pending queue
            for item in queue_pending:
                if item[1] == prompt_id:
                    return {
                        "status": "pending",
                        "prompt_id": prompt_id,
                        "message": "Waiting in queue",
                        "position": queue_pending.index(item) + 1
                    }
            
            # Check running queue
            for item in queue_running:
                if item[1] == prompt_id:
                    return {
                        "status": "running",
                        "prompt_id": prompt_id,
                        "message": "Currently executing"
                    }
            
            # Prompt not found in any queue or history
            return {
                "status": "not_found",
                "prompt_id": prompt_id,
                "message": "Prompt not found"
            }
            
        except Exception as e:
            logger.error(f"Failed to get prompt status: {e}")
            return {
                "status": "error",
                "prompt_id": prompt_id,
                "message": f"Error checking status: {str(e)}"
            }
    
    def get_prompt_progress(self, prompt_id: str) -> Dict[str, Any]:
        """Get detailed progress information for a prompt"""
        try:
            status = self.get_prompt_status(prompt_id)
            
            if status["status"] == "completed":
                # Get execution result
                result = self._get_execution_result(prompt_id)
                return {
                    "status": "completed",
                    "prompt_id": prompt_id,
                    "progress": 100,
                    "message": "Execution completed",
                    "result": result
                }
            elif status["status"] == "running":
                return {
                    "status": "running",
                    "prompt_id": prompt_id,
                    "progress": 50,  # Approximate progress for running
                    "message": "Currently executing workflow"
                }
            elif status["status"] == "pending":
                return {
                    "status": "pending",
                    "prompt_id": prompt_id,
                    "progress": 10,
                    "message": f"Waiting in queue (position {status.get('position', '?')})"
                }
            else:
                return status
                
        except Exception as e:
            logger.error(f"Failed to get prompt progress: {e}")
            return {
                "status": "error",
                "prompt_id": prompt_id,
                "progress": 0,
                "message": f"Error getting progress: {str(e)}"
            }
    
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
        if prompt_id not in history:
            raise Exception("Prompt not found in history")
        
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
    
    def modify_workflow_settings(self, workflow: Dict[str, Any], width: Optional[int], height: Optional[int], steps: Optional[int], cfg_scale: Optional[float]) -> Dict[str, Any]:
        """Modify workflow settings like dimensions, steps, and CFG scale"""
        print(f"modify_workflow_settings called with: width={width}, height={height}, steps={steps}, cfg_scale={cfg_scale}")
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
                
                # Update Empty Latent Image or similar nodes (width and height)
                if node_data.get("class_type") in ["EmptyLatentImage", "LatentFromBatch", "Wan22ImageToVideoLatent"]:
                    if width is not None and "width" in inputs:
                        old_width = inputs.get("width")
                        inputs["width"] = width
                        print(f"Updated width in node {node_id} from {old_width} to {width}")
                        updated_count += 1
                    if height is not None and "height" in inputs:
                        old_height = inputs.get("height")
                        inputs["height"] = height
                        print(f"Updated height in node {node_id} from {old_height} to {height}")
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
        
        print(f"modify_workflow_settings: Updated {updated_count} setting(s)")
        return modified_workflow
