import React from 'react'
import { Settings as SettingsIcon, ChevronDown, ChevronRight, Loader2, Download } from 'lucide-react'
import WorkflowFileUpload from '../components/WorkflowFileUpload.jsx'
import { settingsManager } from '../utils/settingsManager.js'

export default function TextToVideo() {
  const [prompt, setPrompt] = React.useState('')
  const [isGenerating, setIsGenerating] = React.useState(false)
  const [progress, setProgress] = React.useState(0)
  const [showAdvanced, setShowAdvanced] = React.useState(false)
  const [durationSec, setDurationSec] = React.useState(5)
  const [workflowFile, setWorkflowFile] = React.useState(null)
  const [promptId, setPromptId] = React.useState(null)
  const [statusMessage, setStatusMessage] = React.useState('')
  const [fps, setFps] = React.useState(24)
  const [videoUrl, setVideoUrl] = React.useState('')

  const startGeneration = async () => {
    if (!prompt.trim() || !workflowFile) return
    
    // Check if ComfyUI path is configured
    const settings = settingsManager.getSettings()
    if (!settings.comfyuiPath) {
      alert('Please configure ComfyUI path in Settings first. Go to Settings and click "Select ComfyUI Folder".')
      return
    }
    
    setIsGenerating(true)
    setProgress(0)
    setVideoUrl('')
    setPromptId(null)
    setStatusMessage('Starting generation...')

    try {
      // Create FormData for the API call
      const formData = new FormData()
      
      // Create a Blob from the workflow JSON
      const workflowBlob = new Blob([JSON.stringify(workflowFile.json)], { type: 'application/json' })
      formData.append('workflow_file', workflowBlob, workflowFile.fileName)
      formData.append('prompt', prompt.trim())
      
      // Get ComfyUI URL from preferences (default to localhost)
      const prefs = JSON.parse(localStorage.getItem('userPreferences') || '{}')
      const comfyuiUrl = prefs.comfyUiServer || 'http://127.0.0.1:8188'
      formData.append('comfyui_url', comfyuiUrl)
      
      // Call the backend API to start generation
      const response = await fetch('http://127.0.0.1:8000/generate_video', {
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
        alert(`Generation failed: ${result.message}`)
        setIsGenerating(false)
      }
    } catch (error) {
      console.error('Error starting generation:', error)
      alert('Failed to start generation. Please check your ComfyUI server connection.')
      setIsGenerating(false)
    }
  }

  const pollForStatus = async (promptId, comfyuiUrl) => {
    const pollInterval = setInterval(async () => {
      try {
        const statusResponse = await fetch(`http://127.0.0.1:8000/status/${promptId}?comfyui_url=${encodeURIComponent(comfyuiUrl)}`)
        const statusResult = await statusResponse.json()
        
        if (statusResult.success) {
          setStatusMessage(statusResult.message)
          setProgress(statusResult.progress || 0)
          
          if (statusResult.status === 'completed') {
            clearInterval(pollInterval)
            
            // Get ComfyUI path from settings
            const settings = settingsManager.getSettings()
            const comfyuiPath = settings.comfyuiPath || null
            
            // Build the result URL with ComfyUI path if available
            let resultUrl = `http://127.0.0.1:8000/result/${promptId}?comfyui_url=${encodeURIComponent(comfyuiUrl)}`
            if (comfyuiPath) {
              resultUrl += `&comfyui_path=${encodeURIComponent(comfyuiPath)}`
            }
            
            // Get the result
            const resultResponse = await fetch(resultUrl)
            const resultData = await resultResponse.json()
            
            console.log('Result data received:', resultData)
            
            if (resultData.success) {
              // Construct simple URL with filename, subfolder, and comfyui_path
              const videoUrl = `http://127.0.0.1:8000/comfyui-file?filename=${encodeURIComponent(resultData.filename)}&subfolder=${encodeURIComponent(resultData.subfolder || '')}&comfyui_path=${encodeURIComponent(comfyuiPath)}`
              console.log('Constructed videoUrl:', videoUrl)
              setVideoUrl(videoUrl)
              setStatusMessage('Generation completed successfully!')
              setProgress(100)
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
    
    // Cleanup interval after 10 minutes (videos take longer)
    setTimeout(() => {
      clearInterval(pollInterval)
      if (isGenerating) {
        setIsGenerating(false)
        alert('Generation timed out')
      }
    }, 600000)
  }

  const onDownload = () => {
    if (!videoUrl) return
    const link = document.createElement('a')
    link.href = videoUrl
    link.download = 'text-to-video.mp4'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div className="p-6">
      <div className="mb-4">
        <h2 className="text-gray-200 text-base font-semibold">Text to Video</h2>
        <div className="mt-2">
          <WorkflowFileUpload value={workflowFile} onChange={setWorkflowFile} />
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left section */}
        <div className="space-y-6">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <label className="block text-sm text-gray-300 mb-2">Prompt</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Describe the video you want to create…"
              rows={10}
              className="w-full resize-y min-h-[220px] rounded-md bg-gray-950 border border-gray-800 p-3 text-gray-200 placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
            <div className="mt-4 flex items-center gap-3">
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
                  'Generate Video'
                )}
              </button>
              {isGenerating && (
                <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-600 transition-all" style={{ width: `${progress}%` }} />
                </div>
              )}
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-gray-200 font-medium">
                <SettingsIcon size={16} /> Advanced Settings
              </div>
              <button
                onClick={() => setShowAdvanced(v => !v)}
                className="text-gray-400 hover:text-gray-200 transition-colors"
              >
                {showAdvanced ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
              </button>
            </div>
            {showAdvanced && (
              <div className="mt-4 space-y-5">
                {/* Duration */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-sm text-gray-300">Duration</label>
                    <span className="text-xs text-gray-400">{durationSec}s</span>
                  </div>
                  <input
                    type="range"
                    min={1}
                    max={10}
                    value={durationSec}
                    onChange={(e) => setDurationSec(Number(e.target.value))}
                    className="w-full"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="text-sm text-gray-300">FPS</label>
                    <select
                      value={fps}
                      onChange={(e) => setFps(Number(e.target.value))}
                      className="mt-1 w-full bg-gray-950 border border-gray-800 rounded-md p-2 text-gray-200"
                    >
                      <option value={12}>12</option>
                      <option value={24}>24</option>
                      <option value={30}>30</option>
                      <option value={60}>60</option>
                    </select>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right section */}
        <div className="space-y-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 h-[420px] flex items-center justify-center">
            {videoUrl ? (
              <video
                src={videoUrl}
                className="w-full h-full object-contain rounded-lg"
                controls
                autoPlay
                loop
              />
            ) : (
              <div className="text-center text-gray-400">
                <p className="text-sm">Your generated video will appear here.</p>
                {!isGenerating && <p className="text-xs mt-1">Enter a prompt and click Generate.</p>}
              {isGenerating && (
                <div className="mt-4 inline-flex flex-col items-center gap-2 text-gray-300">
                  <div className="inline-flex items-center gap-2">
                    <Loader2 className="animate-spin" size={18} />
                    <span>Generating video ({progress}%)...</span>
                  </div>
                  <div className="text-sm text-gray-400">{statusMessage}</div>
                  {promptId && (
                    <div className="text-xs text-gray-500">Prompt ID: {promptId}</div>
                  )}
                </div>
              )}
              </div>
            )}
          </div>

          <div>
            <button
              onClick={onDownload}
              disabled={!videoUrl}
              className={[
                'inline-flex items-center gap-2 px-3 py-2 rounded-md transition-colors',
                videoUrl ? 'bg-gray-800 hover:bg-gray-700 text-gray-100' : 'bg-gray-800/60 text-gray-500 cursor-not-allowed'
              ].join(' ')}
            >
              <Download size={16} /> Download Video
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

