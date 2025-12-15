"""
Background scheduler for AI Workflows.
Checks active workflows and executes them on schedule.
"""
import threading
import time
import json
from datetime import datetime
from typing import Dict, Optional, Callable


class WorkflowScheduler:
    """Background scheduler that manages workflow execution"""
    
    def __init__(
        self,
        get_workflows_callback: Callable[[], list],
        get_workflow_state_callback: Callable[[str], dict],
        update_workflow_state_callback: Callable[[str, dict], None],
        execute_workflow_callback: Callable[[dict, str], dict],
        get_preferences_callback: Optional[Callable[[], dict]] = None
    ):
        """
        Initialize the scheduler.
        
        Args:
            get_workflows_callback: Function that returns list of all workflows
            get_workflow_state_callback: Function to get workflow state (workflow_id -> state)
            update_workflow_state_callback: Function to update workflow state (workflow_id, updates)
            execute_workflow_callback: Function to execute a workflow (workflow, workflow_id -> result)
            get_preferences_callback: Optional function to get preferences (for ComfyUI settings)
        """
        self.get_workflows = get_workflows_callback
        self.get_workflow_state = get_workflow_state_callback
        self.update_workflow_state = update_workflow_state_callback
        self.execute_workflow = execute_workflow_callback
        self.get_preferences = get_preferences_callback or (lambda: {})
        
        self.running = False
        self.thread = None
        self.check_interval = 60  # Check every 60 seconds
    
    def start(self):
        """Start the scheduler in a background thread"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print("Workflow scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("Workflow scheduler stopped")
    
    def _run(self):
        """Main scheduler loop"""
        while self.running:
            try:
                self._check_and_execute_workflows()
            except Exception as e:
                print(f"Error in workflow scheduler: {e}")
                import traceback
                traceback.print_exc()
            
            # Sleep for check interval
            time.sleep(self.check_interval)
    
    def _check_and_execute_workflows(self):
        """Check all workflows and execute those that are due"""
        workflows = self.get_workflows()
        current_time = datetime.utcnow()
        
        if workflows:
            print(f"Scheduler checking {len(workflows)} workflow(s) at {current_time.isoformat()}")
        
        for workflow in workflows:
            workflow_id = workflow.get('id')
            if not workflow_id:
                continue
            
            try:
                # Get workflow state
                state = self.get_workflow_state(workflow_id)
                
                # Skip if not active, already running, or cancelled
                if not state.get('isActive', False) or state.get('isRunning', False) or state.get('cancelled', False):
                    continue
                
                # Check if it's time to execute
                next_execution = state.get('nextExecutionTime')
                
                # Only execute if nextExecutionTime is set and in the past
                # If nextExecutionTime is None, it means the workflow was just activated
                # and will be executed by the activation endpoint, not by the scheduler
                should_execute = False
                if next_execution is not None:
                    try:
                        next_execution_time = datetime.fromisoformat(next_execution.replace('Z', '+00:00'))
                        if current_time >= next_execution_time.replace(tzinfo=None):
                            should_execute = True
                    except (ValueError, AttributeError):
                        # Invalid date format - skip this execution, let it be handled by activation
                        should_execute = False
                # If nextExecutionTime is None, don't execute here - it's being handled by activation
                
                if should_execute:
                    print(f"[SCHEDULER] Executing scheduled workflow: {workflow_id} ({workflow.get('name', 'Unnamed')}) - nextExecutionTime was {next_execution}")
                    self._execute_workflow_async(workflow, workflow_id)
                else:
                    # Log why it's not executing
                    if next_execution is None:
                        print(f"[SCHEDULER] Workflow {workflow_id} skipped: nextExecutionTime is None (handled by activation)")
                    else:
                        try:
                            next_execution_time = datetime.fromisoformat(next_execution.replace('Z', '+00:00'))
                            if current_time < next_execution_time.replace(tzinfo=None):
                                time_until = (next_execution_time.replace(tzinfo=None) - current_time).total_seconds() / 60
                                print(f"[SCHEDULER] Workflow {workflow_id} skipped: nextExecutionTime is {time_until:.1f} minutes in the future")
                        except:
                            pass
            
            except Exception as e:
                print(f"Error checking workflow {workflow_id}: {e}")
                import traceback
                traceback.print_exc()
    
    def _execute_workflow_async(self, workflow: Dict, workflow_id: str):
        """Execute a workflow asynchronously in a separate thread"""
        # Set isRunning immediately to prevent duplicate executions
        # (execute_workflow will also set it, but this ensures it's set atomically)
        self.update_workflow_state(workflow_id, {"isRunning": True})
        
        def execute():
            try:
                # Execute the workflow (callback handles ComfyUI settings internally)
                result = self.execute_workflow(workflow, workflow_id)
                
                if result.get('success'):
                    print(f"Workflow {workflow_id} executed successfully")
                else:
                    print(f"Workflow {workflow_id} execution failed: {result.get('error', 'Unknown error')}")
            
            except Exception as e:
                print(f"Error executing workflow {workflow_id}: {e}")
                import traceback
                traceback.print_exc()
                
                # Ensure isRunning is set to False on error
                self.update_workflow_state(workflow_id, {"isRunning": False})
        
        # Execute in background thread
        thread = threading.Thread(target=execute, daemon=True)
        thread.start()


# Global scheduler instance (will be initialized in main.py)
scheduler = None


def get_scheduler() -> Optional[WorkflowScheduler]:
    """Get the global scheduler instance"""
    return scheduler


def initialize_scheduler(
    get_workflows_callback,
    get_workflow_state_callback,
    update_workflow_state_callback,
    execute_workflow_callback,
    get_preferences_callback=None
) -> WorkflowScheduler:
    """Initialize the global scheduler"""
    global scheduler
    scheduler = WorkflowScheduler(
        get_workflows_callback=get_workflows_callback,
        get_workflow_state_callback=get_workflow_state_callback,
        update_workflow_state_callback=update_workflow_state_callback,
        execute_workflow_callback=execute_workflow_callback,
        get_preferences_callback=get_preferences_callback
    )
    return scheduler

