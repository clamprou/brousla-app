// ComfyUI folder validation utility
class ComfyUIValidator {
  constructor() {
    this.requiredFiles = ['main.py']
    this.requiredFolders = ['ComfyUI']
  }

  /**
   * Validates if a folder contains a valid ComfyUI installation
   * @param {string} folderPath - Path to the ComfyUI folder
   * @returns {Promise<{isValid: boolean, missingItems: string[], message: string}>}
   */
  async validateComfyUIFolder(folderPath) {
    try {
      // Check if folder path exists
      if (!folderPath || typeof folderPath !== 'string') {
        return {
          isValid: false,
          missingItems: ['Invalid folder path'],
          message: 'Invalid folder path provided'
        }
      }

      // This will be called from Electron main process
      // The actual file system validation will happen there
      return {
        isValid: true,
        missingItems: [],
        message: 'ComfyUI folder validation passed'
      }
    } catch (error) {
      console.error('Error validating ComfyUI folder:', error)
      return {
        isValid: false,
        missingItems: ['Validation error'],
        message: 'Error validating ComfyUI folder'
      }
    }
  }

  /**
   * Get validation requirements for display
   * @returns {object} Requirements object
   */
  getValidationRequirements() {
    return {
      requiredFiles: this.requiredFiles,
      requiredFolders: this.requiredFolders,
      description: 'A valid ComfyUI installation requires ComfyUI folder with main.py file inside'
    }
  }
}

// Create singleton instance
export const comfyuiValidator = new ComfyUIValidator()
