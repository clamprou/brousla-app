import React from 'react'
import { Minus, X, User, Zap, Crown } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext.jsx'

export default function TopBar() {
  const { subscriptionStatus, isAuthenticated } = useAuth()

  const handleProfileClick = () => {
    // Dispatch custom event to navigate to profile
    window.dispatchEvent(new CustomEvent('navigate', { detail: 'profile' }))
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

  // Get plan info for the profile button
  const getPlanInfo = () => {
    if (!isAuthenticated || !subscriptionStatus) {
      return { plan: null, icon: User, color: 'gray', bgColor: 'bg-gray-700', textColor: 'text-gray-300' }
    }

    const plan = subscriptionStatus.subscription_plan
    if (!plan || plan === 'trial') {
      return { plan: null, icon: User, color: 'gray', bgColor: 'bg-gray-700', textColor: 'text-gray-300' }
    }

    switch (plan) {
      case 'basic':
        return { 
          plan: 'Basic', 
          icon: Zap, 
          color: 'blue', 
          bgColor: 'bg-blue-600', 
          textColor: 'text-blue-100',
          iconColor: 'text-blue-200'
        }
      case 'plus':
        return { 
          plan: 'Plus', 
          icon: Crown, 
          color: 'purple', 
          bgColor: 'bg-purple-600', 
          textColor: 'text-purple-100',
          iconColor: 'text-purple-200'
        }
      case 'pro':
        return { 
          plan: 'Pro', 
          icon: Crown, 
          color: 'yellow', 
          bgColor: 'bg-yellow-600', 
          textColor: 'text-yellow-100',
          iconColor: 'text-yellow-200'
        }
      default:
        return { plan: null, icon: User, color: 'gray', bgColor: 'bg-gray-700', textColor: 'text-gray-300' }
    }
  }

  const planInfo = getPlanInfo()
  const PlanIcon = planInfo.icon

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
        {/* Profile/Plan Button - Only show when authenticated */}
        {isAuthenticated && (
          <button
            onClick={handleProfileClick}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md hover:opacity-90 transition-opacity ${planInfo.bgColor} ${planInfo.textColor}`}
            style={{ WebkitAppRegion: 'no-drag', appRegion: 'no-drag' }}
            title={planInfo.plan ? `${planInfo.plan} Plan` : 'Profile'}
          >
            <PlanIcon size={14} className={planInfo.iconColor || planInfo.textColor} />
            {planInfo.plan && (
              <span className="text-xs font-medium">{planInfo.plan}</span>
            )}
          </button>
        )}

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
