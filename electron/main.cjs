const { app, BrowserWindow, ipcMain, dialog, Menu, shell } = require('electron')
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
    // Enable remote debugging for renderer process (for VS Code attachment)
    // This allows VS Code to attach to the renderer process via Chrome DevTools Protocol
    mainWindow.webContents.on('did-frame-finish-load', () => {
      // Enable remote debugging
      if (process.env.ELECTRON_ENABLE_LOGGING) {
        console.log('Renderer process ready for debugging')
      }
    })
    
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
  const serverPath = path.join(process.cwd(), 'workflow-server', 'main.py')
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
  pythonProcess = spawn(pythonCmd, [serverPath], { stdio: 'inherit' })
}

function stopPython() {
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
  }
}

// Register custom protocol handler for deep links
const PROTOCOL_NAME = 'brousla'

// Register the protocol (must be called before app is ready)
if (process.defaultApp) {
  if (process.argv.length >= 2) {
    app.setAsDefaultProtocolClient(PROTOCOL_NAME, process.execPath, [path.resolve(process.argv[1])])
  }
} else {
  app.setAsDefaultProtocolClient(PROTOCOL_NAME)
}

// Handle protocol URLs (Windows - when app is already running)
const gotTheLock = app.requestSingleInstanceLock()
if (!gotTheLock) {
  app.quit()
} else {
  app.on('second-instance', (event, commandLine, workingDirectory) => {
    // Someone tried to run a second instance, focus our window instead
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.focus()
    }
    
    // Check for protocol URL in command line (Windows)
    const url = commandLine.find(arg => arg.startsWith(`${PROTOCOL_NAME}://`))
    if (url) {
      handleProtocolUrl(url)
    }
  })
  
  // Handle protocol URL when app is launched from protocol (Windows)
  // Check command line arguments for protocol URL
  const protocolUrl = process.argv.find(arg => arg.startsWith(`${PROTOCOL_NAME}://`))
  if (protocolUrl) {
    // Store it to handle after app is ready
    process.env.PROTOCOL_URL = protocolUrl
  }
}

function handleProtocolUrl(url) {
  if (!url || !url.startsWith(`${PROTOCOL_NAME}://`)) return
  
  // Parse the URL manually (URL might not be available in all Node contexts)
  const urlWithoutProtocol = url.replace(`${PROTOCOL_NAME}://`, '')
  const [pathPart, queryPart] = urlWithoutProtocol.split('?')
  const params = new URLSearchParams(queryPart || '')
  
  // Ensure window is created and focused
  if (!mainWindow) {
    createWindow()
  } else {
    if (mainWindow.isMinimized()) mainWindow.restore()
    mainWindow.focus()
  }
  
  // Handle email confirmation
  if (pathPart === 'email-confirmation') {
    const queryString = queryPart ? `?${queryPart}` : ''
    
    // Small delay to ensure window is ready
    setTimeout(() => {
      if (mainWindow) {
        if (getIsDev()) {
          // In development, use dev server URL
          const devServerPort = process.env.VITE_DEV_SERVER_PORT || '5173'
          const targetUrl = `http://localhost:${devServerPort}/email-confirmation${queryString}`
          mainWindow.loadURL(targetUrl)
        } else {
          // In production, use hash-based routing (works with file:// protocol)
          // Escape the query string for use in JavaScript
          const escapedQueryString = queryString.replace(/'/g, "\\'").replace(/\n/g, "\\n").replace(/\r/g, "\\r")
          mainWindow.webContents.executeJavaScript(`
            // Set hash with route and query params
            window.location.hash = '/email-confirmation${escapedQueryString}';
            // Also dispatch a custom event to trigger React router if needed
            window.dispatchEvent(new PopStateEvent('popstate'));
          `)
        }
      }
    }, 100)
  }
  // Handle Google OAuth callback
  else if (pathPart === 'google-oauth-callback') {
    const queryString = queryPart ? `?${queryPart}` : ''
    
    // Small delay to ensure window is ready
    setTimeout(() => {
      if (mainWindow) {
        if (getIsDev()) {
          // In development, use dev server URL
          const devServerPort = process.env.VITE_DEV_SERVER_PORT || '5173'
          const targetUrl = `http://localhost:${devServerPort}/google-oauth-callback${queryString}`
          mainWindow.loadURL(targetUrl)
        } else {
          // In production, use hash-based routing (works with file:// protocol)
          // Escape the query string for use in JavaScript
          const escapedQueryString = queryString.replace(/'/g, "\\'").replace(/\n/g, "\\n").replace(/\r/g, "\\r")
          mainWindow.webContents.executeJavaScript(`
            // Set hash with route and query params
            window.location.hash = '/google-oauth-callback${escapedQueryString}';
            // Also dispatch a custom event to trigger React router if needed
            window.dispatchEvent(new PopStateEvent('popstate'));
          `)
        }
      }
    }, 100)
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
  
  // Handle protocol URL on macOS (when app launches from protocol)
  if (process.platform === 'darwin') {
    app.on('open-url', (event, url) => {
      event.preventDefault()
      handleProtocolUrl(url)
    })
  }
  
  // Handle protocol URL stored from command line (Windows)
  if (process.env.PROTOCOL_URL) {
    handleProtocolUrl(process.env.PROTOCOL_URL)
    delete process.env.PROTOCOL_URL
  }
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
// Shell handlers
ipcMain.handle('shell:openExternal', async (event, url) => {
  try {
    await shell.openExternal(url)
    return { success: true }
  } catch (error) {
    console.error('Error opening external URL:', error)
    return { success: false, error: error.message }
  }
})

// Create Stripe checkout window
ipcMain.handle('stripe:openCheckout', async (event, url) => {
  try {
    const checkoutWindow = new BrowserWindow({
      width: 800,
      height: 900,
      parent: mainWindow,
      modal: false,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true
      },
      title: 'Complete Your Subscription'
    })

    // Load the Stripe checkout URL
    await checkoutWindow.loadURL(url)

    // Handle window close
    checkoutWindow.on('closed', () => {
      // Notify renderer that checkout window was closed
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('stripe:checkout-closed')
      }
    })

    // Listen for navigation to success/cancel URLs
    checkoutWindow.webContents.on('did-navigate', (event, navigationUrl) => {
      if (navigationUrl.includes('session_id=')) {
        // Success - notify renderer
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('stripe:checkout-success', navigationUrl)
        }
        checkoutWindow.close()
      } else if (navigationUrl.includes('cancelled=true')) {
        // Cancelled - notify renderer
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('stripe:checkout-cancelled')
        }
        checkoutWindow.close()
      }
    })

    return { success: true, windowId: checkoutWindow.id }
  } catch (error) {
    console.error('Error opening Stripe checkout window:', error)
    return { success: false, error: error.message }
  }
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


