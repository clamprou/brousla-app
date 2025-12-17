# Brousla App Server

Backend API server for the Brousla desktop application. Built with FastAPI, this server handles user authentication, rate limiting, and provides an AI gateway to OpenAI (with support for vLLM/RunPod in the future).

## Architecture

- **Desktop Client**: Electron + React (separate project)
- **Backend Server**: Python + FastAPI (this project)

The client communicates with the backend via HTTP. The backend:
- Handles user authentication (JWT)
- Validates requests and enforces rate limits
- Proxies requests to OpenAI API (or vLLM/RunPod)
- Never exposes API keys to the client

## Features

- ✅ User authentication (register, login, JWT)
- ✅ AI chat endpoint with OpenAI integration
- ✅ Streaming and non-streaming chat support
- ✅ Rate limiting per user
- ✅ Abstraction layer for future vLLM/RunPod support
- ✅ Environment-based configuration

## Setup

### Prerequisites

- Python 3.8+
- pip or poetry

### Installation

1. Clone the repository and navigate to the project directory:
```bash
cd api-server
```

2. Create a virtual environment:
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with the following content:
```bash
# Required environment variables
OPENAI_API_KEY=your_openai_api_key_here
JWT_SECRET=your-secret-key-change-this-in-production-min-32-chars

# Optional (with defaults)
OPENAI_MODEL=gpt-5-mini
OPENAI_TEMPERATURE=1.0
AI_PROVIDER=openai
RATE_LIMIT_REQUESTS_PER_MINUTE=60
HOST=0.0.0.0
PORT=8001
```

**Important**: Replace `your_openai_api_key_here` with your actual OpenAI API key, and use a secure random string for `JWT_SECRET` (minimum 32 characters).

## Running Locally

Start the server using uvicorn:

```bash
# Method 1: Direct uvicorn command
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Method 2: Run main.py
python app/main.py

# Method 3: Using the convenience script
python run.py

# Method 4: With custom settings
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

The API will be available at:
- **API**: http://localhost:8001
- **Interactive Docs**: http://localhost:8001/docs
- **Alternative Docs**: http://localhost:8001/redoc

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | Your OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-5-mini` | OpenAI model to use (e.g., `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`, `gpt-4o`, `gpt-4o-mini`, `gpt-5-mini`) |
| `OPENAI_TEMPERATURE` | No | `1.0` | Temperature for AI responses (0.0-2.0). Note: Some models like `gpt-4o-mini` only support 1.0 |
| `JWT_SECRET` | Yes | - | Secret key for JWT signing (min 32 chars) |
| `AI_PROVIDER` | No | `openai` | Provider: `openai` or `openai-compatible` |
| `AI_BASE_URL` | No | - | Base URL for openai-compatible providers |
| `AI_API_KEY` | No | - | API key for openai-compatible providers |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | No | `60` | Max requests per minute per user |
| `HOST` | No | `0.0.0.0` | Server host |
| `PORT` | No | `8001` | Server port |

## API Endpoints

### Authentication

#### Register a new user
```bash
curl -X POST "http://localhost:8001/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

#### Login
```bash
curl -X POST "http://localhost:8001/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Get current user info
```bash
curl -X GET "http://localhost:8001/auth/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE"
```

### AI Chat

#### Non-streaming chat
```bash
curl -X POST "http://localhost:8001/api/chat" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello! How are you?"}
    ],
    "model": "gpt-4-turbo-preview",
    "temperature": 0.7,
    "stream": false
  }'
```

Response:
```json
{
  "content": "Hello! I'm doing well, thank you for asking...",
  "model": "gpt-4-turbo-preview"
}
```

#### Streaming chat
```bash
curl -X POST "http://localhost:8001/api/chat" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Write a short story about AI"}
    ],
    "model": "gpt-4-turbo-preview",
    "temperature": 0.7,
    "stream": true
  }'
```

The response will be in Server-Sent Events (SSE) format:
```
data: {"content": "Once"}

data: {"content": " upon"}

data: {"content": " a"}

data: [DONE]
```

## Example Workflow

1. **Register a user**:
```bash
curl -X POST "http://localhost:8001/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test123"}'
```

2. **Login to get JWT token**:
```bash
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test123"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

3. **Use the token for chat requests**:
```bash
curl -X POST "http://localhost:8001/api/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

## Project Structure

```
api-server/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Environment configuration
│   ├── models.py            # Pydantic models
│   ├── auth.py              # JWT & password utilities
│   ├── routes_auth.py       # Authentication routes
│   ├── routes_ai.py         # AI chat routes
│   ├── rate_limit.py        # Rate limiting logic
│   └── llm/
│       ├── __init__.py
│       ├── base.py          # LLMClient abstract interface
│       ├── openai_client.py # OpenAI implementation
│       └── factory.py       # LLM client factory
├── requirements.txt
├── .env.example             # Example environment variables
└── README.md
```

## Security Notes

- **Never commit `.env` files** - API keys are secrets
- All `/api/*` endpoints require JWT authentication
- Passwords are hashed using bcrypt
- Rate limiting prevents abuse
- OpenAI API keys are never exposed to the client

## Future Enhancements

- [ ] Database integration (replace in-memory user store)
- [ ] Redis-based rate limiting
- [ ] vLLM/RunPod support via `OpenAICompatibleClient`
- [ ] User plans and quotas
- [ ] Request logging and analytics
- [ ] RS256 JWT support with private/public keys

## Development

To run in development mode with auto-reload:

```bash
uvicorn app.main:app --reload
```

## License

[Your License Here]

