import React from 'react'
import { Bot, Workflow, Zap, ArrowRight, ImageIcon, Film, Type, Upload, Sparkles, Plus } from 'lucide-react'

export default function AIWorkflows() {
  const features = [
    {
      icon: Workflow,
      title: 'Multi-Step Pipelines',
      description: 'Chain together complex workflows like text → image → video → upscale → upload'
    },
    {
      icon: Bot,
      title: 'Autonomous Agents',
      description: 'Let AI agents handle entire content creation processes with minimal oversight'
    },
    {
      icon: Zap,
      title: 'Smart Concatenation',
      description: 'Automatically merge and combine multiple generated outputs into cohesive content'
    }
  ]

  const exampleWorkflows = [
    {
      title: 'Social Media Campaign',
      steps: ['Text Prompt', 'Generate Image', 'Create Video', 'Add Captions', 'Export']
    },
    {
      title: 'Product Showcase',
      steps: ['Product Description', 'Generate Images', 'Create Demo Video', 'Add Music', 'Upload']
    },
    {
      title: 'Educational Content',
      steps: ['Topic Research', 'Generate Visuals', 'Create Animation', 'Add Narration', 'Publish']
    }
  ]

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600/20 rounded-lg">
              <Bot className="h-6 w-6 text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-100">AI Workflows</h1>
              <p className="text-gray-400">Advanced AI-powered content generation pipelines</p>
            </div>
          </div>
          <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors">
            <Plus className="h-4 w-4" />
            Create Workflow
          </button>
        </div>
      </div>

      {/* Main Description Card */}
      <div className="bg-gradient-to-br from-gray-900 to-gray-800 border border-gray-700 rounded-xl p-8 mb-8">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600/20 rounded-full mb-4">
            <Sparkles className="h-8 w-8 text-blue-400" />
          </div>
          <h2 className="text-xl font-semibold text-gray-100 mb-3">Advanced AI Workflows</h2>
          <p className="text-gray-400 max-w-2xl mx-auto">
            Design sophisticated, multi-step content creation pipelines that combine multiple AI models 
            and automation tools. Create autonomous workflows that can handle complex content generation 
            tasks from start to finish.
          </p>
        </div>
      </div>

      {/* Features Grid */}
      <div className="grid md:grid-cols-3 gap-6 mb-8">
        {features.map((feature, index) => (
          <div key={index} className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-blue-600/20 rounded-lg">
                <feature.icon className="h-5 w-5 text-blue-400" />
              </div>
              <h3 className="font-semibold text-gray-200">{feature.title}</h3>
            </div>
            <p className="text-sm text-gray-400">{feature.description}</p>
          </div>
        ))}
      </div>

      {/* Example Workflows */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-gray-200 mb-4">Example Workflow Templates</h3>
        <div className="grid md:grid-cols-3 gap-4">
          {exampleWorkflows.map((workflow, index) => (
            <div key={index} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
              <h4 className="font-medium text-gray-200 mb-3">{workflow.title}</h4>
              <div className="space-y-2">
                {workflow.steps.map((step, stepIndex) => (
                  <div key={stepIndex} className="flex items-center gap-2 text-sm">
                    <div className="flex items-center justify-center w-6 h-6 bg-gray-700 rounded-full text-xs text-gray-300">
                      {stepIndex + 1}
                    </div>
                    <span className="text-gray-400">{step}</span>
                    {stepIndex < workflow.steps.length - 1 && (
                      <ArrowRight className="h-3 w-3 text-gray-500 ml-auto" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}


