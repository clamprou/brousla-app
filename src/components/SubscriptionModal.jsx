import React from 'react'
import { X, AlertCircle, CreditCard, Zap, Crown } from 'lucide-react'

export default function SubscriptionModal({ isOpen, onClose, subscriptionStatus }) {
  if (!isOpen) return null

  const usage = subscriptionStatus?.usage || {}
  const plan = subscriptionStatus?.subscription_plan

  const getUsageText = () => {
    if (usage.type === 'trial') {
      return `${usage.used} / ${usage.limit} free executions used`
    } else if (usage.type === 'monthly') {
      return `${usage.used} / ${usage.limit} executions used this month`
    } else {
      return `${usage.used} executions used this month`
    }
  }

  const handleUpgrade = (plan) => {
    // Navigate to profile page for subscription management with plan pre-selected
    const ev = new CustomEvent('navigate', { detail: 'profile', plan })
    window.dispatchEvent(ev)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 max-w-5xl w-full mx-4 relative">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-gray-400 hover:text-gray-300 hover:bg-gray-800 rounded-lg transition-colors"
          title="Close"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-start gap-4 mb-6">
          <div className="p-3 bg-yellow-600/20 rounded-lg">
            <AlertCircle className="h-6 w-6 text-yellow-400" />
          </div>
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-gray-100 mb-2">
              Subscription Required
            </h2>
            <p className="text-gray-400">
              You've reached the limit on your free trial. Upgrade to continue using AI Workflows.
            </p>
          </div>
        </div>

        {/* Current Usage */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Current Usage</span>
            <span className="text-sm font-medium text-gray-200">{getUsageText()}</span>
          </div>
          {usage.type === 'trial' && (
            <div className="mt-2 w-full bg-gray-700 rounded-full h-2">
              <div
                className="bg-yellow-600 h-2 rounded-full transition-all"
                style={{ width: `${(usage.used / usage.limit) * 100}%` }}
              />
            </div>
          )}
          {usage.type === 'monthly' && (
            <div className="mt-2 w-full bg-gray-700 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{ width: `${(usage.used / usage.limit) * 100}%` }}
              />
            </div>
          )}
        </div>

        {/* Subscription Plans */}
        <div className="grid md:grid-cols-3 gap-4 mb-6">
          {/* Basic Plan */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 hover:border-blue-600 transition-colors">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="h-5 w-5 text-blue-400" />
              <h3 className="text-lg font-semibold text-gray-200">Basic</h3>
            </div>
            <div className="mb-4">
              <span className="text-2xl font-bold text-gray-100">€5.99</span>
              <span className="text-sm text-gray-400">/month</span>
            </div>
            <p className="text-sm text-gray-400 mb-4">
              500 workflow executions per month
            </p>
            <ul className="space-y-2 mb-4 text-sm text-gray-300">
              <li className="flex items-center gap-2">
                <span className="text-green-400">✓</span>
                <span>500 executions/month</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-400">✓</span>
                <span>All AI features</span>
              </li>
            </ul>
            <button
              onClick={() => handleUpgrade('basic')}
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              Upgrade to Basic
            </button>
          </div>

          {/* Plus Plan */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 hover:border-purple-600 transition-colors">
            <div className="flex items-center gap-2 mb-3">
              <Crown className="h-5 w-5 text-purple-400" />
              <h3 className="text-lg font-semibold text-gray-200">Plus</h3>
              <span className="px-2 py-1 bg-purple-600/20 text-purple-400 rounded-full text-xs font-medium">
                Popular
              </span>
            </div>
            <div className="mb-4">
              <span className="text-2xl font-bold text-gray-100">€14.99</span>
              <span className="text-sm text-gray-400">/month</span>
            </div>
            <p className="text-sm text-gray-400 mb-4">
              2000 workflow executions per month
            </p>
            <ul className="space-y-2 mb-4 text-sm text-gray-300">
              <li className="flex items-center gap-2">
                <span className="text-green-400">✓</span>
                <span>2000 executions/month</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-400">✓</span>
                <span>All AI features</span>
              </li>
            </ul>
            <button
              onClick={() => handleUpgrade('plus')}
              className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
            >
              Upgrade to Plus
            </button>
          </div>

          {/* Pro Plan */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 hover:border-yellow-600 transition-colors">
            <div className="flex items-center gap-2 mb-3">
              <Crown className="h-5 w-5 text-yellow-400" />
              <h3 className="text-lg font-semibold text-gray-200">Pro</h3>
            </div>
            <div className="mb-4">
              <span className="text-2xl font-bold text-gray-100">€29.99</span>
              <span className="text-sm text-gray-400">/month</span>
            </div>
            <p className="text-sm text-gray-400 mb-4">
              5000 workflow executions per month
            </p>
            <ul className="space-y-2 mb-4 text-sm text-gray-300">
              <li className="flex items-center gap-2">
                <span className="text-green-400">✓</span>
                <span>5000 executions/month</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-400">✓</span>
                <span>All AI features</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-400">✓</span>
                <span>Priority support</span>
              </li>
            </ul>
            <button
              onClick={() => handleUpgrade('pro')}
              className="w-full px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg font-medium transition-colors"
            >
              Upgrade to Pro
            </button>
          </div>
        </div>

        {/* Info Message */}
        <div className="bg-blue-600/10 border border-blue-600/30 rounded-lg p-4">
          <p className="text-sm text-blue-300">
            <strong>Note:</strong> You've reached your free trial limit. Upgrade to continue activating and running AI workflows. Click any upgrade button above to get started.
          </p>
        </div>
      </div>
    </div>
  )
}

