import React, { useMemo, useState } from 'react'
import TopBar from './components/TopBar.jsx'
import Sidebar from './components/Sidebar.jsx'
import TextToImage from './pages/TextToImage.jsx'
import ImageToVideo from './pages/ImageToVideo.jsx'
import TextToVideo from './pages/TextToVideo.jsx'
import Settings from './pages/Settings.jsx'
import { ImageIcon, Film, Type, Settings as SettingsIcon, Bot } from 'lucide-react'
import AIWorkflows from './pages/AIWorkflows.jsx'
import CreateWorkflow from './pages/CreateWorkflow.jsx'
import WorkflowTypeSelection from './pages/WorkflowTypeSelection.jsx'

export default function App() {
  const [collapsed, setCollapsed] = useState(false)
  const [activeKey, setActiveKey] = useState('text-to-image')
  const previousKeyRef = React.useRef('text-to-image')

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
      default:
        return null
    }
  }, [activeKey])

  return (
    <div className="app-shell flex flex-col bg-gray-950">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          items={items}
          activeKey={activeKey}
          collapsed={collapsed}
          onToggleCollapse={() => setCollapsed(v => !v)}
          onSelect={(key) => {
            if (key !== activeKey) {
              previousKeyRef.current = activeKey
            }
            setActiveKey(key)
          }}
        />
        <div className="flex-1 overflow-auto">
          {page}
        </div>
      </div>
    </div>
  )
}


