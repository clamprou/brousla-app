import React, { useState, useEffect, useRef } from 'react'
import { useAuth } from '../contexts/AuthContext.jsx'
import { LogOut, User, Mail, Shield, CreditCard, Zap, Crown, Check, ExternalLink } from 'lucide-react'
import { BASE_API_URL } from '../config/api.js'
import { createCheckoutSession, cancelSubscription } from '../utils/apiClient.js'
import StripeCheckoutModal from '../components/StripeCheckoutModal.jsx'

export default function Profile() {
  const { token, logout, subscriptionStatus, fetchSubscriptionStatus } = useAuth()
  const [userInfo, setUserInfo] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isCreatingCheckout, setIsCreatingCheckout] = useState(false)
  const [isCancelling, setIsCancelling] = useState(false)
  const [showCheckoutModal, setShowCheckoutModal] = useState(false)
  const [checkoutUrl, setCheckoutUrl] = useState(null)
  const fetchingRef = useRef(false)

  // Refresh subscription status when Profile page is viewed
  useEffect(() => {
    if (token) {
      fetchSubscriptionStatus()
    }
    // Only run when token changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  // Note: Stripe checkout event listeners are now handled by StripeCheckoutListener component

  useEffect(() => {
    if (!token) {
      setIsLoading(false)
      return
    }

    // Prevent multiple simultaneous fetches
    if (fetchingRef.current) {
      return
    }

    fetchingRef.current = true
    let isMounted = true
    
    const fetchUserInfo = async () => {
      try {
        const response = await fetch(`${BASE_API_URL}/auth/me`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        })

        if (!isMounted) {
          fetchingRef.current = false
          return
        }

        if (response.ok) {
          const data = await response.json()
          setUserInfo(data)
        } else {
          const errorText = await response.text()
          let errorData = null
          try {
            errorData = JSON.parse(errorText)
          } catch (e) {
            errorData = { detail: errorText }
          }
          
          if (response.status === 401) {
            setError('Authentication failed. Please log in again.')
            logout()
          } else {
            setError(errorData.detail || 'Failed to load user information')
          }
        }
      } catch (err) {
        if (!isMounted) {
          fetchingRef.current = false
          return
        }
        console.error('Error fetching user info:', err)
        setError('Error loading user information: ' + err.message)
      } finally {
        if (isMounted) {
          setIsLoading(false)
          fetchingRef.current = false
        }
      }
    }

    fetchUserInfo()
    
    return () => {
      isMounted = false
      fetchingRef.current = false
    }
    // Only run when token changes, not when subscriptionStatus or other values change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])
  
  // Check for Stripe callback - only run once on mount
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    const sessionId = urlParams.get('session_id')
    const cancelled = urlParams.get('cancelled')
    
    if (sessionId) {
      // Success - refresh subscription status
      setTimeout(() => {
        if (token) {
          fetchSubscriptionStatus()
        }
        // Remove query params from URL
        window.history.replaceState({}, '', window.location.pathname)
      }, 1000)
    } else if (cancelled) {
      // Cancelled - just remove query params
      window.history.replaceState({}, '', window.location.pathname)
    }
    // Only run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Plan hierarchy: trial < basic < plus < pro
  const planOrder = { trial: 0, basic: 1, plus: 2, pro: 3 }
  
  const getPlanLevel = (plan) => {
    if (!plan || plan === 'trial') return 0
    return planOrder[plan] || 0
  }
  
  const isPlanBigger = (plan1, plan2) => {
    return getPlanLevel(plan1) > getPlanLevel(plan2)
  }

  const handleUpgrade = async (plan) => {
    if (!token) return
    
    setIsCreatingCheckout(true)
    try {
      const result = await createCheckoutSession(token, plan)
      // Open Stripe checkout in modal instead of external browser
      setCheckoutUrl(result.checkout_url)
      setShowCheckoutModal(true)
      setIsCreatingCheckout(false)
    } catch (err) {
      setError(err.message || 'Failed to create checkout session')
      setIsCreatingCheckout(false)
    }
  }

  const handleCancel = async () => {
    if (!token) return
    
    if (!window.confirm('Are you sure you want to cancel your subscription? It will remain active until the end of the current billing period.')) {
      return
    }
    
    setIsCancelling(true)
    try {
      const result = await cancelSubscription(token)
      setError(null)
      alert(result.message || 'Subscription cancelled successfully')
      // Refresh subscription status
      if (fetchSubscriptionStatus) {
        fetchSubscriptionStatus()
      }
    } catch (err) {
      setError(err.message || 'Failed to cancel subscription')
    } finally {
      setIsCancelling(false)
    }
  }

  const handleCheckoutSuccess = () => {
    // Refresh subscription status
    if (token) {
      fetchSubscriptionStatus()
    }
    setShowCheckoutModal(false)
    setCheckoutUrl(null)
  }

  const handleCheckoutCancel = () => {
    setShowCheckoutModal(false)
    setCheckoutUrl(null)
  }

  const getUsageText = () => {
    if (!subscriptionStatus?.usage) return 'N/A'
    const usage = subscriptionStatus.usage
    if (usage.type === 'trial') {
      return `${usage.used} / ${usage.limit} free executions`
    } else if (usage.type === 'monthly') {
      return `${usage.used} / ${usage.limit} executions this month`
    } else {
      return `${usage.used} executions this month`
    }
  }

  const handleLogout = () => {
    logout()
    // Navigation will be handled by ProtectedRoute showing login form
  }

  return (
    <div className="h-full p-6 bg-gray-950">
      {/* Stripe Checkout Modal */}
      <StripeCheckoutModal
        isOpen={showCheckoutModal}
        onClose={handleCheckoutCancel}
        checkoutUrl={checkoutUrl}
        onSuccess={handleCheckoutSuccess}
        onCancel={handleCheckoutCancel}
      />

      <div className="max-w-2xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-gray-200 mb-2">Profile</h1>
          <p className="text-sm text-gray-400">Manage your account settings</p>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-gray-400">Loading...</div>
          </div>
        ) : error ? (
          <div className="p-4 bg-red-900/20 border border-red-600/30 rounded-lg">
            <p className="text-sm text-red-300">{error}</p>
          </div>
        ) : userInfo ? (
          <div className="space-y-6">
            {/* User Info Card */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-16 h-16 rounded-full bg-blue-600 flex items-center justify-center">
                  <User className="h-8 w-8 text-white" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-200">Account Information</h2>
                  <p className="text-sm text-gray-400">Your account details</p>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg">
                  <Mail className="h-5 w-5 text-gray-400 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-xs text-gray-500 mb-1">Email</p>
                    <p className="text-sm text-gray-200">{userInfo.email}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg">
                  <Shield className="h-5 w-5 text-gray-400 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-xs text-gray-500 mb-1">User ID</p>
                    <p className="text-sm text-gray-200 font-mono">{userInfo.id}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Subscription Section */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <div className="flex items-center gap-3 mb-4">
                <CreditCard className="h-5 w-5 text-gray-400" />
                <h3 className="text-lg font-semibold text-gray-200">Subscription</h3>
              </div>
              
                  {subscriptionStatus ? (
                <div className="space-y-4">
                  {/* Current Plan */}
                  <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-gray-400">Current Plan</span>
                      <span className="text-sm font-medium text-gray-200">
                        {subscriptionStatus.subscription_plan 
                          ? subscriptionStatus.subscription_plan.charAt(0).toUpperCase() + subscriptionStatus.subscription_plan.slice(1)
                          : 'Free Trial'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-400">Usage</span>
                      <span className="text-sm font-medium text-gray-200">{getUsageText()}</span>
                    </div>
                    {subscriptionStatus.subscription_end_date && (
                      <div className="flex items-center justify-between mt-2">
                        <span className="text-sm font-medium text-gray-300">Renewal Date</span>
                        <span className="text-sm font-medium text-gray-200">
                          {new Date(subscriptionStatus.subscription_end_date).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric'
                          })}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* All Plans */}
                  <div className="mt-6">
                    <h4 className="text-sm font-semibold text-gray-300 mb-4">Available Plans</h4>
                    <div className="grid md:grid-cols-3 gap-4">
                      {/* Basic Plan */}
                      {(() => {
                        const currentPlan = subscriptionStatus.subscription_plan || 'trial'
                        const isCurrentPlan = currentPlan === 'basic'
                        const isBigger = isPlanBigger('basic', currentPlan)
                        
                        return (
                          <div className={`bg-gray-800 border rounded-lg p-4 ${isCurrentPlan ? 'border-blue-500 ring-2 ring-blue-500/20' : 'border-gray-700'}`}>
                            <div className="flex items-center gap-2 mb-2">
                              <Zap className="h-4 w-4 text-blue-400" />
                              <h4 className="font-semibold text-gray-200">Basic</h4>
                              {isCurrentPlan && (
                                <span className="px-2 py-0.5 bg-blue-600/20 text-blue-400 rounded-full text-xs">
                                  Current
                                </span>
                              )}
                            </div>
                            <div className="mb-2">
                              <span className="text-xl font-bold text-gray-100">€5.99</span>
                              <span className="text-xs text-gray-400">/month</span>
                            </div>
                            <p className="text-sm text-gray-400 mb-3">500 executions/month</p>
                            {isCurrentPlan ? (
                              <button
                                onClick={handleCancel}
                                disabled={isCancelling}
                                className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                {isCancelling ? 'Cancelling...' : 'Cancel Plan'}
                              </button>
                            ) : isBigger ? (
                              <button
                                onClick={() => handleUpgrade('basic')}
                                disabled={isCreatingCheckout}
                                className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                {isCreatingCheckout ? 'Processing...' : 'Upgrade to Basic'}
                              </button>
                            ) : (
                              <button
                                disabled
                                className="w-full px-4 py-2 bg-gray-700 text-gray-500 rounded-lg font-medium cursor-not-allowed"
                                title="Cannot downgrade to a smaller plan"
                              >
                                Current Plan Higher
                              </button>
                            )}
                          </div>
                        )
                      })()}

                      {/* Plus Plan */}
                      {(() => {
                        const currentPlan = subscriptionStatus.subscription_plan || 'trial'
                        const isCurrentPlan = currentPlan === 'plus'
                        const isBigger = isPlanBigger('plus', currentPlan)
                        
                        return (
                          <div className={`bg-gray-800 border rounded-lg p-4 ${isCurrentPlan ? 'border-purple-500 ring-2 ring-purple-500/20' : 'border-gray-700'}`}>
                            <div className="flex items-center gap-2 mb-2">
                              <Crown className="h-4 w-4 text-purple-400" />
                              <h4 className="font-semibold text-gray-200">Plus</h4>
                              {isCurrentPlan && (
                                <span className="px-2 py-0.5 bg-purple-600/20 text-purple-400 rounded-full text-xs">
                                  Current
                                </span>
                              )}
                              {!isCurrentPlan && (
                                <span className="px-2 py-0.5 bg-purple-600/20 text-purple-400 rounded-full text-xs">
                                  Popular
                                </span>
                              )}
                            </div>
                            <div className="mb-2">
                              <span className="text-xl font-bold text-gray-100">€14.99</span>
                              <span className="text-xs text-gray-400">/month</span>
                            </div>
                            <p className="text-sm text-gray-400 mb-3">2000 executions/month</p>
                            {isCurrentPlan ? (
                              <button
                                onClick={handleCancel}
                                disabled={isCancelling}
                                className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                {isCancelling ? 'Cancelling...' : 'Cancel Plan'}
                              </button>
                            ) : isBigger ? (
                              <button
                                onClick={() => handleUpgrade('plus')}
                                disabled={isCreatingCheckout}
                                className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                {isCreatingCheckout ? 'Processing...' : 'Upgrade to Plus'}
                              </button>
                            ) : (
                              <button
                                disabled
                                className="w-full px-4 py-2 bg-gray-700 text-gray-500 rounded-lg font-medium cursor-not-allowed"
                                title="Cannot downgrade to a smaller plan"
                              >
                                Current Plan Higher
                              </button>
                            )}
                          </div>
                        )
                      })()}

                      {/* Pro Plan */}
                      {(() => {
                        const currentPlan = subscriptionStatus.subscription_plan || 'trial'
                        const isCurrentPlan = currentPlan === 'pro'
                        const isBigger = isPlanBigger('pro', currentPlan)
                        
                        return (
                          <div className={`bg-gray-800 border rounded-lg p-4 ${isCurrentPlan ? 'border-yellow-500 ring-2 ring-yellow-500/20' : 'border-gray-700'}`}>
                            <div className="flex items-center gap-2 mb-2">
                              <Crown className="h-4 w-4 text-yellow-400" />
                              <h4 className="font-semibold text-gray-200">Pro</h4>
                              {isCurrentPlan && (
                                <span className="px-2 py-0.5 bg-yellow-600/20 text-yellow-400 rounded-full text-xs">
                                  Current
                                </span>
                              )}
                            </div>
                            <div className="mb-2">
                              <span className="text-xl font-bold text-gray-100">€29.99</span>
                              <span className="text-xs text-gray-400">/month</span>
                            </div>
                            <p className="text-sm text-gray-400 mb-3">5000 executions/month</p>
                            {isCurrentPlan ? (
                              <button
                                onClick={handleCancel}
                                disabled={isCancelling}
                                className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                {isCancelling ? 'Cancelling...' : 'Cancel Plan'}
                              </button>
                            ) : isBigger ? (
                              <button
                                onClick={() => handleUpgrade('pro')}
                                disabled={isCreatingCheckout}
                                className="w-full px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                {isCreatingCheckout ? 'Processing...' : 'Upgrade to Pro'}
                              </button>
                            ) : (
                              <button
                                disabled
                                className="w-full px-4 py-2 bg-gray-700 text-gray-500 rounded-lg font-medium cursor-not-allowed"
                                title="Cannot downgrade to a smaller plan"
                              >
                                Current Plan Higher
                              </button>
                            )}
                          </div>
                        )
                      })()}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-gray-400">Loading subscription information...</div>
              )}
            </div>

            {/* Logout Section */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-gray-200 mb-2">Account Actions</h3>
              <p className="text-sm text-gray-400 mb-4">
                Sign out of your account. You'll need to log in again to access the application.
              </p>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-4 py-2 bg-red-700 hover:bg-red-600 text-gray-200 rounded-lg transition-colors font-medium"
              >
                <LogOut className="h-5 w-5" />
                Log Out
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}

