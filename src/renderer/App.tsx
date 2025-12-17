import React, { useEffect, useMemo, useState } from 'react'
import axios from 'axios'

type HistoryItem = { id: string; prompt: string; resultPath?: string; createdAt: string }
type Preferences = { openaiApiKey?: string; comfyUiServer?: string; defaultWorkflow?: string }

const backendURL = 'http://127.0.0.1:8000'

export function App(): JSX.Element {
  const [prompt, setPrompt] = useState('')
  const [workflow, setWorkflow] = useState('image_generation')
  const [outputPath, setOutputPath] = useState<string | undefined>()
  const [isRunning, setIsRunning] = useState(false)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [prefs, setPrefs] = useState<Preferences>({})
  const [tab, setTab] = useState<'app' | 'settings'>('app')

  useEffect(() => {
    void refreshHistory()
    void refreshPreferences()
  }, [])

  async function refreshHistory() {
    try {
      const res = await axios.get(`${backendURL}/history`)
      setHistory(res.data)
    } catch (e) {
      console.error(e)
    }
  }

  async function refreshPreferences() {
    try {
      const res = await axios.get(`${backendURL}/preferences`)
      setPrefs(res.data)
    } catch (e) {
      console.error(e)
    }
  }

  async function savePreferences(next: Preferences) {
    try {
      await axios.post(`${backendURL}/preferences`, next)
      setPrefs(next)
    } catch (e) {
      console.error(e)
    }
  }

  async function runWorkflow() {
    setIsRunning(true)
    setOutputPath(undefined)
    try {
      const res = await axios.post(`${backendURL}/run_workflow`, {
        prompt,
        workflow,
      })
      setOutputPath(res.data?.resultPath)
      await refreshHistory()
    } catch (e) {
      console.error(e)
    } finally {
      setIsRunning(false)
    }
  }

  const workflows = useMemo(
    () => [
      { id: 'image_generation', name: 'Image Generation' },
      { id: 'video_generation', name: 'Video Generation' },
    ],
    []
  )

  return (
    <div className="container">
      <aside className="sidebar">
        <div className="brand">Brousla</div>
        <nav>
          <button className={tab === 'app' ? 'active' : ''} onClick={() => setTab('app')}>App</button>
          <button className={tab === 'settings' ? 'active' : ''} onClick={() => setTab('settings')}>Settings</button>
        </nav>
        <div className="workflows">
          <h4>Workflows</h4>
          {workflows.map(w => (
            <button key={w.id} className={workflow === w.id ? 'active' : ''} onClick={() => setWorkflow(w.id)}>
              {w.name}
            </button>
          ))}
        </div>
        <div className="history">
          <h4>History</h4>
          <ul>
            {history.map(h => (
              <li key={h.id} title={h.prompt}>{new Date(h.createdAt).toLocaleString()}</li>
            ))}
          </ul>
        </div>
      </aside>

      {tab === 'app' ? (
        <main className="main">
          <div className="prompt-box">
            <textarea value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Describe what to create..." />
            <div className="actions">
              <button onClick={runWorkflow} disabled={isRunning || !prompt.trim()}>{isRunning ? 'Running...' : 'Run Workflow'}</button>
            </div>
          </div>
          <div className="output">
            <h3>Output Preview</h3>
            {!outputPath && <div className="placeholder">No output yet.</div>}
            {outputPath?.match(/\.(png|jpg|jpeg|gif|webp)$/i) && (
              <img src={`${backendURL}/file?path=${encodeURIComponent(outputPath)}`} alt="result" />
            )}
            {outputPath?.match(/\.(mp4|webm|mov)$/i) && (
              <video controls src={`${backendURL}/file?path=${encodeURIComponent(outputPath)}`}></video>
            )}
          </div>
        </main>
      ) : (
        <main className="main">
          <h3>Settings</h3>
          <label>
            OpenAI API Key
            <input type="password" value={prefs.openaiApiKey || ''} onChange={e => setPrefs({ ...prefs, openaiApiKey: e.target.value })} />
          </label>
          <label>
            ComfyUI Server URL
            <input type="text" value={prefs.comfyUiServer || ''} onChange={e => setPrefs({ ...prefs, comfyUiServer: e.target.value })} placeholder="http://127.0.0.1:8188" />
          </label>
          <label>
            Default Workflow
            <select value={prefs.defaultWorkflow || workflow} onChange={e => setPrefs({ ...prefs, defaultWorkflow: e.target.value })}>
              {workflows.map(w => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </select>
          </label>
          <button onClick={() => savePreferences(prefs)}>Save</button>
        </main>
      )}
    </div>
  )
}


