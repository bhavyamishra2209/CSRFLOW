CSRFlow

AI-Powered CSR Project Lifecycle & Compliance Platform

CSRFlow helps organizations manage Corporate Social Responsibility projects from proposal to closure by combining AI-powered document intelligence, structured workflows, compliance checks, milestone tracking, and a tamper-evident audit trail.

🚀 Key Features
📄 AI Document Intelligence — OCR, classification, and structured data extraction from PDF, DOCX, TXT, and images.
🔎 Hybrid AI Search — FAISS semantic search + BM25 keyword search with grounded RAG.
🔄 Project Lifecycle Management — Draft → Submitted → Review → Approved → Implementation → Monitoring → Completed → Closed.
⚖️ CSR Compliance — Section 135 and Schedule VII checks, compliance flagging, and duplicate/double-funding detection.
👥 Role-Based Access Control — CSR Head, Project Manager, and Approver/Auditor.
📊 Project Tracking — Budgets, milestones, progress, and overdue milestone detection.
🔐 Security & Audit — JWT authentication, RLS, project isolation, and SHA-256 hash-chain audit trail.
🧠 Knowledge Graph — Optional Neo4j-based entity and relationship mapping.
🏗️ Architecture
React Frontend
      ↓
FastAPI Backend
      ↓
 ┌───────────────┬─────────────────┐
 │ Authentication │ CSR Workflow   │
 │ JWT + RBAC     │ + Compliance   │
 └───────┬───────┴────────┬────────┘
         ↓                 ↓
   Document Engine     Project Data
    OCR + AI             Supabase
         ↓
   FAISS + BM25
         ↓
   Grounded RAG
         ↓
   Ollama / HF
👥 User Roles
Role	Responsibility
CSR Head	Creates projects, assigns members, manages budgets and users
Project Manager	Executes projects, manages documents and milestones
Approver / Auditor	Reviews projects, checks compliance, approves/rejects stages
Workflow
Draft
  ↓
Submitted
  ↓
Under Review
  ↓
Approved
  ↓
In Progress
  ↓
Monitoring
  ↓
Completed
  ↓
Closed

The backend enforces valid stage transitions and prevents self-approval.

🛠️ Tech Stack
Layer	Technology
Frontend	React, Vite, Tailwind CSS
Backend	FastAPI, Python, Uvicorn
Authentication	Supabase Auth + JWT
Database	Supabase PostgreSQL
Vector Search	FAISS
Keyword Search	BM25
Embeddings	all-MiniLM-L6-v2
LLM	Ollama / HuggingFace
OCR	Tesseract + EasyOCR
File Storage	Firebase
Knowledge Graph	Neo4j AuraDB
Deployment	Render + Vercel/Netlify
⚙️ Setup
Prerequisites
Python 3.12+
Node.js 18+
npm
Git
Supabase account
Ollama (optional)
1. Clone Repository
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd CSRFlow
2. Backend
cd back-end
python -m venv venv

Windows

venv\Scripts\activate

macOS/Linux

source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

Backend: http://localhost:8000
API Docs: http://localhost:8000/docs

3. Supabase

Create a Supabase project and run the provided SQL migration in:

Supabase Dashboard → SQL Editor

The migration creates the required user, project, and workflow tables with Row Level Security.

Create test users for:

CSR Head
Project Manager
Approver
4. Frontend

Open a new terminal:

cd frontend
npm install
npm run dev

Frontend: http://localhost:3000

Keep the backend running while using the frontend.

🔐 Environment Variables
Backend .env
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=

HUGGINGFACE_API_KEY=

FIREBASE_CREDENTIALS_PATH=
FIREBASE_STORAGE_BUCKET=

NEO4J_ENABLED=false
NEO4J_URI=
NEO4J_USERNAME=
NEO4J_PASSWORD=

CORS_ORIGINS=http://localhost:3000
Frontend .env
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_API_BASE_URL=http://localhost:8000

Never commit .env files or secret keys to GitHub.

🧠 AI Pipeline
Upload Document
      ↓
OCR / Text Extraction
      ↓
Classification & Field Extraction
      ↓
Chunking + Embeddings
      ↓
FAISS + BM25 Search
      ↓
Relevant Context
      ↓
Grounded RAG
      ↓
AI Response + Evidence
🔒 Security

CSRFlow uses multiple security layers:

Supabase Authentication
JWT-based sessions
Role-Based Access Control
Row Level Security
Project-level authorization
Self-approval prevention
SHA-256 hash-chain audit trail
Secure environment variables
🧪 Testing
cd back-end
pytest tests/
🚀 Deployment

Backend: Render
Frontend: Vercel / Netlify

Configure the required environment variables on the deployment platform before deploying.

🔮 Future Enhancements
Automated CSR impact report generation
Advanced budget anomaly detection
Real-time notifications
Expanded compliance rules
Advanced knowledge-graph analytics
Multi-organization support
