"""
SHA256 Hash Chain implementation for document integrity and tamper detection.
Creates an immutable audit trail where each document links to the previous one.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class DocumentHashChain:
    """
    Implements a blockchain-like hash chain for document integrity.
    Each document's hash includes the previous document's hash, creating
    an immutable chain that detects any tampering.
    """
    
    def __init__(self, storage_path: str = None):
        """
        Initialize the hash chain.
        
        Args:
            storage_path: Path to store the hash chain data
        """
        if storage_path is None:
            # Use absolute path relative to this file's location
            base_dir = Path(__file__).parent.parent
            storage_path = base_dir / "data" / "hash_chain.json"
        
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.chain: List[Dict[str, Any]] = []
        self._load_chain()
    
    def _load_chain(self):
        """Load existing chain from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    self.chain = json.load(f)
                logger.info(f"✓ Loaded hash chain with {len(self.chain)} entries")
            except Exception as e:
                logger.error(f"Failed to load hash chain: {e}")
                self.chain = []
        else:
            logger.info("No existing hash chain found, starting fresh")
            self.chain = []
    
    def _save_chain(self):
        """Save chain to storage."""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.chain, f, indent=2)
            logger.info(f"✓ Hash chain saved ({len(self.chain)} entries)")
        except Exception as e:
            logger.error(f"Failed to save hash chain: {e}")
    
    def _calculate_hash(self, data: Dict[str, Any]) -> str:
        """
        Calculate SHA256 hash of data.
        
        Args:
            data: Dictionary to hash
            
        Returns:
            Hex string of the hash
        """
        # Sort keys for consistent hashing
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def add_document(
        self,
        document_id: str,
        document_type: str,
        file_hash: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a document to the hash chain.
        
        Args:
            document_id: Unique document identifier
            document_type: Type of document (e.g., "project_proposal", "budget")
            file_hash: SHA256 hash of the actual file content
            user_id: ID of user who uploaded the document
            metadata: Additional metadata to include in the chain
            
        Returns:
            Chain entry with hash information
        """
        # Get previous hash (or genesis hash)
        previous_hash = self.chain[-1]["hash"] if self.chain else "0" * 64
        
        # Create chain entry
        entry = {
            "index": len(self.chain),
            "timestamp": datetime.utcnow().isoformat(),
            "document_id": document_id,
            "document_type": document_type,
            "file_hash": file_hash,
            "user_id": user_id,
            "previous_hash": previous_hash,
            "metadata": metadata or {}
        }
        
        # Calculate hash of this entry
        entry["hash"] = self._calculate_hash({
            "index": entry["index"],
            "timestamp": entry["timestamp"],
            "document_id": entry["document_id"],
            "document_type": entry["document_type"],
            "file_hash": entry["file_hash"],
            "user_id": entry["user_id"],
            "previous_hash": entry["previous_hash"],
            "metadata": entry["metadata"]
        })
        
        # Add to chain
        self.chain.append(entry)
        self._save_chain()
        
        logger.info(f"✓ Document {document_id} added to hash chain (index: {entry['index']})")
        
        return entry
    
    def verify_chain(self) -> Dict[str, Any]:
        """
        Verify the integrity of the entire hash chain.
        
        Returns:
            Dictionary with verification results
        """
        # Always reload from file to get latest data
        self._load_chain()
        
        if not self.chain:
            return {
                "valid": True,
                "message": "Empty chain (valid)",
                "total_entries": 0
            }
        
        for i, entry in enumerate(self.chain):
            # Check if index is correct
            if entry["index"] != i:
                return {
                    "valid": False,
                    "message": f"Invalid index at position {i}",
                    "corrupted_entry": entry
                }
            
            # Check if previous hash matches
            if i > 0:
                if entry["previous_hash"] != self.chain[i - 1]["hash"]:
                    return {
                        "valid": False,
                        "message": f"Broken chain at index {i}",
                        "corrupted_entry": entry
                    }
            else:
                # First entry should have genesis hash
                if entry["previous_hash"] != "0" * 64:
                    return {
                        "valid": False,
                        "message": "Invalid genesis hash",
                        "corrupted_entry": entry
                    }
            
            # Recalculate hash and verify
            calculated_hash = self._calculate_hash({
                "index": entry["index"],
                "timestamp": entry["timestamp"],
                "document_id": entry["document_id"],
                "document_type": entry["document_type"],
                "file_hash": entry["file_hash"],
                "user_id": entry["user_id"],
                "previous_hash": entry["previous_hash"],
                "metadata": entry["metadata"]
            })
            
            if calculated_hash != entry["hash"]:
                return {
                    "valid": False,
                    "message": f"Hash mismatch at index {i}",
                    "corrupted_entry": entry,
                    "expected_hash": calculated_hash,
                    "actual_hash": entry["hash"]
                }
        
        return {
            "valid": True,
            "message": "Hash chain is valid and unbroken",
            "total_entries": len(self.chain)
        }
    
    def get_document_chain(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get all chain entries for a specific document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            List of chain entries for this document
        """
        # Always reload from file to get latest data
        self._load_chain()
        return [entry for entry in self.chain if entry["document_id"] == document_id]
    
    def get_audit_trail(
        self,
        document_id: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get filtered audit trail.
        
        Args:
            document_id: Filter by document ID
            user_id: Filter by user ID
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            
        Returns:
            Filtered list of chain entries
        """
        results = self.chain.copy()
        
        if document_id:
            results = [e for e in results if e["document_id"] == document_id]
        
        if user_id:
            results = [e for e in results if e["user_id"] == user_id]
        
        if start_date:
            results = [e for e in results if e["timestamp"] >= start_date]
        
        if end_date:
            results = [e for e in results if e["timestamp"] <= end_date]
        
        return results
    
    def get_chain_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the hash chain.
        
        Returns:
            Dictionary with chain statistics
        """
        # Always reload from file to get latest data
        self._load_chain()
        
        if not self.chain:
            return {
                "total_entries": 0,
                "unique_documents": 0,
                "unique_users": 0,
                "first_entry": None,
                "last_entry": None
            }
        
        return {
            "total_entries": len(self.chain),
            "unique_documents": len(set(e["document_id"] for e in self.chain)),
            "unique_users": len(set(e["user_id"] for e in self.chain)),
            "first_entry": self.chain[0]["timestamp"],
            "last_entry": self.chain[-1]["timestamp"],
            "chain_valid": self.verify_chain()["valid"]
        }


def calculate_file_hash(file_content: bytes) -> str:
    """
    Calculate SHA256 hash of file content.
    
    Args:
        file_content: Raw file bytes
        
    Returns:
        Hex string of the hash
    """
    return hashlib.sha256(file_content).hexdigest()
