import httpx
from typing import Dict, Any, Optional, List
from config import settings
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class Citation(BaseModel):
    """Citation model for RAGFlow responses"""
    document_id: str
    page_number: int
    text_excerpt: str
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    confidence: float = 0.0

class QueryResponse(BaseModel):
    """Structured response from RAGFlow query"""
    answer: str
    citations: List[Citation]
    confidence_score: float
    sources: List[Dict[str, Any]] = []

class RAGFlowClient:
    def __init__(self):
        self.base_url = settings.ragflow_api_url
        self.api_key = settings.ragflow_api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to RAGFlow API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/health",
                    headers=self.headers,
                    timeout=10.0
                )
                if response.status_code == 200:
                    return {"status": "connected", "data": response.json()}
                else:
                    return {"status": "error", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"RAGFlow connection test failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def upload_document(self, file_path: str, document_name: str) -> Dict[str, Any]:
        """Upload a document to RAGFlow for processing"""
        try:
            async with httpx.AsyncClient() as client:
                with open(file_path, "rb") as file:
                    files = {"file": (document_name, file, "application/pdf")}
                    response = await client.post(
                        f"{self.base_url}/api/v1/documents/upload",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        files=files,
                        timeout=30.0
                    )
                
                if response.status_code == 200:
                    return {"status": "success", "data": response.json()}
                else:
                    return {"status": "error", "message": f"Upload failed: HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Document upload failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def query_documents(self, question: str, document_ids: List[str], conversation_context: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Query documents with a question and optional conversation context"""
        try:
            payload = {
                "question": question,
                "document_ids": document_ids,
                "max_results": 5
            }
            
            # Add conversation context if provided
            if conversation_context:
                # Format conversation context for RAGFlow
                # Include last 5 exchanges to maintain context without overwhelming the model
                recent_context = conversation_context[-10:]  # Last 10 messages (5 exchanges)
                
                # Create a context string that helps RAGFlow understand the conversation flow
                context_parts = []
                for msg in recent_context:
                    role_prefix = "Human" if msg["role"] == "user" else "Assistant"
                    context_parts.append(f"{role_prefix}: {msg['content']}")
                
                if context_parts:
                    context_string = "\n".join(context_parts)
                    payload["conversation_context"] = context_string
                    
                    # Also modify the question to include context reference
                    payload["question"] = f"Given our previous conversation:\n{context_string}\n\nNew question: {question}"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/query",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return {"status": "success", "data": response.json()}
                else:
                    return {"status": "error", "message": f"Query failed: HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Document query failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def get_document_status(self, document_id: str) -> Dict[str, Any]:
        """Get processing status of a document"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/documents/{document_id}/status",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return {"status": "success", "data": response.json()}
                else:
                    return {"status": "error", "message": f"Status check failed: HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Document status check failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def delete_document(self, document_id: str) -> Dict[str, Any]:
        """Delete a document from RAGFlow"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/api/v1/documents/{document_id}",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return {"status": "success", "data": response.json()}
                elif response.status_code == 404:
                    # Document not found in RAGFlow, consider it already deleted
                    return {"status": "success", "message": "Document not found in RAGFlow (already deleted)"}
                else:
                    return {"status": "error", "message": f"Delete failed: HTTP {response.status_code}"}
        except Exception as e:
            logger.error(f"Document deletion failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def extract_citations(self, ragflow_response: Dict[str, Any]) -> List[Citation]:
        """Extract and format citations from RAGFlow response"""
        citations = []
        
        try:
            # RAGFlow typically returns sources/chunks with citation information
            sources = ragflow_response.get("sources", [])
            chunks = ragflow_response.get("chunks", [])
            references = ragflow_response.get("references", [])
            
            # Process sources if available
            for source in sources:
                citation = Citation(
                    document_id=source.get("document_id", ""),
                    page_number=source.get("page_number", 1),
                    text_excerpt=source.get("text", "")[:200] + "..." if len(source.get("text", "")) > 200 else source.get("text", ""),
                    start_position=source.get("start_position"),
                    end_position=source.get("end_position"),
                    confidence=source.get("score", 0.0)
                )
                citations.append(citation)
            
            # Process chunks if sources not available
            if not citations and chunks:
                for chunk in chunks:
                    citation = Citation(
                        document_id=chunk.get("doc_id", ""),
                        page_number=chunk.get("page_num", 1),
                        text_excerpt=chunk.get("content", "")[:200] + "..." if len(chunk.get("content", "")) > 200 else chunk.get("content", ""),
                        confidence=chunk.get("similarity_score", 0.0)
                    )
                    citations.append(citation)
            
            # Process references if other formats not available
            if not citations and references:
                for ref in references:
                    citation = Citation(
                        document_id=ref.get("document_id", ""),
                        page_number=ref.get("page", 1),
                        text_excerpt=ref.get("excerpt", ""),
                        confidence=ref.get("relevance", 0.0)
                    )
                    citations.append(citation)
            
            # Remove duplicates based on document_id and page_number
            unique_citations = []
            seen = set()
            for citation in citations:
                key = (citation.document_id, citation.page_number)
                if key not in seen:
                    seen.add(key)
                    unique_citations.append(citation)
            
            return unique_citations[:5]  # Limit to top 5 citations
            
        except Exception as e:
            logger.error(f"Error extracting citations: {str(e)}")
            return []
    
    def format_citations_for_storage(self, citations: List[Citation]) -> List[Dict[str, Any]]:
        """Format citations for database storage"""
        return [
            {
                "document_id": citation.document_id,
                "page_number": citation.page_number,
                "text_excerpt": citation.text_excerpt,
                "start_position": citation.start_position,
                "end_position": citation.end_position,
                "confidence": citation.confidence
            }
            for citation in citations
        ]

# Global RAGFlow client instance
ragflow_client = RAGFlowClient()