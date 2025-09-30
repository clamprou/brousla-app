import { app, BrowserWindow, ipcMain } from 'electron'
import path from 'path'
import { spawn } from 'child_process'

let mainWindow = null
let pythonProcess = null

function getIsDev() {
  return process.env.VITE_DEV_SERVER_PORT !== undefined
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      preload: path.join(process.cwd(), 'electron', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  const devServerPort = process.env.VITE_DEV_SERVER_PORT || '5173'
  if (getIsDev()) {
    mainWindow.loadURL(`http://localhost:${devServerPort}`)
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(path.join(process.cwd(), 'dist', 'index.html'))
  }
}

function startPython() {
  const serverPath = path.join(process.cwd(), 'server', 'main.py')
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
  pythonProcess = spawn(pythonCmd, [serverPath], { stdio: 'inherit' })
}

function stopPython() {
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
  }
}

app.whenReady().then(() => {
  startPython()
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  stopPython()
})

ipcMain.handle('app:getVersion', () => app.getVersion())


