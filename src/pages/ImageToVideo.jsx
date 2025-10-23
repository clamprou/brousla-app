import React from 'react'
import { Upload, Settings as SettingsIcon, ChevronDown, ChevronRight, Loader2, Download, RotateCcw, ArrowRight } from 'lucide-react'
import WorkflowFileUpload from '../components/WorkflowFileUpload.jsx'

export default function ImageToVideo() {
  const [selectedImage, setSelectedImage] = React.useState(null)
  const [imagePreviewUrl, setImagePreviewUrl] = React.useState('')
  const [isDragging, setIsDragging] = React.useState(false)
  const [isGenerating, setIsGenerating] = React.useState(false)
  const [progress, setProgress] = React.useState(0)
  const [showAdvanced, setShowAdvanced] = React.useState(false)
  const [durationSec, setDurationSec] = React.useState(5)
  const [motionStrength, setMotionStrength] = React.useState(50)
  const [workflowFile, setWorkflowFile] = React.useState(null)
  const [fps, setFps] = React.useState(24)
  const [videoUrl, setVideoUrl] = React.useState('')

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
    setIsGenerating(true)
    setProgress(0)
    setVideoUrl('')

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
      
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 5, 90))
      }, 2000)
      
      // Call the backend API
      const response = await fetch('http://127.0.0.1:8000/generate_image_to_video', {
        method: 'POST',
        body: formData
      })
      
      clearInterval(progressInterval)
      setProgress(100)
      
      const result = await response.json()
      
      if (result.success) {
        // Convert the result path to a URL that can be displayed
        const videoUrl = `http://127.0.0.1:8000/file?path=${encodeURIComponent(result.resultPath)}`
        setVideoUrl(videoUrl)
      } else {
        console.error('Generation failed:', result.error)
        alert(`Generation failed: ${result.message}`)
      }
    } catch (error) {
      console.error('Error generating video:', error)
      alert('Failed to generate video. Please check your ComfyUI server connection.')
    } finally {
      setIsGenerating(false)
    }
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
              'bg-gray-900 border rounded-xl p-6 transition-colors',
              isDragging ? 'border-blue-500' : 'border-gray-800'
            ].join(' ')}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
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
                  <p className="text-gray-400 text-sm">or</p>
                  <button
                    onClick={onBrowseClick}
                    className="mt-2 px-3 py-1.5 text-sm rounded-md bg-blue-600 hover:bg-blue-500 text-white transition-colors"
                  >
                    Click to upload
                  </button>
                </>
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

                {/* Motion Strength */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-sm text-gray-300">Motion strength</label>
                    <span className="text-xs text-gray-400">{motionStrength}</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={motionStrength}
                    onChange={(e) => setMotionStrength(Number(e.target.value))}
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
                  <div className="mt-4 inline-flex items-center gap-2 text-gray-300">
                    <Loader2 className="animate-spin" size={18} />
                    <span>Generating video ({progress}%)...</span>
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
    </div>
  )
}

