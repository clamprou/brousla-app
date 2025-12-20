import React, { useState, useEffect } from 'react'
import { X, CreditCard } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext.jsx'

export default function StripeCheckoutModal({ isOpen, onClose, checkoutUrl, onSuccess, onCancel }) {
  const [isOpening, setIsOpening] = useState(false)
  const { fetchSubscriptionStatus, token } = useAuth()

  // Check for Stripe callback when modal opens (user returned from Stripe)
  useEffect(() => {
    if (!isOpen) return

    const urlParams = new URLSearchParams(window.location.search)
    const sessionId = urlParams.get('session_id')
    const cancelled = urlParams.get('cancelled')

    if (sessionId) {
      // Success - refresh subscription status and close modal
      if (fetchSubscriptionStatus) {
        fetchSubscriptionStatus()
      }
      if (onSuccess) {
        onSuccess()
      }
      onClose()
      // Clean URL
      window.history.replaceState({}, '', window.location.pathname)
    } else if (cancelled) {
      // Cancelled - just close modal
      if (onCancel) {
        onCancel()
      }
      onClose()
      // Clean URL
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [isOpen, fetchSubscriptionStatus, onSuccess, onCancel, onClose])

  // Note: Event listeners are now handled in Profile.jsx to persist even when modal closes

  const handleContinueToPayment = async () => {
    if (!checkoutUrl) return
    
    setIsOpening(true)

    // Open in new Electron window (keeps toolbar on main window)
    if (window.electronAPI && window.electronAPI.openStripeCheckout) {
      try {
        const result = await window.electronAPI.openStripeCheckout(checkoutUrl)
        if (result.success) {
          // Window opened successfully - close this modal
          setIsOpening(false)
          onClose()
        } else {
          // Error opening window
          setIsOpening(false)
          alert(result.error || 'Failed to open checkout window')
        }
      } catch (err) {
        setIsOpening(false)
        alert(err.message || 'Failed to open checkout window')
      }
    } else {
      // Fallback if Electron API not available
      setIsOpening(false)
      alert('Electron API not available. Please restart the application.')
    }
  }

  if (!isOpen) return null

  return (
    <div 
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={(e) => {
        // Prevent closing on backdrop click - user must proceed or cancel
        if (e.target === e.currentTarget) {
          // Optionally allow closing, or remove this to force action
          // onClose()
        }
      }}
    >
      <div 
        className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-lg mx-4 relative shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600/20 rounded-lg">
              <CreditCard className="h-5 w-5 text-blue-400" />
            </div>
            <h2 className="text-xl font-semibold text-gray-200">Complete Your Subscription</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-300 hover:bg-gray-800 rounded-lg transition-colors"
            title="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          <p className="text-base text-gray-300 mb-6 text-center">
            You'll be redirected to Stripe to complete your payment securely.
          </p>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-3 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleContinueToPayment}
              disabled={isOpening || !checkoutUrl}
              className="flex-1 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isOpening ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Opening...
                </>
              ) : (
                'Continue to Payment'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
