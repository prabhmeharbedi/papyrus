# PDF Chat App

A conversational AI application that transforms static PDFs into interactive knowledge sources using RAGFlow integration.

## Project Structure

```
pdf-chat-app/
├── backend/           # FastAPI backend
│   ├── app/          # Application modules
│   ├── venv/         # Python virtual environment
│   ├── main.py       # FastAPI application entry point
│   ├── config.py     # Configuration settings
│   └── requirements.txt
├── frontend/         # React frontend
│   ├── src/          # React source code
│   ├── public/       # Static assets
│   └── package.json
└── .kiro/           # Kiro specs and configuration
    └── specs/
        └── pdf-chat-app/
```

## Getting Started

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate virtual environment (if not already done):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```

5. Update `.env` file with your RAGFlow configuration:
   ```
   RAGFLOW_API_URL=http://localhost:9380
   RAGFLOW_API_KEY=your_ragflow_api_key_here
   ```

6. Start the backend server:
   ```bash
   ./start.sh
   # Or manually: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

The API will be available at:
- Main API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- RAGFlow Test: http://localhost:8000/api/ragflow/test

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

The React app will be available at http://localhost:3000

### Production Build

To create a production build of the frontend:
```bash
cd frontend
npm run build
```

## Current Implementation Status

✅ **Task 1 Complete**: Basic project structure and RAGFlow integration
- FastAPI backend with basic endpoints
- RAGFlow client integration
- React frontend with routing
- Basic system status monitoring

🔄 **Next Steps**: Implement document upload functionality (Task 2)

## API Endpoints

### Health & Status
- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /api/ragflow/test` - Test RAGFlow connection

### Future Endpoints (To be implemented)
- `POST /api/documents/upload` - Upload PDF documents
- `GET /api/documents/` - List documents
- `POST /api/conversations/` - Create conversation
- `POST /api/conversations/{id}/messages` - Send message

## Technology Stack

**Backend:**
- FastAPI (Python web framework)
- SQLAlchemy (Database ORM)
- RAGFlow (RAG engine integration)
- PostgreSQL (Database)
- Redis (Caching)

**Frontend:**
- React 18 with TypeScript
- React Router (Navigation)
- Tailwind CSS (Styling)
- React Query (State management - to be added)

## Development Notes

- Backend runs in a Python virtual environment (`backend/venv/`)
- Frontend uses Create React App with TypeScript
- RAGFlow integration is set up but requires RAGFlow server to be running
- Database models are defined but database setup will be implemented in future tasks