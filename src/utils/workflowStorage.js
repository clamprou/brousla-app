// Workflow storage API service
const BACKEND_URL = 'http://127.0.0.1:8000'

/**
 * Get all stored workflows for the current user
 * @param {string} userId - User ID
 * @returns {Promise<Array>} Array of workflow metadata objects
 */
export async function getStoredWorkflows(userId) {
  if (!userId) {
    console.warn('getStoredWorkflows called without userId')
    return []
  }
  
  try {
    const response = await fetch(`${BACKEND_URL}/stored-workflows`, {
      headers: {
        'X-User-Id': userId
      }
    })
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
 * @param {string} userId - User ID
 * @returns {Promise<Object|null>} Saved workflow metadata or null on error
 */
export async function saveWorkflow(name, description, workflowFile, userId) {
  if (!userId) {
    console.warn('saveWorkflow called without userId')
    return null
  }
  
  try {
    const formData = new FormData()
    
    // Create a Blob from the workflow JSON
    const workflowBlob = new Blob([JSON.stringify(workflowFile.json)], { type: 'application/json' })
    formData.append('workflow_file', workflowBlob, workflowFile.fileName || 'workflow.json')
    formData.append('name', name || '')
    formData.append('description', description || '')
    
    const response = await fetch(`${BACKEND_URL}/stored-workflows`, {
      method: 'POST',
      headers: {
        'X-User-Id': userId
      },
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
 * @param {string} userId - User ID
 * @returns {Promise<Object|null>} Workflow object with json and metadata, or null on error
 */
export async function loadStoredWorkflow(workflowId, userId) {
  if (!userId) {
    console.warn('loadStoredWorkflow called without userId')
    return null
  }
  
  try {
    const response = await fetch(`${BACKEND_URL}/stored-workflows/${workflowId}`, {
      headers: {
        'X-User-Id': userId
      }
    })
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
 * @param {string} userId - User ID
 * @returns {Promise<boolean>} True if successful, false otherwise
 */
export async function deleteStoredWorkflow(workflowId, userId) {
  if (!userId) {
    console.warn('deleteStoredWorkflow called without userId')
    return false
  }
  
  try {
    const response = await fetch(`${BACKEND_URL}/stored-workflows/${workflowId}`, {
      method: 'DELETE',
      headers: {
        'X-User-Id': userId
      }
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
 * @param {string} userId - User ID
 * @returns {Promise<Object|null>} Updated workflow metadata or null on error
 */
export async function updateWorkflowMetadata(workflowId, name, description, userId) {
  if (!userId) {
    console.warn('updateWorkflowMetadata called without userId')
    return null
  }
  
  try {
    const updates = {}
    if (name !== undefined) updates.name = name
    if (description !== undefined) updates.description = description
    
    const response = await fetch(`${BACKEND_URL}/stored-workflows/${workflowId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Id': userId
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
 * @param {string} userId - User ID
 * @returns {Promise<boolean>} True if successful, false otherwise
 */
export async function markWorkflowUsed(workflowId, userId) {
  if (!userId) {
    console.warn('markWorkflowUsed called without userId')
    return false
  }
  
  try {
    const response = await fetch(`${BACKEND_URL}/stored-workflows/${workflowId}/use`, {
      method: 'POST',
      headers: {
        'X-User-Id': userId
      }
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

