import React, { useMemo, useState } from 'react'
import Sidebar from './components/Sidebar.jsx'
import TextToImage from './pages/TextToImage.jsx'
import ImageToVideo from './pages/ImageToVideo.jsx'
import TextToVideo from './pages/TextToVideo.jsx'
import Settings from './pages/Settings.jsx'
import { ImageIcon, Film, Type, Settings as SettingsIcon } from 'lucide-react'

export default function App() {
  const [collapsed, setCollapsed] = useState(false)
  const [activeKey, setActiveKey] = useState('text-to-image')

  const items = useMemo(() => ([
    { key: 'text-to-image', label: 'Text to Image', icon: ImageIcon },
    { key: 'image-to-video', label: 'Image to Video', icon: Film },
    { key: 'text-to-video', label: 'Text to Video', icon: Type },
    { key: 'settings', label: 'Settings', icon: SettingsIcon }
  ]), [])

  const page = useMemo(() => {
    switch (activeKey) {
      case 'text-to-image':
        return <TextToImage />
      case 'image-to-video':
        return <ImageToVideo />
      case 'text-to-video':
        return <TextToVideo />
      case 'settings':
        return <Settings />
      default:
        return null
    }
  }, [activeKey])

  return (
    <div className="app-shell flex bg-gray-950">
      <Sidebar
        items={items}
        activeKey={activeKey}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed(v => !v)}
        onSelect={setActiveKey}
      />
      <div className="flex-1 overflow-auto">
        {page}
      </div>
    </div>
  )
}


