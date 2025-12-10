const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  getVersion: () => ipcRenderer.invoke('app:getVersion'),
  minimizeWindow: () => ipcRenderer.invoke('window:minimize'),
  closeWindow: () => ipcRenderer.invoke('window:close'),
  selectFolder: () => ipcRenderer.invoke('dialog:selectFolder'),
  validateComfyUIFolder: (folderPath) => ipcRenderer.invoke('comfyui:validateFolder', folderPath),
  openExternal: (url) => ipcRenderer.invoke('shell:openExternal', url)
})


