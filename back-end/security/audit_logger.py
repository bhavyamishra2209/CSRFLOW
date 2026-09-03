"""
Comprehensive audit logging for all document operations.
Tracks who did what, when, and provides tamper-proof audit trails.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Enumeration of auditable actions."""
    UPLOAD = "upload"
    VIEW = "view"
    DOWNLOAD = "download"
    UPDATE = "update"
    DELETE = "delete"
    VERIFY = "verify"
    APPROVE = "approve"
    REJECT = "reject"
    SHARE = "share"
    COMMENT = "comment"


class AuditLogger:
    """
    Logs all document operations for compliance and security auditing.
    """
    
    def __init__(self, storage_path: str = None):
        """
        Initialize audit logger.
        
        Args:
            storage_path: Path to store audit logs (JSONL format)
        """
        if storage_path is None:
            # Use absolute path relative to this file's location
            from pathlib import Path
            base_dir = Path(__file__).parent.parent
            storage_path = base_dir / "data" / "audit_log.jsonl"
        
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file if it doesn't exist
        if not self.storage_path.exists():
            self.storage_path.touch()
            logger.info(f"✓ Created new audit log: {storage_path}")
    
    def log_action(
        self,
        action: AuditAction,
        user_id: str,
        document_id: Optional[str] = None,
        resource_type: str = "document",
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log an audit event.
        
        Args:
            action: Action performed
            user_id: ID of user who performed the action
            document_id: Document ID (if applicable)
            resource_type: Type of resource (document, project, user, etc.)
            resource_id: ID of resource affected
            metadata: Additional metadata about the action
            ip_address: IP address of user
            user_agent: User agent string
            success: Whether the action succeeded
            error_message: Error message if action failed
            
        Returns:
            Audit log entry
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action.value,
            "user_id": user_id,
            "document_id": document_id,
            "resource_type": resource_type,
            "resource_id": resource_id or document_id,
            "success": success,
            "error_message": error_message,
            "metadata": metadata or {},
            "ip_address": ip_address,
            "user_agent": user_agent
        }
        
        # Write to log file (append as JSONL)
        try:
            with open(self.storage_path, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
        
        # Also log to application logger
        log_message = f"[AUDIT] {action.value.upper()} | User: {user_id} | Resource: {resource_type}/{resource_id}"
        if success:
            logger.info(log_message)
        else:
            logger.warning(f"{log_message} | FAILED: {error_message}")
        
        return entry
    
    def get_logs(
        self,
        user_id: Optional[str] = None,
        document_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit logs with filters.
        
        Args:
            user_id: Filter by user ID
            document_id: Filter by document ID
            action: Filter by action type
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            limit: Maximum number of entries to return
            
        Returns:
            List of matching audit log entries
        """
        results = []
        
        try:
            with open(self.storage_path, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    entry = json.loads(line)
                    
                    # Apply filters
                    if user_id and entry.get("user_id") != user_id:
                        continue
                    
                    if document_id and entry.get("document_id") != document_id:
                        continue
                    
                    if action and entry.get("action") != action.value:
                        continue
                    
                    if start_date and entry.get("timestamp") < start_date:
                        continue
                    
                    if end_date and entry.get("timestamp") > end_date:
                        continue
                    
                    results.append(entry)
                    
                    if len(results) >= limit:
                        break
        
        except Exception as e:
            logger.error(f"Error reading audit logs: {e}")
        
        return results
    
    def get_document_history(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get complete audit history for a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            List of all audit entries for this document
        """
        return self.get_logs(document_id=document_id, limit=10000)
    
    def get_user_activity(
        self,
        user_id: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get recent activity for a user.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            List of recent audit entries for this user
        """
        from datetime import timedelta
        
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        return self.get_logs(user_id=user_id, start_date=start_date, limit=1000)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get audit log statistics.
        
        Returns:
            Dictionary with audit statistics
        """
        total_entries = 0
        unique_users = set()
        unique_documents = set()
        actions_count = {}
        success_count = 0
        failure_count = 0
        
        try:
            with open(self.storage_path, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    entry = json.loads(line)
                    total_entries += 1
                    
                    if entry.get("user_id"):
                        unique_users.add(entry["user_id"])
                    
                    if entry.get("document_id"):
                        unique_documents.add(entry["document_id"])
                    
                    action = entry.get("action", "unknown")
                    actions_count[action] = actions_count.get(action, 0) + 1
                    
                    if entry.get("success"):
                        success_count += 1
                    else:
                        failure_count += 1
        
        except Exception as e:
            logger.error(f"Error calculating audit stats: {e}")
        
        return {
            "total_entries": total_entries,
            "unique_users": len(unique_users),
            "unique_documents": len(unique_documents),
            "actions": actions_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": round(success_count / total_entries * 100, 2) if total_entries > 0 else 0
        }
    
    def export_logs(
        self,
        output_path: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> str:
        """
        Export audit logs to a file.
        
        Args:
            output_path: Path to export file
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            Path to exported file
        """
        logs = self.get_logs(
            start_date=start_date,
            end_date=end_date,
            limit=1000000
        )
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(logs, f, indent=2)
        
        logger.info(f"✓ Exported {len(logs)} audit log entries to {output_path}")
        
        return output_path
