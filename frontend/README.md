# DocuMind AI Frontend

React + Vite + Tailwind frontend for the DocuMind AI document intelligence system.

## Features

- ✅ **Authentication** - Supabase JWT-based auth with login/magic link
- ✅ **System Status** - Real-time backend health monitoring with cold-start detection
- ✅ **Document Upload** - Drag-and-drop file upload with real-time processing
- ✅ **Document Management** - List, view, and verify documents
- ✅ **AI Query Interface** - Chat with documents with evidence citations
- ✅ **Knowledge Graph** - Interactive visualization of entities and relationships
- ✅ **Analytics Dashboard** - Charts and statistics with Recharts
- ✅ **Schema Management** - Admin-only schema configuration (live field editing)

## Prerequisites

- Node.js 18+ and npm
- Supabase account and project
- Backend API running (https://documind-ai-backend.onrender.com or local)

## Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# API Configuration
VITE_API_BASE_URL=https://documind-ai-backend.onrender.com

# Supabase Configuration (get from https://app.supabase.com)
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here

# Optional: Admin user IDs (comma-separated)
VITE_ADMIN_USER_IDS=uuid1,uuid2
```

### 3. Run Development Server

```bash
npm run dev
```

The app will open at `http://localhost:3000`

### 4. Build for Production

```bash
npm run build
```

Built files will be in the `dist` directory.

## Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── client.js           # API client with all endpoints
│   ├── components/
│   │   └── Layout.jsx          # Main layout with nav and status indicator
│   ├── context/
│   │   └── AuthContext.jsx     # Supabase auth context
│   ├── pages/
│   │   ├── Login.jsx           # Login page
│   │   ├── Dashboard.jsx       # Dashboard with quick actions
│   │   ├── Upload.jsx          # Document upload with drag-and-drop
│   │   ├── Documents.jsx       # Document list with filters
│   │   ├── DocumentDetail.jsx  # Document detail with verification
│   │   ├── AskAI.jsx           # AI chat interface
│   │   ├── KnowledgeGraph.jsx  # Graph visualization
│   │   ├── Analytics.jsx       # Analytics dashboard with charts
│   │   └── SchemaManagement.jsx # Schema editor (admin only)
│   ├── App.jsx                 # Main app with routing
│   ├── main.jsx                # Entry point
│   └── index.css               # Tailwind styles
├── index.html
├── vite.config.js
├── tailwind.config.js
├── package.json
└── README.md
```

## API Endpoints Used

| Endpoint | Method | Usage |
|----------|--------|-------|
| `/health` | GET | System status check |
| `/upload` | POST | Upload document |
| `/documents/list` | GET | List user documents |
| `/documents/{id}` | GET | Get document details |
| `/documents/{id}/verify` | POST | Verify document |
| `/query` | POST | AI query with evidence |
| `/kg/visualize` | GET | Knowledge graph data |
| `/users/me/stats` | GET | User analytics |
| `/schemas/{type}` | GET | Get schema |
| `/schemas/{type}` | PUT | Update schema |

## Features Detail

### Authentication
- Email/password login via Supabase
- Magic link support (passwordless)
- Session management with JWT
- Automatic token refresh
- 401 handling with redirect

### System Status
- Real-time health checks every 30 seconds
- Cold start detection (60 second warmup)
- Visual indicators: Online (green), Warming (yellow), Offline (red)

### Document Upload
- Drag-and-drop interface
- File type validation (PDF, JPG, PNG, DOCX, TXT)
- File size limit (50MB)
- Real-time processing status
- Shows: classification, extracted fields, knowledge graph info

### Document Verification
- One-click verification against records database
- Status badges: Verified (green), Revoked (red), Expired (amber), Not Found (grey)
- Informative tooltips about production readiness

### AI Query
- Chat interface with message history
- Evidence citations for every answer
- Source document references with relevance scores
- Knowledge graph enhancement toggle
- Grounded responses (refuses to answer without evidence)

### Knowledge Graph
- Interactive force-directed graph visualization
- Entity types: Person, Location, Date, Organization, Document
- Typed relationships: BORN_ON, LIVES_AT, IDENTIFIED_BY
- Click nodes for details
- Color-coded legend

### Analytics
- Key metrics cards
- Bar chart: Documents by type
- Pie charts: Verification status, type distribution
- Summary statistics table
- Recharts integration

### Schema Management (Admin Only)
- Select document type
- Add/edit/remove fields
- Configure field type, description, required flag
- Live JSON preview
- Save to backend

## Styling

- **Tailwind CSS** for utility-first styling
- **Lucide React** for icons
- Government/official visual style:
  - Muted blues and greys
  - Clear typography
  - Professional, not playful
  - High contrast for accessibility

## Error Handling

- User-friendly error toasts (not raw dumps)
- Specific handling for:
  - 401 Unauthorized → redirect to login
  - Cold start delays → loading skeleton
  - 422 Validation errors → inline messages
  - Empty states → helpful CTAs

## Development Tips

1. **Hot Module Replacement**: Vite provides instant HMR
2. **API Base URL**: Change in `.env` to point to local backend
3. **Supabase Local**: Use Supabase CLI for local auth testing
4. **Mock Data**: Add mock responses in API client for offline dev

## Deployment

### Vercel

```bash
vercel --prod
```

### Netlify

```bash
netlify deploy --prod
```

### Environment Variables

Set these in your deployment platform:
- `VITE_API_BASE_URL`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_ADMIN_USER_IDS` (optional)

## Troubleshooting

### "Session expired" on every request
- Check that Supabase keys are correct
- Verify JWT token is being stored in localStorage
- Check backend CORS configuration

### Knowledge graph not loading
- Upload a document first
- Check `/kg/visualize` endpoint response
- Verify Neo4j is enabled in backend

### Charts not displaying
- Verify `recharts` is installed
- Check that stats API returns proper data structure
- Inspect browser console for errors

### Admin features not visible
- Confirm user ID is in `VITE_ADMIN_USER_IDS`
- Check JWT token contains correct user ID
- Verify `isAdmin()` function logic

## License

MIT License - See LICENSE file for details
