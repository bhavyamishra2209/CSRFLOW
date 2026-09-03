"""
API routes for security and audit features.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from security.hash_chain import DocumentHashChain, calculate_file_hash
from security.integrity_checker import IntegrityChecker
from security.audit_logger import AuditLogger, AuditAction

logger = logging.getLogger(__name__)

# Initialize security components
hash_chain = DocumentHashChain()
integrity_checker = IntegrityChecker()
audit_logger = AuditLogger()


# Request/Response models
class HashChainEntry(BaseModel):
    document_id: str
    document_type: str
    file_hash: str
    user_id: str
    metadata: Optional[Dict[str, Any]] = None


class IntegrityCheckRequest(BaseModel):
    document_id: str
    current_hash: str


class AuditLogQuery(BaseModel):
    user_id: Optional[str] = None
    document_id: Optional[str] = None
    action: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    limit: int = 100


def register_security_routes(app):
    """Register security and audit routes."""
    
    router = APIRouter(prefix="/security", tags=["Security & Audit"])
    
    # ==========================================
    # Hash Chain Endpoints
    # ==========================================
    
    @router.post("/hash-chain/add")
    async def add_to_hash_chain(entry: HashChainEntry, request: Request):
        """
        Add a document to the hash chain.
        Creates an immutable audit trail entry.
        """
        try:
            chain_entry = hash_chain.add_document(
                document_id=entry.document_id,
                document_type=entry.document_type,
                file_hash=entry.file_hash,
                user_id=entry.user_id,
                metadata=entry.metadata
            )
            
            # Log the action
            audit_logger.log_action(
                action=AuditAction.UPLOAD,
                user_id=entry.user_id,
                document_id=entry.document_id,
                metadata={"hash_chain_index": chain_entry["index"]},
                ip_address=request.client.host if request.client else None
            )
            
            return {
                "success": True,
                "message": "Document added to hash chain",
                "chain_entry": chain_entry
            }
        
        except Exception as e:
            logger.error(f"Error adding to hash chain: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/hash-chain/verify")
    async def verify_hash_chain():
        """
        Verify the integrity of the entire hash chain.
        Detects any tampering with the audit trail.
        """
        try:
            result = hash_chain.verify_chain()
            return result
        
        except Exception as e:
            logger.error(f"Error verifying hash chain: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/hash-chain/document/{document_id}")
    async def get_document_chain(document_id: str):
        """
        Get hash chain entries for a specific document.
        Shows complete history of document in the chain.
        """
        try:
            entries = hash_chain.get_document_chain(document_id)
            return {
                "document_id": document_id,
                "total_entries": len(entries),
                "entries": entries
            }
        
        except Exception as e:
            logger.error(f"Error getting document chain: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/hash-chain/stats")
    async def get_chain_stats():
        """
        Get statistics about the hash chain.
        """
        try:
            stats = hash_chain.get_chain_stats()
            return stats
        
        except Exception as e:
            logger.error(f"Error getting chain stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ==========================================
    # Integrity Check Endpoints
    # ==========================================
    
    @router.post("/integrity/verify")
    async def verify_document_integrity(check: IntegrityCheckRequest):
        """
        Verify document integrity by comparing hashes.
        Detects if a document has been tampered with.
        """
        try:
            # Get stored hash from chain
            chain_entries = hash_chain.get_document_chain(check.document_id)
            
            if not chain_entries:
                raise HTTPException(
                    status_code=404,
                    detail="Document not found in hash chain"
                )
            
            stored_hash = chain_entries[-1]["file_hash"]
            
            # Verify integrity
            result = {
                "document_id": check.document_id,
                "valid": check.current_hash == stored_hash,
                "current_hash": check.current_hash,
                "stored_hash": stored_hash,
                "message": "Document integrity verified" if check.current_hash == stored_hash else "⚠️ Document has been tampered with!"
            }
            
            return result
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error verifying integrity: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ==========================================
    # Audit Log Endpoints
    # ==========================================
    
    @router.post("/audit/log")
    async def log_audit_action(
        action: str,
        user_id: str,
        document_id: Optional[str] = None,
        resource_type: str = "document",
        metadata: Optional[Dict[str, Any]] = None,
        request: Request = None
    ):
        """
        Manually log an audit action.
        """
        try:
            # Convert string to AuditAction enum
            try:
                action_enum = AuditAction(action.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid action. Must be one of: {[a.value for a in AuditAction]}"
                )
            
            entry = audit_logger.log_action(
                action=action_enum,
                user_id=user_id,
                document_id=document_id,
                resource_type=resource_type,
                metadata=metadata,
                ip_address=request.client.host if request and request.client else None
            )
            
            return {
                "success": True,
                "message": "Audit action logged",
                "entry": entry
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error logging audit action: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/audit/query")
    async def query_audit_logs(query: AuditLogQuery):
        """
        Query audit logs with filters.
        """
        try:
            logs = audit_logger.get_logs(
                user_id=query.user_id,
                document_id=query.document_id,
                action=AuditAction(query.action) if query.action else None,
                start_date=query.start_date,
                end_date=query.end_date,
                limit=query.limit
            )
            
            return {
                "total": len(logs),
                "logs": logs
            }
        
        except Exception as e:
            logger.error(f"Error querying audit logs: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/audit/document/{document_id}")
    async def get_document_audit_history(document_id: str):
        """
        Get complete audit history for a document.
        """
        try:
            history = audit_logger.get_document_history(document_id)
            return {
                "document_id": document_id,
                "total_actions": len(history),
                "history": history
            }
        
        except Exception as e:
            logger.error(f"Error getting document history: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/audit/user/{user_id}")
    async def get_user_audit_activity(user_id: str, days: int = 30):
        """
        Get recent audit activity for a user.
        """
        try:
            activity = audit_logger.get_user_activity(user_id, days=days)
            return {
                "user_id": user_id,
                "days": days,
                "total_actions": len(activity),
                "activity": activity
            }
        
        except Exception as e:
            logger.error(f"Error getting user activity: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/audit/stats")
    async def get_audit_stats():
        """
        Get audit log statistics.
        """
        try:
            stats = audit_logger.get_stats()
            return stats
        
        except Exception as e:
            logger.error(f"Error getting audit stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Register the router
    app.include_router(router)
    logger.info("✓ Security routes registered")
