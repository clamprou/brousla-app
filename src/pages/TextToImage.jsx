import React, { useCallback, useMemo, useState } from 'react'
import { Settings as SettingsIcon, ChevronDown, ChevronRight, Download, Loader2 } from 'lucide-react'
import WorkflowFileUpload from '../components/WorkflowFileUpload.jsx'
import ComfyUIErrorModal from '../components/ComfyUIErrorModal.jsx'
import { settingsManager } from '../utils/settingsManager.js'
import { WORKFLOW_BASE_URL } from '../config/workflowServer.js'

export default function TextToImage() {
  const [prompt, setPrompt] = useState('')
  const [negativePrompt, setNegativePrompt] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [imageUrl, setImageUrl] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)

  const [workflowFile, setWorkflowFile] = useState(null)
  const [promptId, setPromptId] = useState(null)
  const [statusMessage, setStatusMessage] = useState('')
  const [imageWidth, setImageWidth] = useState('')
  const [imageHeight, setImageHeight] = useState('')
  const [numSteps, setNumSteps] = useState('')
  const [cfgScale, setCfgScale] = useState('')
  const [seed, setSeed] = useState('')
  const [showComfyUIError, setShowComfyUIError] = useState(false)

    const startGeneration = useCallback(async () => {
    if (!prompt.trim() || !workflowFile) return
    
    // Check if ComfyUI path is configured
    const settings = settingsManager.getSettings()
    if (!settings.comfyuiPath) {
      alert('Please configure ComfyUI path in Settings first. Go to Settings and click "Select ComfyUI Folder".')
      return
    }
    
    setIsGenerating(true)
    setImageUrl('')
    setPromptId(null)
    setStatusMessage('Starting generation...')
    
    try {
      // Create FormData for the API call
      const formData = new FormData()
      
      // Create a Blob from the workflow JSON
      const workflowBlob = new Blob([JSON.stringify(workflowFile.json)], { type: 'application/json' })
      formData.append('workflow_file', workflowBlob, workflowFile.fileName)
      formData.append('prompt', prompt.trim())
      if (negativePrompt.trim()) {
        formData.append('negative_prompt', negativePrompt.trim())
      }
      
      // Add advanced settings if provided
      console.log('Advanced settings:', { imageWidth, imageHeight, numSteps, cfgScale })
      if (imageWidth.trim()) {
        formData.append('width', imageWidth.trim())
        console.log('Added width:', imageWidth.trim())
      }
      if (imageHeight.trim()) {
        formData.append('height', imageHeight.trim())
        console.log('Added height:', imageHeight.trim())
      }
      if (numSteps.trim()) {
        formData.append('steps', numSteps.trim())
        console.log('Added steps:', numSteps.trim())
      }
      if (cfgScale.trim()) {
        formData.append('cfg_scale', cfgScale.trim())
        console.log('Added cfg_scale:', cfgScale.trim())
      }
      if (seed.trim()) {
        formData.append('seed', seed.trim())
        console.log('Added seed:', seed.trim())
      }
      
      // Get ComfyUI URL from preferences (default to localhost)
      const prefs = JSON.parse(localStorage.getItem('userPreferences') || '{}')
      const comfyuiUrl = prefs.comfyUiServer || 'http://127.0.0.1:8188'
      formData.append('comfyui_url', comfyuiUrl)
      
      // Call the backend API to start generation
      const response = await fetch(`${WORKFLOW_BASE_URL}/generate_image`, {
        method: 'POST',
        body: formData
      })
      
      const result = await response.json()
      
      if (result.success) {
        setPromptId(result.prompt_id)
        setStatusMessage('Generation started, checking status...')
        
        // Start polling for status
        pollForStatus(result.prompt_id, comfyuiUrl)
      } else {
        console.error('Generation failed:', result.error)
        if (result.isComfyUIOffline) {
          setShowComfyUIError(true)
        } else {
          alert(`Generation failed: ${result.message}`)
        }
        setIsGenerating(false)
      }
    } catch (error) {
      console.error('Error starting generation:', error)
      // Check if error message indicates ComfyUI is offline
      const errorStr = error.message?.toLowerCase() || String(error).toLowerCase()
      if (errorStr.includes('connection') || errorStr.includes('refused') || errorStr.includes('failed to establish')) {
        setShowComfyUIError(true)
      } else {
        alert('Failed to start generation. Please check your ComfyUI server connection.')
      }
      setIsGenerating(false)
    }
  }, [prompt, negativePrompt, workflowFile, imageWidth, imageHeight, numSteps, cfgScale])

  const pollForStatus = useCallback(async (promptId, comfyuiUrl) => {
    const pollInterval = setInterval(async () => {
      try {
        const statusResponse = await fetch(`${WORKFLOW_BASE_URL}/status/${promptId}?comfyui_url=${encodeURIComponent(comfyuiUrl)}`)
        const statusResult = await statusResponse.json()
        
        if (statusResult.success) {
          setStatusMessage(statusResult.message)
          
          if (statusResult.status === 'completed') {
            clearInterval(pollInterval)
            
            // Get ComfyUI path from settings
            const settings = settingsManager.getSettings()
            const comfyuiPath = settings.comfyuiPath || null
            
            // Build the result URL with ComfyUI path if available
            let resultUrl = `${WORKFLOW_BASE_URL}/result/${promptId}?comfyui_url=${encodeURIComponent(comfyuiUrl)}`
            
            if (comfyuiPath) {
              resultUrl += `&comfyui_path=${encodeURIComponent(comfyuiPath)}`
            }
            // Get the result
            const resultResponse = await fetch(resultUrl)
            console.log('Result response:', resultResponse)
            const resultData = await resultResponse.json()
            
            console.log('Result data received:', resultData)
            
            if (resultData.success) {
              // Construct simple URL with filename, subfolder, and comfyui_path
              const imageUrl = `${WORKFLOW_BASE_URL}/comfyui-file?filename=${encodeURIComponent(resultData.filename)}&subfolder=${encodeURIComponent(resultData.subfolder || '')}&comfyui_path=${encodeURIComponent(comfyuiPath)}`
              console.log('Constructed imageUrl:', imageUrl)
              setImageUrl(imageUrl)
              setStatusMessage('Generation completed successfully!')
            } else {
              console.error('Result fetch failed:', resultData)
              alert(`Failed to get result: ${resultData.message || resultData.error || 'Unknown error'}`)
            }
            
            setIsGenerating(false)
          } else if (statusResult.status === 'error') {
            clearInterval(pollInterval)
            alert(`Generation error: ${statusResult.message}`)
            setIsGenerating(false)
          }
        } else {
          clearInterval(pollInterval)
          alert(`Status check failed: ${statusResult.message}`)
          setIsGenerating(false)
        }
      } catch (error) {
        console.error('Error polling status:', error)
        clearInterval(pollInterval)
        alert('Error checking generation status')
        setIsGenerating(false)
      }
    }, 2000) // Poll every 2 seconds
    
    // Cleanup interval after 5 minutes
    setTimeout(() => {
      clearInterval(pollInterval)
      if (isGenerating) {
        setIsGenerating(false)
        alert('Generation timed out')
      }
    }, 300000)
  }, [isGenerating])

  const handleDownload = useCallback(async () => {
    if (!imageUrl) return
    try {
      const res = await fetch(imageUrl)
      const blob = await res.blob()
      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = 'generated-image.png'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(objectUrl)
    } catch (e) {
      window.open(imageUrl, '_blank')
    }
  }, [imageUrl])

  const navigateToImageToVideo = useCallback(() => {
    const ev = new CustomEvent('navigate', { detail: 'image-to-video' })
    window.dispatchEvent(ev)
  }, [])

  return (
    <div className="p-6 h-full">
      <div className="mb-4">
        <h2 className="text-gray-200 text-base font-semibold">Text to Image</h2>
        <div className="mt-2">
          <WorkflowFileUpload value={workflowFile} onChange={setWorkflowFile} />
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left section */}
        <div className="space-y-6">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <label className="text-sm text-gray-300 mb-2">Prompt</label>
            <textarea
              className="w-full min-h-[200px] resize-vertical bg-gray-950 text-gray-100 rounded-lg border border-gray-800 p-3 focus:outline-none focus:ring-2 focus:ring-blue-600"
              placeholder="Describe the image you want to create…"
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
            />
          </div>

          {/* Advanced Settings */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <button
              onClick={() => setShowAdvanced(v => !v)}
              className="w-full flex items-center justify-between text-left hover:opacity-80 transition-opacity"
            >
              <div className="flex items-center gap-2 text-gray-200 font-medium">
                <SettingsIcon size={16} /> Advanced Settings
              </div>
              <div className="text-gray-400 hover:text-gray-200 transition-colors">
                {showAdvanced ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
              </div>
            </button>
            {showAdvanced && (
              <div className="mt-4 space-y-3">
                <div className="flex flex-col">
                  <label className="text-xs text-gray-400 mb-1">Negative Prompt</label>
                  <textarea
                    className="bg-gray-950 text-gray-100 rounded-lg border border-gray-800 p-2 focus:outline-none resize-vertical min-h-[80px]"
                    placeholder="Describe what you want to avoid..."
                    value={negativePrompt}
                    onChange={e => setNegativePrompt(e.target.value)}
                  />
                </div>
                
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="flex flex-col">
                  <label className="text-xs text-gray-400 mb-1">Width</label>
                  <input
                    type="number"
                    min={128}
                    step={64}
                    placeholder="e.g. 768"
                    className="bg-gray-950 text-gray-100 rounded-lg border border-gray-800 p-2 focus:outline-none"
                    value={imageWidth}
                    onChange={e => setImageWidth(e.target.value)}
                  />
                </div>
                <div className="flex flex-col">
                  <label className="text-xs text-gray-400 mb-1">Height</label>
                  <input
                    type="number"
                    min={128}
                    step={64}
                    placeholder="e.g. 768"
                    className="bg-gray-950 text-gray-100 rounded-lg border border-gray-800 p-2 focus:outline-none"
                    value={imageHeight}
                    onChange={e => setImageHeight(e.target.value)}
                  />
                </div>
                <div className="flex flex-col">
                  <label className="text-xs text-gray-400 mb-1">Steps</label>
                  <input
                    type="number"
                    min={1}
                    max={200}
                    placeholder="e.g. 25"
                    className="bg-gray-950 text-gray-100 rounded-lg border border-gray-800 p-2 focus:outline-none"
                    value={numSteps}
                    onChange={e => setNumSteps(e.target.value)}
                  />
                </div>
                <div className="flex flex-col">
                  <label className="text-xs text-gray-400 mb-1">CFG Scale</label>
                  <input
                    type="number"
                    step="0.5"
                    min={1}
                    max={20}
                    placeholder="e.g. 7.5"
                    className="bg-gray-950 text-gray-100 rounded-lg border border-gray-800 p-2 focus:outline-none"
                    value={cfgScale}
                    onChange={e => setCfgScale(e.target.value)}
                  />
                </div>
                <div className="flex flex-col">
                  <label className="text-xs text-gray-400 mb-1">Seed</label>
                  <input
                    type="number"
                    placeholder="e.g. 1234567890"
                    className="bg-gray-950 text-gray-100 rounded-lg border border-gray-800 p-2 focus:outline-none"
                    value={seed}
                    onChange={e => setSeed(e.target.value)}
                  />
                  <p className="text-xs text-gray-500 mt-1">Define the outcome of the generation</p>
                </div>
              </div>
              </div>
            )}
          </div>

          {/* Generate Button */}
          <div className="flex items-center gap-3">
            <button
              onClick={startGeneration}
              disabled={isGenerating || !prompt.trim() || !workflowFile}
              className={[
                'px-4 py-2 rounded-lg font-medium transition-colors',
                isGenerating || !prompt.trim() || !workflowFile ? 'bg-gray-700 text-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-500 text-white'
              ].join(' ')}
            >
              {isGenerating ? (
                <span className="inline-flex items-center gap-2">
                  <Loader2 className="animate-spin" size={16} /> Generating...
                </span>
              ) : (
                'Generate Image'
              )}
            </button>
          </div>
        </div>

        {/* Right panel */}
        <div className="flex flex-col bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex-1 rounded-lg bg-gray-950 border border-gray-800 min-h-[240px] md:min-h-[300px] flex items-center justify-center overflow-hidden">
            {isGenerating && (
              <div className="flex flex-col items-center gap-3 text-gray-300">
                <span className="h-10 w-10 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <div className="text-sm">{statusMessage}</div>
                {promptId && (
                  <div className="text-xs text-gray-400">Prompt ID: {promptId}</div>
                )}
              </div>
            )}
            {!isGenerating && imageUrl && (
              <img src={imageUrl} alt="Generated" className="object-contain max-h-full" />
            )}
            {!isGenerating && !imageUrl && (
              <div className="text-sm text-gray-400">No image yet. Enter a prompt and generate.</div>
            )}
          </div>

          <div className="mt-4">
            <button
              onClick={handleDownload}
              disabled={!imageUrl}
              className={[
                'inline-flex items-center gap-2 px-3 py-2 rounded-md transition-colors',
                imageUrl ? 'bg-gray-800 hover:bg-gray-700 text-gray-100' : 'bg-gray-800/60 text-gray-500 cursor-not-allowed'
              ].join(' ')}
            >
              <Download size={16} /> Download Image
            </button>
          </div>
        </div>
      </div>
      <ComfyUIErrorModal isOpen={showComfyUIError} onClose={() => setShowComfyUIError(false)} />
    </div>
  )
}


