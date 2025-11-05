// Simple workflow management utility
class WorkflowManager {
  constructor() {
    this.workflows = []
    this.loadFromStorage()
  }

  loadFromStorage() {
    try {
      const stored = localStorage.getItem('userWorkflows')
      if (stored) {
        this.workflows = JSON.parse(stored)
      }
    } catch (error) {
      console.error('Error loading workflows from storage:', error)
      this.workflows = []
    }
  }

  saveToStorage() {
    try {
      localStorage.setItem('userWorkflows', JSON.stringify(this.workflows))
    } catch (error) {
      console.error('Error saving workflows to storage:', error)
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
    return [...this.workflows]
  }

  getWorkflowById(id) {
    return this.workflows.find(w => w.id === id)
  }
}

// Create singleton instance
export const workflowManager = new WorkflowManager()
