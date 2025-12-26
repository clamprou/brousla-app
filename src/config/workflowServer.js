// Workflow Server Configuration (local workflow-server / ComfyUI proxy)
// Can be overridden at build time via VITE_WORKFLOW_BASE_URL

export const WORKFLOW_BASE_URL =
  import.meta.env.VITE_WORKFLOW_BASE_URL || 'http://127.0.0.1:8000'

