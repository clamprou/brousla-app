const { app, BrowserWindow, ipcMain, dialog, Menu } = require('electron')
const path = require('path')
const { existsSync } = require('fs')
const { spawn } = require('child_process')

let mainWindow = null
let pythonProcess = null

function getIsDev() {
  return process.env.VITE_DEV_SERVER_PORT !== undefined
}

function createWindow() {
  const appBasePath = app.isPackaged ? process.resourcesPath : process.cwd()
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    frame: false, // Remove default frame for custom title bar
    titleBarStyle: 'hidden',
    webPreferences: {
      preload: path.join(appBasePath, 'electron', 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  const devServerPort = process.env.VITE_DEV_SERVER_PORT || '5173'
  if (getIsDev()) {
    mainWindow.loadURL(`http://localhost:${devServerPort}`)
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    const distIndexPath = path.join(appBasePath, 'dist', 'index.html')
    if (!existsSync(distIndexPath)) {
      dialog.showErrorBox(
        'Renderer build missing',
        'Could not find dist/index.html. Run "npm run dev" for development or "npm run build" to create production assets.'
      )
      app.quit()
      return
    }
    mainWindow.loadFile(distIndexPath)
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
  
  // Disable the default menu
  Menu.setApplicationMenu(null)

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

// Window control handlers
ipcMain.handle('window:minimize', () => {
  if (mainWindow) {
    mainWindow.minimize()
  }
})

ipcMain.handle('window:close', () => {
  if (mainWindow) {
    mainWindow.close()
  }
})


