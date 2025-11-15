import React from 'react'
import { Upload, Settings as SettingsIcon, ChevronDown, ChevronRight, Loader2, Download, RotateCcw, ArrowRight } from 'lucide-react'
import WorkflowFileUpload from '../components/WorkflowFileUpload.jsx'
import ComfyUIErrorModal from '../components/ComfyUIErrorModal.jsx'
import { settingsManager } from '../utils/settingsManager.js'

export default function ImageToVideo() {
  const [selectedImage, setSelectedImage] = React.useState(null)
  const [imagePreviewUrl, setImagePreviewUrl] = React.useState('')
  const [isDragging, setIsDragging] = React.useState(false)
  const [isGenerating, setIsGenerating] = React.useState(false)
  const [progress, setProgress] = React.useState(0)
  const [showAdvanced, setShowAdvanced] = React.useState(false)
  const [positivePrompt, setPositivePrompt] = React.useState('')
  const [negativePrompt, setNegativePrompt] = React.useState('')
  const [workflowFile, setWorkflowFile] = React.useState(null)
  const [promptId, setPromptId] = React.useState(null)
  const [statusMessage, setStatusMessage] = React.useState('')
  const [fps, setFps] = React.useState('')
  const [steps, setSteps] = React.useState('')
  const [length, setLength] = React.useState('')
  const [seed, setSeed] = React.useState('')
  const [videoUrl, setVideoUrl] = React.useState('')
  const [showComfyUIError, setShowComfyUIError] = React.useState(false)

  const fileInputRef = React.useRef(null)

  React.useEffect(() => {
    return () => {
      if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl)
    }
  }, [imagePreviewUrl])

  const onBrowseClick = () => fileInputRef.current?.click()

  const handleFiles = (files) => {
    const file = files?.[0]
    if (!file) return
    setSelectedImage(file)
    const url = URL.createObjectURL(file)
    if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl)
    setImagePreviewUrl(url)
  }

  const onInputChange = (e) => handleFiles(e.target.files)

  const onDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const onDragLeave = () => setIsDragging(false)

  const onDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  const startGeneration = async () => {
    if (!selectedImage || !workflowFile) return
    
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
      
      // Add the selected image
      formData.append('image_file', selectedImage)
      
      // Get ComfyUI URL from preferences (default to localhost)
      const prefs = JSON.parse(localStorage.getItem('userPreferences') || '{}')
      const comfyuiUrl = prefs.comfyUiServer || 'http://127.0.0.1:8188'
      formData.append('comfyui_url', comfyuiUrl)
      
      // Add ComfyUI path to form data
      formData.append('comfyui_path', settings.comfyuiPath)
      
      // Add prompts if provided
      if (positivePrompt.trim()) {
        formData.append('positive_prompt', positivePrompt.trim())
      }
      if (negativePrompt.trim()) {
        formData.append('negative_prompt', negativePrompt.trim())
      }
      
      // Add advanced settings if provided
      if (fps.trim()) {
        formData.append('fps', fps.trim())
      }
      if (steps.trim()) {
        formData.append('steps', steps.trim())
      }
      if (length.trim()) {
        formData.append('length', length.trim())
      }
      if (seed.trim()) {
        formData.append('seed', seed.trim())
      }
      
      // Call the backend API to start generation
      const response = await fetch('http://127.0.0.1:8000/generate_image_to_video', {
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
    link.download = 'image-to-video.mp4'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div className="p-6">
      <div className="mb-4">
        <h2 className="text-gray-200 text-base font-semibold">Image to Video</h2>
        <div className="mt-2">
          <WorkflowFileUpload value={workflowFile} onChange={setWorkflowFile} />
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left section */}
        <div className="space-y-6">
          <div
            className={[
              'bg-gray-900 border rounded-xl p-6 transition-colors cursor-pointer',
              isDragging ? 'border-blue-500 bg-blue-950/20' : 'border-gray-800 hover:border-gray-700'
            ].join(' ')}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
            onClick={onBrowseClick}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={onInputChange}
            />
            <div className="flex flex-col items-center justify-center text-center">
              {imagePreviewUrl ? (
                <div className="w-full">
                  <img
                    src={imagePreviewUrl}
                    alt="Uploaded preview"
                    className="w-full h-56 object-contain rounded-lg bg-gray-950 border border-gray-800"
                  />
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-center w-16 h-16 rounded-full bg-gray-800/60 text-gray-300">
                    <Upload size={24} />
                  </div>
                  <p className="mt-4 text-gray-200 font-medium">Drag and drop an image</p>
                  <p className="text-gray-400 text-sm mt-1">or click anywhere to browse</p>
                </>
              )}
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <label className="text-sm text-gray-300 mb-2">Positive Prompt (optional)</label>
            <textarea
              value={positivePrompt}
              onChange={(e) => setPositivePrompt(e.target.value)}
              placeholder="Describe the motion you want..."
              rows={3}
              className="w-full resize-y min-h-[80px] rounded-md bg-gray-950 border border-gray-800 p-3 text-gray-200 placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>

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
              <div className="mt-4 space-y-5">
                <div>
                  <label className="text-sm text-gray-300 mb-1">Negative Prompt</label>
                  <textarea
                    value={negativePrompt}
                    onChange={(e) => setNegativePrompt(e.target.value)}
                    placeholder="Describe what you want to avoid..."
                    rows={2}
                    className="w-full resize-y min-h-[60px] rounded-md bg-gray-950 border border-gray-800 p-3 text-gray-200 placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="text-sm text-gray-300 mb-1">FPS</label>
                    <input
                      type="number"
                      min={1}
                      placeholder="e.g. 24"
                      value={fps}
                      onChange={(e) => setFps(e.target.value)}
                      className="w-full bg-gray-950 border border-gray-800 rounded-md p-2 text-gray-200 placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-gray-300 mb-1">Steps</label>
                    <input
                      type="number"
                      min={1}
                      placeholder="e.g. 50"
                      value={steps}
                      onChange={(e) => setSteps(e.target.value)}
                      className="w-full bg-gray-950 border border-gray-800 rounded-md p-2 text-gray-200 placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-sm text-gray-300 mb-1">Length</label>
                  <input
                    type="number"
                    min={1}
                    placeholder="e.g. 1, 5, 9, 13..."
                    value={length}
                    onChange={(e) => {
                      const val = e.target.value
                      setLength(val)
                    }}
                    onBlur={(e) => {
                      const val = e.target.value
                      if (val === '') {
                        setLength('')
                        return
                      }
                      const numVal = parseInt(val)
                      if (!isNaN(numVal) && numVal > 0) {
                        // Check if value matches pattern: 1 + 4*n where n >= 0
                        if ((numVal - 1) % 4 !== 0) {
                          // Round to nearest valid value
                          const rounded = Math.round((numVal - 1) / 4) * 4 + 1
                          setLength(Math.max(1, rounded).toString())
                        }
                      }
                    }}
                    className="w-full bg-gray-950 border border-gray-800 rounded-md p-2 text-gray-200 placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                  <p className="text-xs text-gray-400 mt-1">Values: 1, 5, 9, 13, 17, 21... (increments of 4)</p>
                </div>

                <div>
                  <label className="text-sm text-gray-300 mb-1">Seed</label>
                  <input
                    type="number"
                    placeholder="e.g. 1234567890"
                    value={seed}
                    onChange={(e) => setSeed(e.target.value)}
                    className="w-full bg-gray-950 border border-gray-800 rounded-md p-2 text-gray-200 placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600"
                  />
                  <p className="text-xs text-gray-400 mt-1">Define the outcome of the video</p>
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={startGeneration}
              disabled={isGenerating || !selectedImage || !workflowFile}
              className={[
                'px-4 py-2 rounded-lg font-medium transition-colors',
                isGenerating || !selectedImage || !workflowFile ? 'bg-gray-700 text-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-500 text-white'
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
                <div
                  className="h-full bg-blue-600 transition-all"
                  style={{ width: `${progress}%` }}
                />
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
                {!isGenerating && <p className="text-xs mt-1">Upload an image and click Generate.</p>}
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

          <div className="flex flex-wrap items-center gap-2">
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
      <ComfyUIErrorModal isOpen={showComfyUIError} onClose={() => setShowComfyUIError(false)} />
    </div>
  )
}

