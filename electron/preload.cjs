const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  getVersion: () => ipcRenderer.invoke('app:getVersion'),
  minimizeWindow: () => ipcRenderer.invoke('window:minimize'),
  closeWindow: () => ipcRenderer.invoke('window:close'),
  selectFolder: () => ipcRenderer.invoke('dialog:selectFolder'),
  validateComfyUIFolder: (folderPath) => ipcRenderer.invoke('comfyui:validateFolder', folderPath),
  openExternal: (url) => ipcRenderer.invoke('shell:openExternal', url),
  openStripeCheckout: (url) => ipcRenderer.invoke('stripe:openCheckout', url),
  onStripeCheckoutSuccess: (callback) => {
    ipcRenderer.on('stripe:checkout-success', (event, url) => callback(url))
  },
  onStripeCheckoutCancelled: (callback) => {
    ipcRenderer.on('stripe:checkout-cancelled', () => callback())
  },
  onStripeCheckoutClosed: (callback) => {
    ipcRenderer.on('stripe:checkout-closed', () => callback())
  },
  removeStripeListeners: () => {
    ipcRenderer.removeAllListeners('stripe:checkout-success')
    ipcRenderer.removeAllListeners('stripe:checkout-cancelled')
    ipcRenderer.removeAllListeners('stripe:checkout-closed')
  }
})


