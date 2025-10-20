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
      clipDuration: workflowData.clipDuration,
      numberOfClips: workflowData.numberOfClips,
      videoModel: workflowData.videoModel,
      imageModel: workflowData.imageModel,
      status: 'draft',
      lastRun: null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      steps: 2 // Basic workflow: generate images + create videos
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
      clipDuration: workflowData.clipDuration || existingWorkflow.clipDuration,
      numberOfClips: workflowData.numberOfClips || existingWorkflow.numberOfClips,
      videoModel: workflowData.videoModel || existingWorkflow.videoModel,
      imageModel: workflowData.imageModel || existingWorkflow.imageModel,
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
