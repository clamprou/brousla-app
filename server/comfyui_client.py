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
    
    def modify_workflow_prompt(self, workflow: Dict[str, Any], prompt_text: str) -> Dict[str, Any]:
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
        
        # Find and update text input nodes
        for node_id, node_data in workflow_data.items():
            if isinstance(node_data, dict):
                # Check if this is a text input node
                if node_data.get("class_type") in ["CLIPTextEncode", "CLIPTextEncodeSDXL"]:
                    # Update the text input
                    if "inputs" in node_data and "text" in node_data["inputs"]:
                        node_data["inputs"]["text"] = prompt_text
                
                # Also check for direct text nodes
                elif node_data.get("class_type") == "String":
                    if "inputs" in node_data and "string" in node_data["inputs"]:
                        node_data["inputs"]["string"] = prompt_text
        
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
