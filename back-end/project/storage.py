"""
CSR Project Storage Layer
Feature #1: CSR Project Lifecycle Management

In-memory dictionary store backed by JSON file persistence.
Provides CRUD and audit trail storage with disk synchronization.
"""

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from project.models import CSRProject, ProjectAuditEntry, ProjectStage

logger = logging.getLogger(__name__)

# Default persistence file path: back-end/project_store.json
DEFAULT_STORE_PATH = Path(__file__).parent.parent / "project_store.json"


class ProjectStore:
    """
    In-memory project and audit store with atomic JSON file persistence.
    """

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or Path(os.getenv("PROJECT_STORE_PATH", str(DEFAULT_STORE_PATH)))
        self._lock = threading.RLock()
        self._projects: Dict[str, Dict[str, Any]] = {}
        self._audit_log: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        """Load data from JSON file if present."""
        with self._lock:
            if not self.file_path.exists():
                return
            try:
                data = json.loads(self.file_path.read_text(encoding="utf-8"))
                self._projects = data.get("projects", {})
                self._audit_log = data.get("audit_log", [])
                logger.info(f"Loaded {len(self._projects)} project(s) and {len(self._audit_log)} audit record(s) from {self.file_path}")
            except Exception as e:
                logger.error(f"Failed to load project store from {self.file_path}: {e}")

    def save(self) -> None:
        """Persist in-memory state to JSON file."""
        with self._lock:
            try:
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                payload = {
                    "projects": self._projects,
                    "audit_log": self._audit_log,
                }
                # Write to temp file first, then atomic replace
                temp_path = self.file_path.with_suffix(".tmp")
                temp_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
                temp_path.replace(self.file_path)
            except Exception as e:
                logger.error(f"Failed to save project store to {self.file_path}: {e}")

    def create(self, project: CSRProject) -> CSRProject:
        """Add a new project to the store."""
        with self._lock:
            self._projects[project.project_id] = project.model_dump()
            self.save()
            return project

    def get(self, project_id: str) -> Optional[CSRProject]:
        """Get project by ID."""
        with self._lock:
            data = self._projects.get(project_id)
            if data is None:
                return None
            return CSRProject.model_validate(data)

    def list_projects(
        self,
        owner_id: Optional[str] = None,
        stage: Optional[ProjectStage] = None,
    ) -> List[CSRProject]:
        """List projects with optional owner and stage filters."""
        with self._lock:
            results = []
            for data in self._projects.values():
                if owner_id and data.get("owner_id") != owner_id:
                    continue
                if stage and data.get("current_stage") != stage.value:
                    continue
                results.append(CSRProject.model_validate(data))
            # Sort by created_at descending
            results.sort(key=lambda p: p.created_at, reverse=True)
            return results

    def update(self, project: CSRProject) -> CSRProject:
        """Update an existing project in the store."""
        with self._lock:
            self._projects[project.project_id] = project.model_dump()
            self.save()
            return project

    def add_audit_entry(self, audit_entry: ProjectAuditEntry) -> None:
        """Append an audit record and persist."""
        with self._lock:
            self._audit_log.append(audit_entry.model_dump())
            self.save()

    def get_audit_trail(self, project_id: str) -> List[ProjectAuditEntry]:
        """Retrieve audit records for a given project."""
        with self._lock:
            entries = [
                ProjectAuditEntry.model_validate(e)
                for e in self._audit_log
                if e.get("project_id") == project_id
            ]
            entries.sort(key=lambda a: a.performed_at)
            return entries

    def get_next_sequence_for_year(self, year: int) -> int:
        """Calculate the next integer sequence for project code generation."""
        with self._lock:
            prefix = f"CSR-{year}-"
            max_seq = 0
            for data in self._projects.values():
                code = data.get("project_code", "")
                if code.startswith(prefix):
                    suffix = code[len(prefix):]
                    try:
                        seq = int(suffix)
                        if seq > max_seq:
                            max_seq = seq
                    except ValueError:
                        pass
            return max_seq + 1

    def clear(self) -> None:
        """Clear all in-memory and persisted data (for test isolation)."""
        with self._lock:
            self._projects.clear()
            self._audit_log.clear()
            if self.file_path.exists():
                try:
                    self.file_path.unlink()
                except Exception:
                    pass


# Singleton instance
project_store = ProjectStore()
