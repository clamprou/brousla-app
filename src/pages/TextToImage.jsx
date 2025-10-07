import React, { useCallback, useMemo, useState } from 'react'
import ModelSelector from '../components/ModelSelector.jsx'

export default function TextToImage() {
  const [prompt, setPrompt] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [imageUrl, setImageUrl] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)

  const [model, setModel] = useState('Flux Schnell')
  const [imageSize, setImageSize] = useState('768x768')
  const [numSteps, setNumSteps] = useState(25)
  const [cfgScale, setCfgScale] = useState(7.5)

  const sizeOptions = useMemo(() => [
    '512x512',
    '768x768',
    '1024x1024'
  ], [])

  const startGeneration = useCallback(() => {
    if (!prompt.trim()) return
    setIsGenerating(true)
    setImageUrl('')
    // Mock API call with delay; swap with real backend call later
    setTimeout(() => {
      // Use a deterministic placeholder based on settings to avoid caching artifacts
      const size = imageSize.split('x')[0]
      const demoUrl = `https://picsum.photos/seed/${encodeURIComponent(prompt)}-${size}/${size}`
      setImageUrl(demoUrl)
      setIsGenerating(false)
    }, 2000)
  }, [prompt, imageSize])

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
          <ModelSelector value={model} onChange={setModel} options={["Flux Schnell", "HiDream"]} />
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-full">
        {/* Left panel */}
        <div className="flex flex-col bg-gray-900 border border-gray-800 rounded-xl p-4">
          <label className="text-sm text-gray-300 mb-2">Prompt</label>
          <textarea
            className="flex-1 min-h-[200px] md:min-h-[300px] resize-vertical bg-gray-950 text-gray-100 rounded-lg border border-gray-800 p-3 focus:outline-none focus:ring-2 focus:ring-indigo-600"
            placeholder="Describe the image you want to create…"
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
          />

          <button
            onClick={startGeneration}
            disabled={isGenerating || !prompt.trim()}
            className={`mt-4 inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors
              ${isGenerating || !prompt.trim() ? 'bg-indigo-700/50 text-gray-300 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-500 text-white'}`}
          >
            {isGenerating && (
              <span className="inline-block h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            )}
            {isGenerating ? 'Generating…' : 'Generate Image'}
          </button>

          {/* Advanced Settings */}
          <div className="mt-4">
            <button
              onClick={() => setShowAdvanced(v => !v)}
              className="w-full text-left text-sm text-gray-300 hover:text-white"
            >
              {showAdvanced ? 'Hide Advanced Settings' : 'Show Advanced Settings'}
            </button>
            {showAdvanced && (
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
                
                <div className="flex flex-col">
                  <label className="text-xs text-gray-400 mb-1">Image Size</label>
                  <select
                    className="bg-gray-950 text-gray-100 rounded-lg border border-gray-800 p-2 focus:outline-none"
                    value={imageSize}
                    onChange={e => setImageSize(e.target.value)}
                  >
                    {sizeOptions.map(opt => <option key={opt}>{opt}</option>)}
                  </select>
                </div>
                <div className="flex flex-col">
                  <label className="text-xs text-gray-400 mb-1">Number of Steps</label>
                  <input
                    type="number"
                    min={1}
                    max={200}
                    className="bg-gray-950 text-gray-100 rounded-lg border border-gray-800 p-2 focus:outline-none"
                    value={numSteps}
                    onChange={e => setNumSteps(Number(e.target.value))}
                  />
                </div>
                <div className="flex flex-col">
                  <label className="text-xs text-gray-400 mb-1">CFG Scale</label>
                  <input
                    type="number"
                    step="0.5"
                    min={1}
                    max={20}
                    className="bg-gray-950 text-gray-100 rounded-lg border border-gray-800 p-2 focus:outline-none"
                    value={cfgScale}
                    onChange={e => setCfgScale(Number(e.target.value))}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right panel */}
        <div className="flex flex-col bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex-1 rounded-lg bg-gray-950 border border-gray-800 min-h-[240px] md:min-h-[300px] flex items-center justify-center overflow-hidden">
            {isGenerating && (
              <div className="flex flex-col items-center gap-3 text-gray-300">
                <span className="h-10 w-10 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <div className="text-sm">Generating preview…</div>
              </div>
            )}
            {!isGenerating && imageUrl && (
              <img src={imageUrl} alt="Generated" className="object-contain max-h-full" />
            )}
            {!isGenerating && !imageUrl && (
              <div className="text-sm text-gray-400">No image yet. Enter a prompt and generate.</div>
            )}
          </div>

          <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-2">
            <button
              onClick={handleDownload}
              disabled={!imageUrl}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors
                ${imageUrl ? 'bg-gray-800 hover:bg-gray-700 text-white' : 'bg-gray-800/50 text-gray-400 cursor-not-allowed'}`}
            >
              Download Image
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}


