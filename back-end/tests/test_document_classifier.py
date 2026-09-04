"""
Tests for document classifier supporting 20 document types.
"""

import pytest
import numpy as np
from document.document_classifier import DocumentClassifier
from document.schemas.document_types import DOCUMENT_TYPES


class MockEmbeddingModel:
    """Mock embedding model producing deterministic vectors."""
    @property
    def dimension(self) -> int:
        return 384

    def embed(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        # Return constant normalized embeddings
        vecs = np.random.RandomState(42).randn(len(texts), 384)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        return vecs / norms


def test_classifier_initialization():
    mock_model = MockEmbeddingModel()
    classifier = DocumentClassifier(mock_model)

    assert len(classifier.type_names) == 20
    assert "Project Proposal" in classifier.type_names
    assert "Utilization Certificate" in classifier.type_names


def test_classifier_classification():
    mock_model = MockEmbeddingModel()
    classifier = DocumentClassifier(mock_model)

    doc_type, confidence = classifier.classify("Project Title: Clean Water Initiative\nImplementing Agency: River NGO")
    assert isinstance(doc_type, str)
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0001
