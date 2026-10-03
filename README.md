# CSRFlow

**AI-Powered CSR Project Lifecycle & Compliance Platform**

CSRFlow manages the complete Corporate Social Responsibility (CSR) project lifecycle — from proposal to closure. It centralizes documents, approvals, budgets, milestones, and compliance checks, while using AI to extract information, answer questions, and flag potential inconsistencies.

---

## 🚀 Key Features

- **AI Document Intelligence** — Extracts key information from CSR documents using OCR and AI
- **RAG-Based Document Q&A** — Ask questions about uploaded project documents and get context-based answers
- **Hybrid Search** — Combines semantic/vector search with keyword search for accurate retrieval
- **CSR Lifecycle Management** — Tracks projects from proposal to closure
- **Budget & Milestone Tracking** — Monitor project spending, milestones, and progress
- **Compliance Checks** — Helps identify missing or potentially non-compliant information
- **Inconsistency Detection** — Flags potential contradictions across project documents and reports
- **Tamper-Evident Audit Trail** — Uses SHA-256 hash chaining to detect unauthorized changes
- **Role-Based Access Control (RBAC)** — Restricts actions based on user roles
- **Project Isolation** — Prevents unauthorized access to other projects' data
- **Secure Authentication** — JWT authentication with refresh-token/session support
- **Knowledge Graph**  — Neo4j-based visualization of relationships between project entities

---

## 👥 User Roles

### CSR Head
- Creates and manages CSR projects
- Assigns Project Managers and Approvers
- Manages project information and budgets
- Views project progress and statistics
- Manages users
- Views audit history

### Project Manager
- Manages assigned projects
- Uploads and organizes documents
- Tracks milestones and expenses
- Uploads progress reports
- Submits projects for review
- Uses AI document Q&A

### Approver / Auditor
- Independently reviews projects
- Checks documents and compliance
- Reviews flagged inconsistencies
- Approves or rejects project stages
- Verifies audit history

> **Rule:** An Approver cannot approve or reject a project they created.

---

## 🔄 Project Workflow

```
Proposal → Evaluation/Compliance → Approval → Funding → Implementation → Monitoring → Completion → Closure
```

**Basic flow:** CSR Head creates project → Project Manager executes → Approver reviews and approves → Monitoring → Completion → CSR Head closes the project.

---

## 🏗️ Architecture

```
Frontend (React + Vite)
        ↓
FastAPI Backend
        ↓
Supabase PostgreSQL + Authentication
        ↓
AI/RAG Pipeline
        ↓
OCR → Chunking → Embeddings → FAISS → Hybrid Search → Ollama/LLM
```

> Neo4j can optionally be used for knowledge-graph visualization.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React.js, Vite, JavaScript, Tailwind CSS, React Router, Axios |
| **Backend** | Python, FastAPI, JWT |
| **Database & Auth** | Supabase, PostgreSQL, Supabase Auth, Row Level Security |
| **AI/RAG** | Ollama, Sentence Transformers, FAISS, OCR, Embeddings, RAG |
| **Knowledge Graph** | Neo4j |
| **Security** | AES-256, SHA-256 Hash Chaining, RBAC, JWT + Refresh Tokens |

---

## ⚙️ Installation

### Backend

```bash
cd back-end
python -m venv venv
```

Activate the virtual environment (Windows):

```bash
.\venv\Scripts\Activate.ps1
```

Install dependencies and run:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend runs at: `http://localhost:8000`

### Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:3000`

> Keep both the frontend and backend running during development.

---

## 🔐 Environment Variables

**Backend `.env`**

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_JWT_SECRET=your_jwt_secret
```

**Frontend `.env`**

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

> ⚠️ Never commit `.env` files or secret keys to GitHub.

---

## 🗄️ Supabase Setup

1. Create a Supabase project
2. Open the SQL Editor
3. Run the provided database migration
4. Create users via Supabase Authentication
5. Assign one of the following roles to each user:
   - `csr_head`
   - `project_manager`
   - `approver`

Supabase provides authentication, PostgreSQL, and Row Level Security for protecting project data.

---

## 🤖 AI Pipeline

```
Document Upload
      ↓
OCR / Text Extraction
      ↓
Document Chunking
      ↓
Embedding Generation
      ↓
FAISS Vector Search
      ↓
Keyword + Semantic Search
      ↓
Relevant Context
      ↓
Ollama / LLM
      ↓
AI Answer / Analysis
```

The system can also compare information across documents and flag potential inconsistencies.

---

## 🔒 Security

CSRFlow uses multiple security layers:

- JWT Authentication
- Refresh Tokens / Session Renewal
- Role-Based Access Control
- Supabase Row Level Security
- Project-Level Authorization
- Project Isolation
- SHA-256 Hash Chaining
- Audit Logging

---

## 📊 Audit Trail

Important project actions are recorded using a hash chain:

```
Record 1 → SHA-256 → Record 2 → SHA-256 → Record 3 → ...
```

If an earlier record is modified, the hash chain reveals that the audit history has been altered.

---

## 🧪 Testing

**Backend:**

```bash
pytest
```

**Frontend build:**

```bash
npm run build
```

---

## 🚀 Deployment

| Component | Options |
|---|---|
| Frontend | Vercel / Netlify |
| Backend | Render / Railway / any FastAPI-compatible cloud platform |
| Database & Auth | Supabase |

---

## 🔮 Future Enhancements

- Automated CSR report generation
- Advanced inconsistency analysis
- Email and notification system
- Advanced analytics dashboard
- Mobile application
- Advanced knowledge-graph insights
- Automated compliance recommendations

---

## 🎯 Vision

CSRFlow transforms fragmented CSR paperwork into a traceable digital lifecycle — one where AI understands documents, helps detect potential inconsistencies, tracks funds and milestones, and creates a tamper-evident trail from proposal to closure.

---

## 👩‍💻 Team

Built as a hackathon project focused on improving transparency, efficiency, compliance, and accountability in CSR project management.
