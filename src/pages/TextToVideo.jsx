import React from 'react'
import { Settings as SettingsIcon, ChevronDown, ChevronRight, Loader2, Download } from 'lucide-react'

export default function TextToVideo() {
  const [prompt, setPrompt] = React.useState('')
  const [isGenerating, setIsGenerating] = React.useState(false)
  const [progress, setProgress] = React.useState(0)
  const [showAdvanced, setShowAdvanced] = React.useState(false)
  const [durationSec, setDurationSec] = React.useState(5)
  const [model, setModel] = React.useState('FLUX Schnell')
  const [fps, setFps] = React.useState(24)
  const [videoUrl, setVideoUrl] = React.useState('')

  const startGeneration = () => {
    if (!prompt.trim()) return
    setIsGenerating(true)
    setProgress(0)
    setVideoUrl('')

    const start = Date.now()
    const durationMs = 3000
    const interval = setInterval(() => {
      const elapsed = Date.now() - start
      const pct = Math.min(100, Math.round((elapsed / durationMs) * 100))
      setProgress(pct)
      if (elapsed >= durationMs) {
        clearInterval(interval)
        setVideoUrl('/sample-video.mp4')
        setIsGenerating(false)
      }
    }, 80)
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
                disabled={isGenerating || !prompt.trim()}
                className={[
                  'px-4 py-2 rounded-lg font-medium transition-colors',
                  isGenerating || !prompt.trim() ? 'bg-gray-700 text-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-500 text-white'
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

                {/* Model selector */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="text-sm text-gray-300">Model</label>
                    <select
                      value={model}
                      onChange={(e) => setModel(e.target.value)}
                      className="mt-1 w-full bg-gray-950 border border-gray-800 rounded-md p-2 text-gray-200"
                    >
                      <option>FLUX Schnell</option>
                      <option>Pika</option>
                      <option>RunwayML</option>
                    </select>
                  </div>
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
                  <div className="mt-4 inline-flex items-center gap-2 text-gray-300">
                    <Loader2 className="animate-spin" size={18} />
                    <span>Generating video ({progress}%)...</span>
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

