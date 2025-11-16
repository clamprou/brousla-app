# Brousla App - Desktop AI Application

Electron + React desktop application with dual Python FastAPI backend architecture.

## Architecture Overview

This application uses a **two-server architecture**:

1. **Authentication & AI Server** (`brousla-app-server/`) - Port 8001
   - User authentication (JWT, register, login)
   - AI chat endpoints (OpenAI integration)
   - Rate limiting and security

2. **ComfyUI Workflow Server** (`server/`) - Port 8000
   - ComfyUI workflow execution
   - Image and video generation
   - Workflow scheduling and management

3. **Desktop Client** (`src/`, `electron/`)
   - Electron + React frontend
   - Communicates with both backend servers
   - Never directly calls OpenAI/RunPod APIs

## Quickstart

### Prerequisites

1. **Node.js 18+** and **Python 3.10+**
2. **FFMPEG** (required for multi-clip video concatenation):
   - Windows: Download from https://ffmpeg.org/download.html and add to PATH
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt-get install ffmpeg` or `sudo yum install ffmpeg`

### Installation

1. **Install Node dependencies:**
```bash
npm install
```

2. **Install Python dependencies for both servers:**

```bash
# ComfyUI Workflow Server
pip install -r server/requirements.txt

# Authentication & AI Server
pip install -r brousla-app-server/requirements.txt
```

3. **Configure Authentication Server:**

Create `brousla-app-server/.env`:
```bash
OPENAI_API_KEY=your_openai_api_key_here
JWT_SECRET=your-secret-key-change-this-in-production-min-32-chars
PORT=8001
```

4. **Configure Client (optional):**

Create `.env` in project root:
```bash
VITE_API_BASE_URL=http://localhost:8001
```

### Development

Run all services (renderer, Electron, ComfyUI server, Auth server):

```bash
npm run dev
```

Or run services individually:
- `npm run dev:renderer` - Vite dev server
- `npm run dev:electron` - Electron app
- `npm run dev:comfyui` - ComfyUI workflow server (port 8000)
- `npm run dev:auth` - Authentication & AI server (port 8001)

### Build

Build installers for Win/Mac/Linux:

```bash
npm run build
```

## Project Structure

```
brousla-app/
├── electron/              # Electron main process and preload
├── src/                   # React renderer (Vite)
│   ├── components/        # React components
│   ├── pages/            # Page components
│   ├── contexts/         # React contexts (Auth)
│   ├── config/           # Configuration
│   └── utils/            # Utility functions
├── server/               # ComfyUI Workflow Server (port 8000)
│   ├── main.py           # FastAPI app for workflows
│   ├── workflow_executor.py
│   ├── comfyui_client.py
│   └── data/             # Workflow data and preferences
├── brousla-app-server/   # Authentication & AI Server (port 8001)
│   ├── app/
│   │   ├── main.py       # FastAPI app entry point
│   │   ├── routes_auth.py # Authentication routes
│   │   ├── routes_ai.py   # AI chat routes
│   │   ├── auth.py        # JWT & password utilities
│   │   └── llm/           # LLM client implementations
│   └── requirements.txt
├── models/               # Model configs/placeholders
└── assets/               # Static assets
```

## Server Details

### Authentication & AI Server (Port 8001)

- **Location**: `brousla-app-server/`
- **Purpose**: User authentication and AI chat
- **Endpoints**:
  - `POST /auth/register` - User registration
  - `POST /auth/login` - User login (returns JWT)
  - `GET /auth/me` - Get current user info
  - `POST /api/chat` - AI chat (streaming/non-streaming)
- **Documentation**: See `brousla-app-server/README.md`

### ComfyUI Workflow Server (Port 8000)

- **Location**: `server/`
- **Purpose**: ComfyUI workflow execution
- **Endpoints**: Various workflow and ComfyUI management endpoints
- **Data**: Stored in `server/data/`

## Important Notes

- **Authentication is required** - Users must log in or register before accessing the application
- **API Keys**: OpenAI API keys are stored only on the backend (`brousla-app-server/`)
- **Client Security**: The client never directly calls OpenAI/RunPod APIs - all requests go through the backend servers
- **Settings**: ComfyUI settings stored in `server/data/preferences.json`
- **History**: Workflow history stored in `server/data/history.json`

## Development Tips

- Use **F12** or **Ctrl+Shift+I** (Cmd+Option+I on Mac) to toggle DevTools
- Check console for detailed request/response logging
- API errors show full details in the UI for debugging
- Both servers support hot-reload in development mode