"""
Main FastAPI application entry point — CSRFlow
Run with: uvicorn main:app --reload
"""

import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ─── App ────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="CSRFlow API",
    description="CSR Project Lifecycle Management — document intelligence + RBAC workflows",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

_raw_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://localhost:8081",
)
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# ─── RAG Engine (optional — existing DocuMind AI features) ──────────────────

rag_engine = None

try:
    logger.info("Initializing RAG engine…")
    from embedding.model import create_embedding_model
    embedder = create_embedding_model()

    from storage.vector_db import FaissVectorDatabase
    vector_db = FaissVectorDatabase(dimension=embedder.dimension)

    try:
        from llm.ollama_model import OllamaLLM
        llm = OllamaLLM(model="phi")
        if not llm.available:
            raise Exception("Ollama not available")
        logger.info("✓ Ollama LLM")
    except Exception:
        from llm.serverless_model import HuggingFaceInferenceAPI
        llm = HuggingFaceInferenceAPI(
            model_name="mistralai/Mistral-7B-Instruct-v0.2",
            api_key=os.getenv("HUGGINGFACE_API_KEY"),
        )
        logger.info("✓ HuggingFace LLM")

    from rag.engine import RAGEngine
    rag_engine = RAGEngine(
        embedder=embedder, vector_db=vector_db, llm=llm, top_k=5, search_type="hybrid"
    )
    logger.info("✓ RAG engine ready")

except Exception as e:
    logger.warning(f"RAG engine not available ({e}) — running without document intelligence")

# ─── Register RAG-dependent routes ──────────────────────────────────────────

if rag_engine:
    try:
        from routes.routes import RAGAPIRouter
        RAGAPIRouter(app, rag_engine)
        logger.info("✓ Document / RAG routes")
    except Exception as e:
        logger.warning(f"RAG routes failed: {e}")

    try:
        from routes.graph_routes import register_graph_routes, neo4j_startup_check
        register_graph_routes(app, rag_engine)
        neo4j_startup_check()
        logger.info("✓ Graph routes")
    except Exception as e:
        logger.warning(f"Graph routes failed: {e}")

    try:
        from routes.schema_routes import register_schema_routes
        register_schema_routes(app)
        logger.info("✓ Schema routes")
    except Exception as e:
        logger.warning(f"Schema routes failed: {e}")

    try:
        from routes.analytics_routes import register_analytics_routes
        register_analytics_routes(app)
        logger.info("✓ Analytics routes")
    except Exception as e:
        logger.warning(f"Analytics routes failed: {e}")

# ─── CSR routes — always registered (no RAG dependency) ─────────────────────

try:
    from routes.user_routes import register_user_routes
    register_user_routes(app)
    logger.info("✓ User profile routes")
except Exception as e:
    logger.warning(f"User routes failed: {e}")

try:
    from routes.csr_routes import register_csr_routes
    register_csr_routes(app)
    logger.info("✓ CSR project routes")
except Exception as e:
    logger.warning(f"CSR routes failed: {e}")

# ─── Security routes (SHA256 hash chain & audit logs) ───────────────────────

try:
    from routes.security_routes import register_security_routes
    register_security_routes(app)
    logger.info("✓ Security routes (hash chain & audit)")
except Exception as e:
    logger.warning(f"Security routes failed: {e}")

# ─── Always-available endpoints ──────────────────────────────────────────────

@app.get("/", tags=["System"])
async def root():
    return {
        "name":       "CSRFlow API",
        "version":    "2.0.0",
        "status":     "operational" if rag_engine else "limited",
        "rag_engine": "ready" if rag_engine else "not initialized",
        "docs":       "/docs",
    }


@app.get("/health", tags=["System"])
async def health_check():
    doc_count = 0
    if rag_engine:
        try:
            if hasattr(rag_engine, "vector_db") and hasattr(rag_engine.vector_db, "count"):
                doc_count = rag_engine.vector_db.count()
        except Exception:
            pass
    return {
        "status":         "healthy" if rag_engine else "degraded",
        "version":        "2.0.0",
        "rag_engine":     "initialized" if rag_engine else "not initialized",
        "document_count": doc_count,
    }


@app.get("/status", tags=["System"])
async def system_status():
    return {
        "api":    "running",
        "version": "2.0.0",
        "components": {
            "rag_engine": "ready" if rag_engine else "not initialized",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
