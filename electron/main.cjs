const { app, BrowserWindow, ipcMain, dialog, Menu } = require('electron')
const path = require('path')
const { existsSync, statSync } = require('fs')
const { spawn } = require('child_process')

let mainWindow = null
let pythonProcess = null

function getIsDev() {
  // Check if VITE_DEV_SERVER_PORT is set OR if we're not in production
  return process.env.VITE_DEV_SERVER_PORT !== undefined || !app.isPackaged
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
    // Always open DevTools in development for debugging
    // Only skip if VS Code debugger is attaching
    if (!process.env.VSCODE_INSPECTOR_OPTIONS && !process.env.VSCODE_CWD) {
      // Small delay to check if debugger is attaching
      setTimeout(() => {
        if (mainWindow && !mainWindow.webContents.isDevToolsOpened()) {
          // Only open if VS Code debugger hasn't attached yet
          mainWindow.webContents.openDevTools({ mode: 'detach' })
        }
      }, 1000)
    }
    
    // Add keyboard shortcut to toggle DevTools (F12 or Ctrl+Shift+I / Cmd+Option+I)
    mainWindow.webContents.on('before-input-event', (event, input) => {
      if (input.key === 'F12' || 
          (input.control && input.shift && input.key.toLowerCase() === 'i') ||
          (input.meta && input.alt && input.key.toLowerCase() === 'i')) {
        if (mainWindow.webContents.isDevToolsOpened()) {
          mainWindow.webContents.closeDevTools()
        } else {
          mainWindow.webContents.openDevTools({ mode: 'detach' })
        }
      }
    })
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
  // Only start Python server in production (in dev, it's started by dev:backend)
  if (!getIsDev()) {
    startPython()
  }
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
  // Only stop Python if we started it (production mode)
  if (!getIsDev()) {
    stopPython()
  }
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

// Folder selection handler
ipcMain.handle('dialog:selectFolder', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    title: 'Select ComfyUI Folder',
    buttonLabel: 'Select Folder'
  })
  return result
})

// ComfyUI folder validation handler
ipcMain.handle('comfyui:validateFolder', async (event, folderPath) => {
  try {
    if (!folderPath || typeof folderPath !== 'string') {
      return {
        isValid: false,
        missingItems: ['Invalid folder path'],
        message: 'Invalid folder path provided'
      }
    }

    // Check if the folder exists
    if (!existsSync(folderPath)) {
      return {
        isValid: false,
        missingItems: ['Folder does not exist'],
        message: 'Selected folder does not exist'
      }
    }

    // Check if it's actually a directory
    const stats = statSync(folderPath)
    if (!stats.isDirectory()) {
      return {
        isValid: false,
        missingItems: ['Not a directory'],
        message: 'Selected path is not a directory'
      }
    }

    // Check for main.py inside ComfyUI subfolder
    const comfyUIPath = path.join(folderPath, 'ComfyUI')
    const mainPyPath = path.join(comfyUIPath, 'main.py')
    
    // First check if ComfyUI folder exists
    if (!existsSync(comfyUIPath)) {
      return {
        isValid: false,
        missingItems: ['ComfyUI folder'],
        message: 'ComfyUI folder not found in selected directory'
      }
    }
    
    // Then check if main.py exists inside ComfyUI folder
    if (!existsSync(mainPyPath)) {
      return {
        isValid: false,
        missingItems: ['main.py'],
        message: 'main.py file not found in ComfyUI folder'
      }
    }

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
      message: `Error validating ComfyUI folder: ${error.message}`
    }
  }
})


