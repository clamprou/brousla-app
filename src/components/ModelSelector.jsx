import React from 'react'

const CUSTOM_LABEL = 'Custom Workflow (ComfyUI)'

export default function ModelSelector({ value, onChange, options, onCustomWorkflowChange }) {
  const baseOptions = options && options.length ? options : ['FLUX Schnell', 'Pika', 'RunwayML']
  const allOptions = React.useMemo(() => [...baseOptions, CUSTOM_LABEL], [baseOptions])

  const [customWorkflowMeta, setCustomWorkflowMeta] = React.useState(null)
  const fileInputRef = React.useRef(null)

  const isCustomSelected = value === CUSTOM_LABEL

  const handleSelectChange = (e) => {
    const next = e.target.value
    onChange?.(next)
    if (next !== CUSTOM_LABEL) {
      setCustomWorkflowMeta(null)
      onCustomWorkflowChange?.(null)
    }
  }

  const onChooseFileClick = () => fileInputRef.current?.click()

  const onFileChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const text = await file.text()
      const json = JSON.parse(text)
      const payload = { fileName: file.name, json }
      setCustomWorkflowMeta(payload)
      onCustomWorkflowChange?.(payload)
    } catch (err) {
      console.error('Invalid workflow JSON', err)
      setCustomWorkflowMeta(null)
      onCustomWorkflowChange?.(null)
    }
  }

  return (
    <div className="inline-flex items-center gap-3">
      <div className="inline-flex items-center gap-2">
        <label className="text-xs text-gray-400">Model</label>
        <select
          value={value}
          onChange={handleSelectChange}
          className="bg-gray-950 border border-gray-800 text-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-600"
        >
          {allOptions.map(m => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>

      {isCustomSelected && (
        <div className="inline-flex items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={onFileChange}
          />
          <button
            type="button"
            onClick={onChooseFileClick}
            className="px-3 py-1 rounded-md bg-gray-800 hover:bg-gray-700 text-gray-100 text-sm transition-colors border border-gray-700 shadow-sm"
          >
            Choose File
          </button>
          {customWorkflowMeta?.fileName && (
            <span className="text-xs text-gray-400 truncate max-w-[200px]" title={customWorkflowMeta.fileName}>
              {customWorkflowMeta.fileName}
            </span>
          )}
        </div>
      )}
    </div>
  )
}


