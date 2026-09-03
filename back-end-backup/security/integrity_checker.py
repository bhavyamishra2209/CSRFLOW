"""
Document integrity verification using SHA256 hashing.
Verifies that documents haven't been tampered with after upload.
"""

import hashlib
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class IntegrityChecker:
    """
    Verifies document integrity by comparing stored hashes with current file hashes.
    """
    
    def __init__(self):
        """Initialize integrity checker."""
        pass
    
    def calculate_hash(self, file_content: bytes) -> str:
        """
        Calculate SHA256 hash of file content.
        
        Args:
            file_content: Raw file bytes
            
        Returns:
            Hex string of the hash
        """
        return hashlib.sha256(file_content).hexdigest()
    
    def calculate_hash_from_path(self, file_path: str) -> str:
        """
        Calculate SHA256 hash from file path.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hex string of the hash
        """
        try:
            with open(file_path, 'rb') as f:
                return self.calculate_hash(f.read())
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            raise
    
    def verify_integrity(
        self,
        file_content: bytes,
        stored_hash: str
    ) -> Dict[str, Any]:
        """
        Verify file integrity by comparing current hash with stored hash.
        
        Args:
            file_content: Current file content
            stored_hash: Previously stored hash
            
        Returns:
            Dictionary with verification results
        """
        current_hash = self.calculate_hash(file_content)
        
        is_valid = current_hash == stored_hash
        
        result = {
            "valid": is_valid,
            "current_hash": current_hash,
            "stored_hash": stored_hash,
            "message": "Document integrity verified" if is_valid else "Document has been tampered with!"
        }
        
        if not is_valid:
            logger.warning(f"⚠️  Integrity check failed! Current: {current_hash}, Stored: {stored_hash}")
        else:
            logger.info(f"✓ Integrity check passed: {current_hash}")
        
        return result
    
    def verify_from_path(
        self,
        file_path: str,
        stored_hash: str
    ) -> Dict[str, Any]:
        """
        Verify file integrity from file path.
        
        Args:
            file_path: Path to file
            stored_hash: Previously stored hash
            
        Returns:
            Dictionary with verification results
        """
        try:
            with open(file_path, 'rb') as f:
                return self.verify_integrity(f.read(), stored_hash)
        except Exception as e:
            logger.error(f"Error verifying integrity for {file_path}: {e}")
            return {
                "valid": False,
                "error": str(e),
                "message": f"Error reading file: {e}"
            }
    
    def generate_checksum_file(
        self,
        file_path: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate a checksum file for a document.
        
        Args:
            file_path: Path to file
            output_path: Path to save checksum file (defaults to {file_path}.sha256)
            
        Returns:
            Path to checksum file
        """
        file_hash = self.calculate_hash_from_path(file_path)
        
        if not output_path:
            output_path = f"{file_path}.sha256"
        
        with open(output_path, 'w') as f:
            f.write(f"{file_hash}  {Path(file_path).name}\n")
        
        logger.info(f"✓ Checksum file created: {output_path}")
        
        return output_path
    
    def verify_checksum_file(
        self,
        file_path: str,
        checksum_path: str
    ) -> Dict[str, Any]:
        """
        Verify a file against its checksum file.
        
        Args:
            file_path: Path to file
            checksum_path: Path to checksum file
            
        Returns:
            Dictionary with verification results
        """
        try:
            # Read stored hash from checksum file
            with open(checksum_path, 'r') as f:
                line = f.readline().strip()
                stored_hash = line.split()[0]
            
            # Verify
            return self.verify_from_path(file_path, stored_hash)
            
        except Exception as e:
            logger.error(f"Error verifying checksum file: {e}")
            return {
                "valid": False,
                "error": str(e),
                "message": f"Error reading checksum file: {e}"
            }
    
    def batch_verify(
        self,
        file_hashes: Dict[str, str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Verify multiple files at once.
        
        Args:
            file_hashes: Dictionary mapping file paths to stored hashes
            
        Returns:
            Dictionary mapping file paths to verification results
        """
        results = {}
        
        for file_path, stored_hash in file_hashes.items():
            results[file_path] = self.verify_from_path(file_path, stored_hash)
        
        return results
