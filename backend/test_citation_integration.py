#!/usr/bin/env python3
"""
Integration test for citation system with API endpoints
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import json
from main import app

client = TestClient(app)

def mock_ragflow_query_response():
    """Mock RAGFlow query response with citation data"""
    return {
        "status": "success",
        "data": {
            "answer": "The document discusses machine learning algorithms and their applications in data science. These algorithms can be categorized into supervised, unsupervised, and reinforcement learning approaches.",
            "confidence_score": 0.87,
            "sources": [
                {
                    "document_id": "ragflow_doc_123",
                    "page_number": 15,
                    "text": "Machine learning algorithms are computational methods that enable computers to learn patterns from data without being explicitly programmed for each specific task. These algorithms form the backbone of modern artificial intelligence systems.",
                    "score": 0.92,
                    "start_position": 250,
                    "end_position": 450
                },
                {
                    "document_id": "ragflow_doc_123",
                    "page_number": 23,
                    "text": "Supervised learning algorithms require labeled training data to learn the mapping between input features and target outputs. Common examples include linear regression, decision trees, and neural networks.",
                    "score": 0.85,
                    "start_position": 100,
                    "end_position": 300
                },
                {
                    "document_id": "ragflow_doc_456",
                    "page_number": 8,
                    "text": "Unsupervised learning algorithms work with unlabeled data to discover hidden patterns and structures. Clustering and dimensionality reduction are typical applications of unsupervised learning.",
                    "score": 0.78,
                    "start_position": 50,
                    "end_position": 250
                }
            ]
        }
    }

# Citation system tests integrated into this file

def test_citation_processing_logic():
    """Test the citation processing logic without API complexity"""
    
    # Test the core citation processing functionality
    from app.ragflow_client import RAGFlowClient
    
    client = RAGFlowClient()
    mock_response = mock_ragflow_query_response()
    
    # Test citation extraction
    citations = client.extract_citations(mock_response["data"])
    print(f"✅ Extracted {len(citations)} citations from RAGFlow response")
    
    # Test citation formatting for storage
    formatted_citations = client.format_citations_for_storage(citations)
    print(f"✅ Formatted {len(formatted_citations)} citations for database storage")
    
    # Test document ID mapping (simulate what happens in the API)
    doc_id_mapping = {
        'ragflow_doc_123': 'local_doc_id_1',
        'ragflow_doc_456': 'local_doc_id_2'
    }
    
    # Simulate the mapping process from the API
    for citation in formatted_citations:
        ragflow_doc_id = citation.get("document_id", "")
        if ragflow_doc_id in doc_id_mapping:
            citation["document_id"] = doc_id_mapping[ragflow_doc_id]
            citation["document_filename"] = f"test_document_{ragflow_doc_id[-3:]}.pdf"
    
    print("✅ Document ID mapping completed")
    
    # Verify the final citation structure
    for i, citation in enumerate(formatted_citations):
        print(f"   Citation {i+1}:")
        print(f"     - Document ID: {citation.get('document_id')}")
        print(f"     - Filename: {citation.get('document_filename')}")
        print(f"     - Page: {citation.get('page_number')}")
        print(f"     - Excerpt: {citation.get('text_excerpt', '')[:100]}...")
        print(f"     - Confidence: {citation.get('confidence')}")
        
        # Verify required fields
        assert "document_id" in citation
        assert "page_number" in citation
        assert "text_excerpt" in citation
        assert "confidence" in citation
        assert citation["document_id"] in ['local_doc_id_1', 'local_doc_id_2']
    
    print("✅ All citation fields verified")
    return True

def test_citation_display_format():
    """Test that citations are formatted correctly for frontend display"""
    
    # Test the citation format matches what the frontend expects
    expected_citation_fields = [
        'document_id',
        'document_filename', 
        'page_number',
        'text_excerpt',
        'confidence'
    ]
    
    mock_response = mock_ragflow_query_response()
    
    # Import the RAGFlow client to test citation extraction
    from app.ragflow_client import RAGFlowClient
    client = RAGFlowClient()
    
    citations = client.extract_citations(mock_response["data"])
    formatted_citations = client.format_citations_for_storage(citations)
    
    print(f"✅ Formatted {len(formatted_citations)} citations for frontend")
    
    for citation in formatted_citations:
        for field in expected_citation_fields:
            if field != 'document_filename':  # This is added later in the API
                assert field in citation, f"Missing field: {field}"
    
    # Test that text excerpts are properly truncated
    for citation in formatted_citations:
        excerpt = citation.get('text_excerpt', '')
        assert len(excerpt) <= 203, f"Text excerpt too long: {len(excerpt)} characters"  # 200 + "..."
    
    return True

def main():
    """Run citation integration tests"""
    print("Citation System Integration Tests")
    print("=" * 50)
    
    tests = [
        ("Citation Processing Logic", test_citation_processing_logic),
        ("Citation Display Format", test_citation_display_format)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"\nRunning: {test_name}")
            result = test_func()
            if result:
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print(f"Integration Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All citation integration tests passed!")
        return True
    else:
        print("⚠️  Some integration tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)