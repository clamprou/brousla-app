// Simple workflow management utility
class WorkflowManager {
  constructor() {
    this.workflows = []
    this.userId = null
  }

  setUserId(userId) {
    this.userId = userId
    this.loadFromStorage()
  }

  getStorageKey() {
    if (!this.userId) {
      return null
    }
    return `userWorkflows_${this.userId}`
  }

  loadFromStorage() {
    try {
      const storageKey = this.getStorageKey()
      if (!storageKey) {
        this.workflows = []
        return
      }
      
      const stored = localStorage.getItem(storageKey)
      if (stored) {
        this.workflows = JSON.parse(stored)
        // Ensure all workflows have userId in metadata
        this.workflows = this.workflows.map(w => ({
          ...w,
          userId: w.userId || this.userId
        }))
      } else {
        this.workflows = []
      }
    } catch (error) {
      console.error('Error loading workflows from storage:', error)
      this.workflows = []
    }
  }

  saveToStorage() {
    try {
      const storageKey = this.getStorageKey()
      if (!storageKey) {
        console.warn('Cannot save workflows: no user ID set')
        return
      }
      
      // Ensure all workflows have userId in metadata before saving
      const workflowsToSave = this.workflows.map(w => ({
        ...w,
        userId: w.userId || this.userId
      }))
      
      localStorage.setItem(storageKey, JSON.stringify(workflowsToSave))
    } catch (error) {
      console.error('Error saving workflows to storage:', error)
    }
  }

  clearWorkflows() {
    // Clear in-memory workflows only, don't delete from localStorage
    // This allows workflows to persist when user logs out and logs back in
    this.workflows = []
  }

  clearWorkflowsFromStorage() {
    // Use this method only if you actually want to delete workflows from storage
    const storageKey = this.getStorageKey()
    if (storageKey) {
      localStorage.removeItem(storageKey)
      this.workflows = []
    }
  }

  addWorkflow(workflowData) {
    const newWorkflow = {
      id: Date.now().toString(),
      name: workflowData.name || this.generateWorkflowName(workflowData.concept),
      description: workflowData.description || workflowData.concept,
      concept: workflowData.concept,
      numberOfClips: workflowData.numberOfClips,
      videoWorkflowFile: workflowData.videoWorkflowFile,
      imageWorkflowFile: workflowData.imageWorkflowFile,
      schedule: workflowData.schedule || 1, // Default to 1 minute if not provided
      negativePrompt: workflowData.negativePrompt || '',
      width: workflowData.width || '',
      height: workflowData.height || '',
      fps: workflowData.fps || '',
      steps: workflowData.steps || '',
      length: workflowData.length || '',
      seed: workflowData.seed || '',
      status: 'draft',
      lastRun: null,
      userId: this.userId, // Add userId to workflow metadata
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }

    this.workflows.unshift(newWorkflow) // Add to beginning
    this.saveToStorage()
    
    // Dispatch event to notify other components
    window.dispatchEvent(new CustomEvent('workflowsUpdated', { 
      detail: { workflows: [...this.workflows] } 
    }))

    return newWorkflow
  }

  generateWorkflowName(concept) {
    // Generate a name based on the concept
    const words = concept.split(' ').slice(0, 4)
    return words.join(' ') + (words.length < 4 ? ' Workflow' : '')
  }

  updateWorkflow(id, workflowData) {
    const workflowIndex = this.workflows.findIndex(w => w.id === id)
    if (workflowIndex === -1) return null

    const existingWorkflow = this.workflows[workflowIndex]
    const updatedWorkflow = {
      ...existingWorkflow,
      name: workflowData.name || existingWorkflow.name,
      description: workflowData.description || workflowData.concept || existingWorkflow.description,
      concept: workflowData.concept || existingWorkflow.concept,
      numberOfClips: workflowData.numberOfClips !== undefined ? workflowData.numberOfClips : existingWorkflow.numberOfClips,
      videoWorkflowFile: workflowData.videoWorkflowFile || existingWorkflow.videoWorkflowFile,
      imageWorkflowFile: workflowData.imageWorkflowFile || existingWorkflow.imageWorkflowFile,
      schedule: workflowData.schedule !== undefined ? workflowData.schedule : (existingWorkflow.schedule || 1),
      negativePrompt: workflowData.negativePrompt !== undefined ? workflowData.negativePrompt : (existingWorkflow.negativePrompt || ''),
      width: workflowData.width !== undefined ? workflowData.width : (existingWorkflow.width || ''),
      height: workflowData.height !== undefined ? workflowData.height : (existingWorkflow.height || ''),
      fps: workflowData.fps !== undefined ? workflowData.fps : (existingWorkflow.fps || ''),
      steps: workflowData.steps !== undefined ? workflowData.steps : (existingWorkflow.steps || ''),
      length: workflowData.length !== undefined ? workflowData.length : (existingWorkflow.length || ''),
      seed: workflowData.seed !== undefined ? workflowData.seed : (existingWorkflow.seed || ''),
      updatedAt: new Date().toISOString()
    }

    this.workflows[workflowIndex] = updatedWorkflow
    this.saveToStorage()
    
    // Dispatch event to notify other components
    window.dispatchEvent(new CustomEvent('workflowsUpdated', { 
      detail: { workflows: [...this.workflows] } 
    }))

    return updatedWorkflow
  }

  deleteWorkflow(id) {
    this.workflows = this.workflows.filter(w => w.id !== id)
    this.saveToStorage()
    
    // Dispatch event to notify other components
    window.dispatchEvent(new CustomEvent('workflowsUpdated', { 
      detail: { workflows: [...this.workflows] } 
    }))
  }

  getWorkflows() {
    // Only return workflows for the current user
    if (!this.userId) {
      return []
    }
    return [...this.workflows].filter(w => w.userId === this.userId)
  }

  getWorkflowById(id) {
    const workflow = this.workflows.find(w => w.id === id)
    // Ensure workflow belongs to current user
    if (workflow && workflow.userId === this.userId) {
      return workflow
    }
    return null
  }
}

// Create singleton instance
export const workflowManager = new WorkflowManager()
