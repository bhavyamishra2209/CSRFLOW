"""
Knowledge Graph — FastAPI endpoints (Phase 3)

Reuses existing KG logic without reimplementing it:
  - KnowledgeGraphExtractor.process_document_chunks()  → entity extraction
  - Neo4jKnowledgeGraphStore.save_knowledge_graph()    → persist to Neo4j
  - Neo4jKnowledgeGraphStore.get_neighbors()           → hop traversal
  - kg_manager (singleton)                             → in-memory KG

Endpoints
─────────
POST /documents/{id}/graph/sync   — extract + write to Neo4j for one doc
GET  /documents/{id}/graph        — nodes/edges within 2 hops of this doc
GET  /users/me/graph              — combined graph across all user's docs

All three require a valid Supabase JWT (Phase 2 auth dependency).

Neo4j is optional — if disabled / unreachable the endpoints degrade
gracefully (return the in-memory KG data instead) so the rest of the app
is never affected.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from auth.auth import UserInfo, get_current_user
from routes.routes import _DOC_REGISTRY  # in-memory registry from Phase 1

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Neo4j availability flag — set once at import time
# ---------------------------------------------------------------------------
NEO4J_ENABLED: bool = os.getenv("NEO4J_ENABLED", "false").lower() in (
    "true", "1", "t", "yes"
)

router = APIRouter(tags=["Knowledge Graph"])

# ---------------------------------------------------------------------------
# Lazy Neo4j store — created once on first use
# ---------------------------------------------------------------------------
_neo4j_store = None
_neo4j_available: bool = False   # updated by startup_check()


def _get_neo4j_store():
    """Return a connected Neo4jKnowledgeGraphStore or None."""
    global _neo4j_store, _neo4j_available
    if not NEO4J_ENABLED:
        return None
    if _neo4j_store is not None and _neo4j_available:
        return _neo4j_store
    try:
        from knowledge_graph.neo4j_store import Neo4jKnowledgeGraphStore
        store = Neo4jKnowledgeGraphStore()   # reads env vars automatically
        if store.connect():
            _neo4j_store = store
            _neo4j_available = True
            logger.info("Neo4j store connected")
        else:
            _neo4j_available = False
            logger.warning("Neo4j store connect() returned False")
    except Exception as e:
        _neo4j_available = False
        logger.warning(f"Neo4j store unavailable: {e}")
    return _neo4j_store if _neo4j_available else None


# ---------------------------------------------------------------------------
# Startup check (called from main.py lifespan)
# ---------------------------------------------------------------------------

def neo4j_startup_check() -> None:
    """
    Attempt a trivial Neo4j query at startup.
    Logs a clear WARNING if unreachable — never raises, never crashes the app.
    """
    if not NEO4J_ENABLED:
        logger.info("Neo4j disabled (NEO4J_ENABLED=false) — KG will use in-memory store only")
        return

    try:
        store = _get_neo4j_store()
        if store is None:
            logger.warning(
                "⚠️  Neo4j is ENABLED but not reachable. "
                "Check NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD in .env. "
                "The app will continue — graph sync endpoints will return in-memory data."
            )
        else:
            logger.info("✓ Neo4j connection verified at startup")
    except Exception as e:
        logger.warning(f"⚠️  Neo4j startup check failed: {e} — continuing without Neo4j")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _chunks_for_doc(doc_id: str, rag_engine) -> tuple[List[str], List[Dict]]:
    """Return (chunks, chunk_metadata) for a given document_id from FAISS."""
    chunks: List[str] = []
    meta:   List[Dict] = []
    vdb = getattr(rag_engine, "vector_db", None)
    if vdb and hasattr(vdb, "documents"):
        for c in vdb.documents.values():
            if c.metadata.get("document_id") == doc_id:
                chunks.append(c.text)
                meta.append(c.metadata)
    return chunks, meta


def _kg_to_flat_json(
    kg,
    doc_id: Optional[str] = None,
    max_hops: int = 2,
    store=None,
) -> Dict[str, Any]:
    """
    Convert in-memory KG or Neo4j neighbours to flat nodes/edges JSON.

    Shape: { "nodes": [{"id","label","type"}], "edges": [{"source","target","type"}] }
    """
    nodes: List[Dict] = []
    edges: List[Dict] = []
    seen_nodes = set()
    seen_edges = set()

    # If Neo4j available and doc_id given, use it for 2-hop neighbourhood
    if store is not None and doc_id is not None:
        try:
            # Find entities whose metadata references this document
            entities = kg.entities if hasattr(kg, "entities") else {}
            doc_entity_ids = [
                eid for eid, ent in entities.items()
                if ent.get("metadata", {}).get("document_id") == doc_id
                   or ent.get("metadata", {}).get("source_document") == doc_id
            ]
            for eid in doc_entity_ids:
                neighbours = store.get_neighbors(eid)
                for ent, rel in neighbours:
                    for n in (ent,):
                        nid = getattr(n, "id", str(n))
                        if nid not in seen_nodes:
                            seen_nodes.add(nid)
                            nodes.append({
                                "id":    nid,
                                "label": getattr(n, "name", nid),
                                "type":  getattr(n, "type", "Unknown"),
                            })
                    eid_str = getattr(rel, "id", f"{rel.source}-{rel.target}")
                    if eid_str not in seen_edges:
                        seen_edges.add(eid_str)
                        edges.append({
                            "source": getattr(rel, "source", ""),
                            "target": getattr(rel, "target", ""),
                            "type":   getattr(rel, "type",   ""),
                        })
            if nodes or edges:
                return {"nodes": nodes, "edges": edges, "source": "neo4j"}
        except Exception as e:
            logger.warning(f"Neo4j graph fetch failed, falling back to in-memory: {e}")

    # Fallback: walk the in-memory KG
    try:
        entities  = kg.entities  if hasattr(kg, "entities")  else {}
        relations = kg.relations if hasattr(kg, "relations") else {}

        # Filter to doc-specific entities if doc_id given
        if doc_id:
            relevant_ids = {
                eid for eid, ent in entities.items()
                if ent.get("metadata", {}).get("document_id") == doc_id
                   or ent.get("metadata", {}).get("source_document") == doc_id
                   or ent.get("name", "") == doc_id   # document node itself
            }
            # Include entities reachable within max_hops
            frontier = set(relevant_ids)
            for _ in range(max_hops):
                next_frontier = set()
                for rel in relations.values():
                    src, tgt = rel.get("source"), rel.get("target")
                    if src in frontier and tgt not in relevant_ids:
                        next_frontier.add(tgt)
                    if tgt in frontier and src not in relevant_ids:
                        next_frontier.add(src)
                relevant_ids |= next_frontier
                frontier = next_frontier
        else:
            relevant_ids = set(entities.keys())

        for eid in relevant_ids:
            if eid not in entities:
                continue
            ent = entities[eid]
            seen_nodes.add(eid)
            nodes.append({
                "id":    eid,
                "label": ent.get("name", eid),
                "type":  ent.get("type", "Unknown"),
            })

        for rel in relations.values():
            src, tgt = rel.get("source"), rel.get("target")
            if src in relevant_ids and tgt in relevant_ids:
                eid_str = f"{src}-{tgt}-{rel.get('type','')}"
                if eid_str not in seen_edges:
                    seen_edges.add(eid_str)
                    edges.append({
                        "source": src,
                        "target": tgt,
                        "type":   rel.get("type", ""),
                    })
    except Exception as e:
        logger.error(f"In-memory KG graph fetch failed: {e}")

    return {"nodes": nodes, "edges": edges, "source": "in_memory"}


# ---------------------------------------------------------------------------
# Route factory — called from main.py after rag_engine is ready
# ---------------------------------------------------------------------------

def register_graph_routes(app, rag_engine) -> None:
    """
    Register all three graph endpoints on the FastAPI app.
    Called from main.py after the RAG engine is initialised.
    """

    # ── POST /documents/{id}/graph/sync ────────────────────────────────────

    @router.post(
        "/documents/{document_id}/graph/sync",
        summary="Extract entities + sync this document to Neo4j KG",
    )
    async def sync_document_graph(
        document_id: str,
        user: UserInfo = Depends(get_current_user),
    ):
        """
        1. Looks up the document in the in-memory registry (owner-scoped).
        2. Retrieves its chunks from FAISS.
        3. Runs KnowledgeGraphExtractor.process_document_chunks() on them
           (reusing the existing extractor, no duplication).
        4. Merges result into kg_manager (in-memory KG).
        5. If Neo4j is enabled, calls Neo4jKnowledgeGraphStore.save_knowledge_graph().

        This is also called automatically from /upload so the UI never
        needs to call it manually — it is exposed for manual re-sync or
        debugging.
        """
        # Ownership check
        rec = _DOC_REGISTRY.get(document_id)
        if rec is None or rec.get("owner_id") != user.user_id:
            raise HTTPException(
                status_code=404,
                detail={"error": "Document not found", "document_id": document_id},
            )

        chunks, chunk_meta = _chunks_for_doc(document_id, rag_engine)
        if not chunks:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "no_chunks",
                    "message": "Document has no indexed chunks. Re-upload the document.",
                },
            )

        # --- Entity extraction (reuse existing extractor) ---
        try:
            from knowledge_graph.kg_manager import kg_manager
            kg_manager.process_extracted_fields(
                document_id=document_id,
                filename=rec.get("filename", document_id),
                document_type=rec.get("document_type", "Other"),
                extracted_fields=rec.get("extracted_fields", []),
                chunks=chunks,
            )
            kg_manager.process_document(chunks, chunk_meta)
            stats = kg_manager.get_stats()
        except Exception as e:
            logger.error(f"KG extraction failed for {document_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail={"error": "extraction_failed", "message": str(e)},
            )

        # --- Persist to Neo4j (optional) ---
        neo4j_synced = False
        neo4j_message = "Neo4j disabled or unavailable — data stored in-memory only"
        store = _get_neo4j_store()
        if store is not None:
            try:
                from knowledge_graph.model import KnowledgeGraph, Entity, Relation
                simple_kg = KnowledgeGraph()
                ekg = kg_manager.kg
                for eid, ent in ekg.entities.items():
                    e = Entity(
                        name=ent.get("name", ""),
                        type=ent.get("type", "Other"),
                        metadata=ent.get("metadata", {}),
                        id=eid,
                    )
                    simple_kg.entities[eid] = e
                    simple_kg.graph.add_node(eid, **{
                        "name": e.name, "type": e.type,
                    })
                for rid, rel in ekg.relations.items():
                    r = Relation(
                        source=rel.get("source", ""),
                        target=rel.get("target", ""),
                        type=rel.get("type", ""),
                        weight=rel.get("confidence", 1.0),
                        id=rid,
                    )
                    simple_kg.relations[rid] = r
                    if r.source in simple_kg.entities and r.target in simple_kg.entities:
                        simple_kg.graph.add_edge(r.source, r.target,
                                                 type=r.type, weight=r.weight)
                neo4j_synced = store.save_knowledge_graph(simple_kg)
                neo4j_message = "Synced to Neo4j" if neo4j_synced else "Neo4j save failed"
            except Exception as e:
                logger.warning(f"Neo4j sync failed (non-fatal): {e}")
                neo4j_message = f"Neo4j sync error: {e}"

        return {
            "status":        "success",
            "document_id":   document_id,
            "entity_count":  stats.get("entity_count", 0),
            "relation_count": stats.get("relation_count", 0),
            "entity_types":  stats.get("entity_types", {}),
            "neo4j_synced":  neo4j_synced,
            "neo4j_message": neo4j_message,
        }

    # ── GET /documents/{id}/graph ───────────────────────────────────────────

    @router.get(
        "/documents/{document_id}/graph",
        summary="Get nodes/edges within 2 hops of this document",
    )
    async def get_document_graph(
        document_id: str,
        max_hops: int = 2,
        user: UserInfo = Depends(get_current_user),
    ):
        """
        Returns the knowledge graph subgraph for a single document.

        Shape:
        ```json
        {
          "nodes": [{"id": "...", "label": "Ravi Kumar Sharma", "type": "Person"}],
          "edges": [{"source": "...", "target": "...", "type": "BORN_ON"}],
          "source": "in_memory | neo4j"
        }
        ```
        """
        rec = _DOC_REGISTRY.get(document_id)
        if rec is None or rec.get("owner_id") != user.user_id:
            raise HTTPException(
                status_code=404,
                detail={"error": "Document not found", "document_id": document_id},
            )

        try:
            from knowledge_graph.kg_manager import kg_manager
            # Reload from disk if in-memory KG is empty
            if not kg_manager.kg.entities:
                kg_manager._load()
            store = _get_neo4j_store()
            result = _kg_to_flat_json(
                kg_manager.kg,
                doc_id=document_id,
                max_hops=max_hops,
                store=store,
            )
            result["document_id"] = document_id
            result["node_count"]  = len(result["nodes"])
            result["edge_count"]  = len(result["edges"])
            return result
        except Exception as e:
            logger.error(f"get_document_graph failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={"error": "graph_fetch_failed", "message": str(e)},
            )

    # ── GET /users/me/graph ─────────────────────────────────────────────────

    @router.get(
        "/users/me/graph",
        summary="Combined KG graph across all of the current user's documents",
    )
    async def get_user_graph(
        max_nodes: int = 150,
        user: UserInfo = Depends(get_current_user),
    ):
        """
        Returns a merged knowledge graph for every document owned by the
        current user, capped at max_nodes most-connected nodes.

        Shape: same as GET /documents/{id}/graph.
        """
        try:
            from knowledge_graph.kg_manager import kg_manager

            if not kg_manager.kg.entities:
                kg_manager._load()

            # Collect all document_ids belonging to this user
            user_doc_ids = {
                did for did, rec in _DOC_REGISTRY.items()
                if rec.get("owner_id") == user.user_id
            }

            # Also check FAISS chunk metadata for older uploads
            vdb = getattr(rag_engine, "vector_db", None)
            if vdb and hasattr(vdb, "documents"):
                for c in vdb.documents.values():
                    if c.metadata.get("owner_id") == user.user_id:
                        did = c.metadata.get("document_id")
                        if did:
                            user_doc_ids.add(did)

            if not user_doc_ids:
                return {
                    "nodes": [], "edges": [],
                    "source":      "in_memory",
                    "node_count":  0,
                    "edge_count":  0,
                    "document_count": 0,
                }

            ekg = kg_manager.kg

            # Collect all entity IDs that belong to any of the user's docs
            relevant_ids = set()
            for eid, ent in ekg.entities.items():
                meta = ent.get("metadata", {})
                if (
                    meta.get("document_id") in user_doc_ids
                    or meta.get("source_document") in user_doc_ids
                ):
                    relevant_ids.add(eid)

            # Also include entities reachable within 1 hop
            for rel in ekg.relations.values():
                src, tgt = rel.get("source"), rel.get("target")
                if src in relevant_ids:
                    relevant_ids.add(tgt)
                if tgt in relevant_ids:
                    relevant_ids.add(src)

            # Cap by connectivity
            import networkx as nx
            graph = ekg.graph
            if len(relevant_ids) > max_nodes:
                degree = {n: graph.degree(n) for n in relevant_ids if graph.has_node(n)}
                relevant_ids = {
                    nid for nid, _ in
                    sorted(degree.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
                }

            nodes = [
                {
                    "id":    eid,
                    "label": ekg.entities[eid].get("name", eid),
                    "type":  ekg.entities[eid].get("type", "Unknown"),
                }
                for eid in relevant_ids
                if eid in ekg.entities
            ]

            seen_edges: set = set()
            edges = []
            for rel in ekg.relations.values():
                src, tgt = rel.get("source"), rel.get("target")
                if src in relevant_ids and tgt in relevant_ids:
                    key = f"{src}|{tgt}|{rel.get('type','')}"
                    if key not in seen_edges:
                        seen_edges.add(key)
                        edges.append({
                            "source": src,
                            "target": tgt,
                            "type":   rel.get("type", ""),
                        })

            return {
                "nodes":          nodes,
                "edges":          edges,
                "source":         "in_memory",
                "node_count":     len(nodes),
                "edge_count":     len(edges),
                "document_count": len(user_doc_ids),
            }
        except Exception as e:
            logger.error(f"get_user_graph failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={"error": "graph_fetch_failed", "message": str(e)},
            )

    # Register the router with the FastAPI app
    app.include_router(router)
    logger.info("Graph routes registered: /documents/{id}/graph/sync, "
                "/documents/{id}/graph, /users/me/graph")
