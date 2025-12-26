import React, { useMemo, useState, useEffect } from 'react'
import TopBar from './components/TopBar.jsx'
import Sidebar from './components/Sidebar.jsx'
import TextToImage from './pages/TextToImage.jsx'
import ImageToVideo from './pages/ImageToVideo.jsx'
import TextToVideo from './pages/TextToVideo.jsx'
import Settings from './pages/Settings.jsx'
import Profile from './pages/Profile.jsx'
import EmailConfirmation from './pages/EmailConfirmation.jsx'
import GoogleOAuthCallback from './pages/GoogleOAuthCallback.jsx'
import { ImageIcon, Film, Type, Settings as SettingsIcon, Bot } from 'lucide-react'
import AIWorkflows from './pages/AIWorkflows.jsx'
import CreateWorkflow from './pages/CreateWorkflow.jsx'
import WorkflowTypeSelection from './pages/WorkflowTypeSelection.jsx'
import ComfyUIConnectionModal from './components/ComfyUIConnectionModal.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import { AuthProvider } from './contexts/AuthContext.jsx'
import StripeCheckoutListener from './components/StripeCheckoutListener.jsx'
import { WORKFLOW_BASE_URL } from './config/workflowServer.js'

export default function App() {
  const [collapsed, setCollapsed] = useState(false)
  const [activeKey, setActiveKey] = useState('text-to-image')
  const previousKeyRef = React.useRef('text-to-image')
  const [isComfyUIConnected, setIsComfyUIConnected] = useState(false)
  const [showConnectionModal, setShowConnectionModal] = useState(false)
  const [isCheckingConnection, setIsCheckingConnection] = useState(true)
  const previousActiveKeyRef = React.useRef('text-to-image')
  
  // Check if we're on email confirmation page
  // Support both pathname routing (dev) and hash routing (production)
  const isEmailConfirmation = useMemo(() => {
    const params = new URLSearchParams(window.location.search)
    const hashParams = window.location.hash ? new URLSearchParams(window.location.hash.split('?')[1] || '') : null
    const hasToken = params.has('token') || (hashParams && hashParams.has('token'))
    
    return window.location.pathname === '/email-confirmation' || 
           window.location.hash.startsWith('#/email-confirmation') ||
           hasToken
  }, [])

  // Check if we're on Google OAuth callback page
  // Support both pathname routing (dev) and hash routing (production)
  const [isGoogleOAuthCallback, setIsGoogleOAuthCallback] = useState(() => {
    return window.location.pathname === '/google-oauth-callback' || 
           window.location.hash.startsWith('#/google-oauth-callback') ||
           window.location.href.includes('google-oauth-callback')
  })

  // Update OAuth callback detection when URL changes
  useEffect(() => {
    const checkCallback = () => {
      const isCallback = window.location.pathname === '/google-oauth-callback' || 
                        window.location.hash.startsWith('#/google-oauth-callback') ||
                        window.location.href.includes('google-oauth-callback')
      setIsGoogleOAuthCallback(isCallback)
    }
    
    checkCallback()
    // Also listen for popstate events (back/forward navigation) and hash changes
    window.addEventListener('popstate', checkCallback)
    window.addEventListener('hashchange', checkCallback)
    // Check periodically in case URL changes without events
    const interval = setInterval(checkCallback, 100)
    
    return () => {
      window.removeEventListener('popstate', checkCallback)
      window.removeEventListener('hashchange', checkCallback)
      clearInterval(interval)
    }
  }, [])

  // Global navigation event to allow pages to trigger navigation without props drilling
  React.useEffect(() => {
    const handler = (e) => {
      const key = e?.detail
      if (typeof key === 'string') {
        // Store previous key before navigating (unless navigating back)
        if (key !== activeKey) {
          previousKeyRef.current = activeKey
        }
        setActiveKey(key)
      }
    }
    window.addEventListener('navigate', handler)
    return () => window.removeEventListener('navigate', handler)
  }, [activeKey])

  // Expose function to get previous page
  React.useEffect(() => {
    window.getPreviousPage = () => previousKeyRef.current
  }, [])

  // Check ComfyUI connection on app mount
  useEffect(() => {
    const checkComfyUIConnection = async () => {
      try {
        const response = await fetch(`${WORKFLOW_BASE_URL}/comfyui/test-connection`)
        const data = await response.json()

        if (data.success) {
          setIsComfyUIConnected(true)
          setShowConnectionModal(false)
        } else {
          setIsComfyUIConnected(false)
          setShowConnectionModal(true)
        }
      } catch (error) {
        console.error('Error checking ComfyUI connection:', error)
        setIsComfyUIConnected(false)
        setShowConnectionModal(true)
      } finally {
        setIsCheckingConnection(false)
      }
    }

    checkComfyUIConnection()
  }, [])

  // Handle successful connection
  const handleConnectionSuccess = () => {
    setIsComfyUIConnected(true)
    setShowConnectionModal(false)
  }

  // Handle opening settings from modal
  const handleOpenSettings = () => {
    setActiveKey('settings')
  }

  // Track previous activeKey and re-check connection when leaving Settings
  useEffect(() => {
    const previousKey = previousActiveKeyRef.current
    previousActiveKeyRef.current = activeKey
    
    // If we just left Settings and connection isn't established, re-check
    if (previousKey === 'settings' && activeKey !== 'settings' && !isComfyUIConnected) {
      const checkConnection = async () => {
        try {
          const response = await fetch(`${WORKFLOW_BASE_URL}/comfyui/test-connection`)
          const data = await response.json()
          if (!data.success) {
            setShowConnectionModal(true)
          } else {
            setIsComfyUIConnected(true)
            setShowConnectionModal(false)
          }
        } catch (error) {
          setShowConnectionModal(true)
        }
      }
      checkConnection()
    }
  }, [activeKey, isComfyUIConnected])

  const items = useMemo(() => ([
    // AI Workflows
    { key: 'ai-composer', label: 'AI Workflows', icon: Bot, group: 'ai' },
    // Manual Generation (ordered: Text to Image, Image to Video, Text to Video)
    { key: 'text-to-image', label: 'Text to Image', icon: ImageIcon, group: 'manual' },
    { key: 'image-to-video', label: 'Image to Video', icon: Film, group: 'manual' },
    { key: 'text-to-video', label: 'Text to Video', icon: Type, group: 'manual' },
    // Settings
    { key: 'settings', label: 'Settings', icon: SettingsIcon, group: 'settings' }
  ]), [])

  const page = useMemo(() => {
    switch (activeKey) {
      case 'text-to-image':
        return <TextToImage />
      case 'image-to-video':
        return <ImageToVideo />
      case 'text-to-video':
        return <TextToVideo />
      case 'ai-composer':
        return <AIWorkflows />
      case 'workflow-type-selection':
        return <WorkflowTypeSelection />
      case 'create-workflow':
        return <CreateWorkflow />
      case 'settings':
        return <Settings />
      case 'profile':
        return <Profile />
      default:
        return null
    }
  }, [activeKey])

  // Show modal only when connection is not established and not on Settings page
  const shouldShowModal = showConnectionModal && activeKey !== 'settings'

  // If email confirmation token is in URL, show EmailConfirmation page (outside ProtectedRoute)
  if (isEmailConfirmation) {
    return (
      <AuthProvider>
        <EmailConfirmation />
      </AuthProvider>
    )
  }

  // If Google OAuth callback, show GoogleOAuthCallback page (outside ProtectedRoute)
  if (isGoogleOAuthCallback) {
    return (
      <AuthProvider>
        <GoogleOAuthCallback />
      </AuthProvider>
    )
  }

  return (
    <AuthProvider>
      <ProtectedRoute>
        {/* Persistent Stripe checkout event listener */}
        <StripeCheckoutListener />
        <div className="app-shell flex flex-col bg-gray-950">
          {/* ComfyUI Connection Modal - Highest Priority */}
          <ComfyUIConnectionModal
            isOpen={shouldShowModal}
            onConnectionSuccess={handleConnectionSuccess}
            onOpenSettings={handleOpenSettings}
          />

          {/* Block app interaction when modal is shown */}
          <div className={`flex flex-col h-screen ${shouldShowModal ? 'pointer-events-none opacity-50' : ''}`}>
            <TopBar />
            <div className="flex flex-1 overflow-hidden min-h-0">
              <Sidebar
                items={items}
                activeKey={activeKey}
                collapsed={collapsed}
                onToggleCollapse={() => setCollapsed(v => !v)}
                onSelect={(key) => {
                  // Block navigation when modal should be shown, except to Settings
                  if (shouldShowModal && key !== 'settings') {
                    return
                  }
                  if (key !== activeKey) {
                    previousKeyRef.current = activeKey
                  }
                  setActiveKey(key)
                }}
              />
              <div className="flex-1 overflow-auto min-h-0">
                {page}
              </div>
            </div>
          </div>
        </div>
      </ProtectedRoute>
    </AuthProvider>
  )
}


