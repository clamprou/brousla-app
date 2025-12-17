import React from 'react'
import { AlertTriangle, X } from 'lucide-react'

export default function ConfirmationModal({ 
  isOpen, 
  onClose, 
  onConfirm, 
  title, 
  message, 
  confirmText = 'Confirm', 
  cancelText = 'Cancel',
  type = 'danger' 
}) {
  if (!isOpen) return null

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      onClose()
    }
  }

  React.useEffect(() => {
    if (isOpen) {
      // Store the currently focused element
      const activeElement = document.activeElement
      
      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
      
      return () => {
        document.removeEventListener('keydown', handleKeyDown)
        document.body.style.overflow = 'unset'
        
        // Restore focus to the previously focused element
        if (activeElement && typeof activeElement.focus === 'function') {
          setTimeout(() => {
            try {
              activeElement.focus()
            } catch (e) {
              // Ignore focus errors
            }
          }, 0)
        }
      }
    }
  }, [isOpen])

  const getButtonStyles = () => {
    switch (type) {
      case 'danger':
        return {
          confirm: 'bg-red-600 hover:bg-red-700 text-white',
          icon: 'text-red-400'
        }
      case 'warning':
        return {
          confirm: 'bg-yellow-600 hover:bg-yellow-700 text-white',
          icon: 'text-yellow-400'
        }
      default:
        return {
          confirm: 'bg-blue-600 hover:bg-blue-700 text-white',
          icon: 'text-blue-400'
        }
    }
  }

  const buttonStyles = getButtonStyles()

  return (
    <div 
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg bg-${type === 'danger' ? 'red' : type === 'warning' ? 'yellow' : 'blue'}-600/20`}>
              <AlertTriangle className={`h-5 w-5 ${buttonStyles.icon}`} />
            </div>
            <h3 className="text-lg font-semibold text-gray-200">{title}</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          <p className="text-gray-300 mb-6">{message}</p>
          
          {/* Actions */}
          <div className="flex items-center justify-end gap-3">
            {cancelText && (
              <button
                onClick={onClose}
                className="px-4 py-2 text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded-lg font-medium transition-colors"
              >
                {cancelText}
              </button>
            )}
            <button
              onClick={() => {
                onConfirm()
                onClose()
              }}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${buttonStyles.confirm}`}
            >
              {confirmText}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
