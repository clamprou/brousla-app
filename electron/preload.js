import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
  getVersion: () => ipcRenderer.invoke('app:getVersion')
})


