const { app, BrowserWindow, ipcMain, dialog, Menu, shell } = require('electron')
const path = require('path')
const { existsSync, statSync } = require('fs')
const { spawn } = require('child_process')

let mainWindow = null
let workflowServerProcess = null
let apiServerProcess = null

function getIsDev() {
  // Check if VITE_DEV_SERVER_PORT is set OR if we're not in production
  return process.env.VITE_DEV_SERVER_PORT !== undefined || !app.isPackaged
}

function getAppBasePath() {
  // In packaged apps, extraResources live under process.resourcesPath
  return app.isPackaged ? process.resourcesPath : process.cwd()
}

function createWindow() {
  const appPath = app.getAppPath()
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    frame: false, // Remove default frame for custom title bar
    titleBarStyle: 'hidden',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
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
    const distIndexPath = path.join(appPath, 'dist', 'index.html')
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

function startWorkflowServer() {
  const appBasePath = getAppBasePath()
  const serverPath = path.join(appBasePath, 'workflow-server', 'main.py')
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
  workflowServerProcess = spawn(pythonCmd, [serverPath], {
    stdio: 'inherit',
    env: {
      ...process.env,
      PYTHONUNBUFFERED: '1',
    },
  })
}

function startApiServer() {
  const appBasePath = getAppBasePath()
  const serverPath = path.join(appBasePath, 'api-server', 'run.py')
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
  apiServerProcess = spawn(pythonCmd, [serverPath], {
    stdio: 'inherit',
    env: {
      ...process.env,
      PYTHONUNBUFFERED: '1',
      // Ensure production-like behavior when packaged.
      UVICORN_RELOAD: '0',
      LOG_LEVEL: process.env.LOG_LEVEL || 'INFO',
    },
  })
}

function stopPython() {
  if (workflowServerProcess) {
    workflowServerProcess.kill()
    workflowServerProcess = null
  }
  if (apiServerProcess) {
    apiServerProcess.kill()
    apiServerProcess = null
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
  // Only start Python servers in production (in dev, they're started by npm scripts)
  if (!getIsDev()) {
    startWorkflowServer()
    startApiServer()
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
    const parsed = new URL(String(url))
    const protocol = parsed.protocol.toLowerCase()
    if (protocol === 'https:') {
      await shell.openExternal(parsed.toString())
      return { success: true }
    }
    if (protocol === 'http:' && (parsed.hostname === '127.0.0.1' || parsed.hostname === 'localhost')) {
      await shell.openExternal(parsed.toString())
      return { success: true }
    }
    throw new Error(`Blocked external URL: ${parsed.toString()}`)
  } catch (error) {
    console.error('Error opening external URL:', error)
    return { success: false, error: error.message }
  }
})

// Create Stripe checkout window
ipcMain.handle('stripe:openCheckout', async (event, url) => {
  try {
    const parsed = new URL(String(url))
    const hostname = parsed.hostname.toLowerCase()
    const isStripe =
      parsed.protocol.toLowerCase() === 'https:' &&
      (hostname === 'checkout.stripe.com' || hostname.endsWith('.stripe.com'))
    if (!isStripe) {
      throw new Error(`Blocked non-Stripe checkout URL: ${parsed.toString()}`)
    }

    const checkoutWindow = new BrowserWindow({
      width: 800,
      height: 900,
      parent: mainWindow,
      modal: false,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        sandbox: true
      },
      title: 'Complete Your Subscription'
    })

    // Load the Stripe checkout URL
    await checkoutWindow.loadURL(parsed.toString())

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


