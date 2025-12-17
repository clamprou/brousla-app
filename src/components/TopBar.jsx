import React from 'react'
import { Settings, HelpCircle, Minus, X, User } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext.jsx'

export default function TopBar() {
  const { isAuthenticated } = useAuth()

  const handleSettingsClick = () => {
    // Dispatch custom event to navigate to settings
    window.dispatchEvent(new CustomEvent('navigate', { detail: 'settings' }))
  }

  const handleProfileClick = () => {
    // Dispatch custom event to navigate to profile
    window.dispatchEvent(new CustomEvent('navigate', { detail: 'profile' }))
  }

  const handleHelpClick = () => {
    // You can implement help functionality here
    console.log('Help clicked')
  }

  const handleMinimizeClick = () => {
    if (window.electronAPI && window.electronAPI.minimizeWindow) {
      window.electronAPI.minimizeWindow()
    }
  }

  const handleCloseClick = () => {
    if (window.electronAPI && window.electronAPI.closeWindow) {
      window.electronAPI.closeWindow()
    }
  }

  return (
    <div 
      className="flex items-center justify-between h-12 bg-gray-900 border-b border-gray-700 px-4 shadow-lg"
      style={{ 
        WebkitAppRegion: 'drag',
        appRegion: 'drag'
      }}
    >
      {/* Left side - Logo/App Name */}
      <div className="flex items-center">
        <h1 className="text-lg font-semibold text-white">AI Studio</h1>
      </div>

      {/* Right side - Controls */}
      <div className="flex items-center space-x-2">
        {/* Profile Button - Only show when authenticated */}
        {isAuthenticated && (
          <button
            onClick={handleProfileClick}
            className="p-2 rounded-md hover:bg-gray-700 text-gray-300 hover:text-white transition-colors duration-200"
            style={{ WebkitAppRegion: 'no-drag', appRegion: 'no-drag' }}
            title="Profile"
          >
            <User size={16} />
          </button>
        )}

        {/* Settings Button */}
        <button
          onClick={handleSettingsClick}
          className="p-2 rounded-md hover:bg-gray-700 text-gray-300 hover:text-white transition-colors duration-200"
          style={{ WebkitAppRegion: 'no-drag', appRegion: 'no-drag' }}
          title="Settings"
        >
          <Settings size={16} />
        </button>

        {/* Help Button */}
        <button
          onClick={handleHelpClick}
          className="p-2 rounded-md hover:bg-gray-700 text-gray-300 hover:text-white transition-colors duration-200"
          style={{ WebkitAppRegion: 'no-drag', appRegion: 'no-drag' }}
          title="Help"
        >
          <HelpCircle size={16} />
        </button>

        {/* Separator */}
        <div className="w-px h-6 bg-gray-600 mx-2" />

        {/* Window Controls */}
        <button
          onClick={handleMinimizeClick}
          className="p-2 rounded-md hover:bg-gray-700 text-gray-300 hover:text-white transition-colors duration-200"
          style={{ WebkitAppRegion: 'no-drag', appRegion: 'no-drag' }}
          title="Minimize"
        >
          <Minus size={16} />
        </button>

        <button
          onClick={handleCloseClick}
          className="p-2 rounded-md hover:bg-red-600 text-gray-300 hover:text-white transition-colors duration-200"
          style={{ WebkitAppRegion: 'no-drag', appRegion: 'no-drag' }}
          title="Close"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  )
}
