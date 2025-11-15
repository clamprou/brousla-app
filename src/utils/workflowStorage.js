// Workflow storage API service
const BACKEND_URL = 'http://127.0.0.1:8000'

/**
 * Get all stored workflows
 * @returns {Promise<Array>} Array of workflow metadata objects
 */
export async function getStoredWorkflows() {
  try {
    const response = await fetch(`${BACKEND_URL}/stored-workflows`)
    const data = await response.json()
    
    if (data.success) {
      return data.workflows || []
    } else {
      console.error('Failed to get stored workflows:', data.error)
      return []
    }
  } catch (error) {
    console.error('Error fetching stored workflows:', error)
    return []
  }
}

/**
 * Save a workflow
 * @param {string} name - Workflow name
 * @param {string} description - Optional description
 * @param {Object} workflowFile - Workflow file object with json, fileName, etc.
 * @returns {Promise<Object|null>} Saved workflow metadata or null on error
 */
export async function saveWorkflow(name, description, workflowFile) {
  try {
    const formData = new FormData()
    
    // Create a Blob from the workflow JSON
    const workflowBlob = new Blob([JSON.stringify(workflowFile.json)], { type: 'application/json' })
    formData.append('workflow_file', workflowBlob, workflowFile.fileName || 'workflow.json')
    formData.append('name', name || '')
    formData.append('description', description || '')
    
    const response = await fetch(`${BACKEND_URL}/stored-workflows`, {
      method: 'POST',
      body: formData
    })
    
    const data = await response.json()
    
    if (data.success) {
      return data.workflow
    } else {
      console.error('Failed to save workflow:', data.error)
      return null
    }
  } catch (error) {
    console.error('Error saving workflow:', error)
    return null
  }
}

/**
 * Load a stored workflow by ID
 * @param {string} workflowId - Workflow ID
 * @returns {Promise<Object|null>} Workflow object with json and metadata, or null on error
 */
export async function loadStoredWorkflow(workflowId) {
  try {
    const response = await fetch(`${BACKEND_URL}/stored-workflows/${workflowId}`)
    const data = await response.json()
    
    if (data.success) {
      return {
        json: data.workflow,
        metadata: data.metadata
      }
    } else {
      console.error('Failed to load workflow:', data.error)
      return null
    }
  } catch (error) {
    console.error('Error loading workflow:', error)
    return null
  }
}

/**
 * Delete a stored workflow
 * @param {string} workflowId - Workflow ID
 * @returns {Promise<boolean>} True if successful, false otherwise
 */
export async function deleteStoredWorkflow(workflowId) {
  try {
    const response = await fetch(`${BACKEND_URL}/stored-workflows/${workflowId}`, {
      method: 'DELETE'
    })
    
    const data = await response.json()
    
    if (data.success) {
      return true
    } else {
      console.error('Failed to delete workflow:', data.error)
      return false
    }
  } catch (error) {
    console.error('Error deleting workflow:', error)
    return false
  }
}

/**
 * Update workflow metadata (name, description)
 * @param {string} workflowId - Workflow ID
 * @param {string} name - New name (optional)
 * @param {string} description - New description (optional)
 * @returns {Promise<Object|null>} Updated workflow metadata or null on error
 */
export async function updateWorkflowMetadata(workflowId, name, description) {
  try {
    const updates = {}
    if (name !== undefined) updates.name = name
    if (description !== undefined) updates.description = description
    
    const response = await fetch(`${BACKEND_URL}/stored-workflows/${workflowId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(updates)
    })
    
    const data = await response.json()
    
    if (data.success) {
      return data.workflow
    } else {
      console.error('Failed to update workflow:', data.error)
      return null
    }
  } catch (error) {
    console.error('Error updating workflow:', error)
    return null
  }
}

/**
 * Mark a workflow as used (update lastUsed timestamp)
 * @param {string} workflowId - Workflow ID
 * @returns {Promise<boolean>} True if successful, false otherwise
 */
export async function markWorkflowUsed(workflowId) {
  try {
    const response = await fetch(`${BACKEND_URL}/stored-workflows/${workflowId}/use`, {
      method: 'POST'
    })
    
    const data = await response.json()
    
    if (data.success) {
      return true
    } else {
      console.error('Failed to mark workflow as used:', data.error)
      return false
    }
  } catch (error) {
    console.error('Error marking workflow as used:', error)
    return false
  }
}

