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
      name: this.generateWorkflowName(workflowData.concept),
      description: workflowData.concept,
      concept: workflowData.concept,
      clipDuration: workflowData.clipDuration,
      numberOfClips: workflowData.numberOfClips,
      videoModel: workflowData.videoModel,
      imageModel: workflowData.imageModel,
      status: 'draft',
      lastRun: null,
      createdAt: new Date().toISOString(),
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
}

// Create singleton instance
export const workflowManager = new WorkflowManager()
