// Settings management utility
class SettingsManager {
  constructor() {
    this.settings = {
      comfyuiPath: null,
      comfyuiServer: 'http://localhost:8188',
      openaiApiKey: null,
      defaultWorkflow: null
    }
    this.loadFromStorage()
  }

  loadFromStorage() {
    try {
      const stored = localStorage.getItem('appSettings')
      if (stored) {
        this.settings = { ...this.settings, ...JSON.parse(stored) }
      }
    } catch (error) {
      console.error('Error loading settings from storage:', error)
    }
  }

  saveToStorage() {
    try {
      localStorage.setItem('appSettings', JSON.stringify(this.settings))
    } catch (error) {
      console.error('Error saving settings to storage:', error)
    }
  }

  setComfyUIPath(path) {
    this.settings.comfyuiPath = path
    this.saveToStorage()
    
    // Dispatch event to notify components
    window.dispatchEvent(new CustomEvent('settingsUpdated', { 
      detail: { settings: { ...this.settings } } 
    }))
  }

  getComfyUIPath() {
    return this.settings.comfyuiPath
  }

  getSettings() {
    return { ...this.settings }
  }

  setSetting(key, value) {
    this.settings[key] = value
    this.saveToStorage()
    
    // Dispatch event to notify components
    window.dispatchEvent(new CustomEvent('settingsUpdated', { 
      detail: { settings: { ...this.settings } } 
    }))
  }
}

// Create singleton instance
export const settingsManager = new SettingsManager()
