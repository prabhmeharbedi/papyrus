from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import os
import uuid
import shutil
from pathlib import Path
from typing import List, Dict, Any
import asyncio
import time
from dotenv import load_dotenv
from app.ragflow_client import ragflow_client
from app.models import Document, Conversation, Message
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from config import settings
from pydantic import BaseModel
from logging_config import setup_logging, get_logger
from error_handlers import (
    http_exception_handler,
    starlette_exception_handler,
    validation_exception_handler,
    general_exception_handler,
    api_error_handler,
    APIError,
    DocumentProcessingError,
    RAGFlowError,
    DatabaseError
)
import redis

# Load environment variables
load_dotenv()

# Setup logging
setup_logging(settings.log_level, settings.log_file)
logger = get_logger(__name__)

app = FastAPI(
    title="PDF Chat App API",
    description="Backend API for PDF Chat Application with RAGFlow integration",
    version="1.0.0"
)

# Add error handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, starlette_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Configure CORS with settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis setup
try:
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    redis_client.ping()  # Test connection
    logger.info("Redis connection established")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}")
    redis_client = None

# Create uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# File validation constants using settings
MAX_FILE_SIZE = settings.max_file_size
ALLOWED_EXTENSIONS = {".pdf"}

# Pydantic models for request/response
class ChatRequest(BaseModel):
    question: str
    document_ids: List[str]
    conversation_id: str = None

class CreateConversationRequest(BaseModel):
    document_ids: List[str]
    title: str = None

def sanitize_user_input(text: str) -> str:
    """Sanitize user input to prevent XSS and other issues"""
    if not text:
        return ""
    
    # Strip whitespace
    text = text.strip()
    
    # Remove null bytes and control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # Limit length to prevent abuse
    max_length = 10000  # 10KB limit for messages
    if len(text) > max_length:
        text = text[:max_length]
    
    return text

def validate_chat_request(request: ChatRequest) -> None:
    """Validate chat request parameters"""
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )
    
    # Sanitize the question
    request.question = sanitize_user_input(request.question)
    
    if len(request.question) < 3:
        raise HTTPException(
            status_code=400,
            detail="Question must be at least 3 characters long."
        )
    
    if not request.document_ids:
        raise HTTPException(
            status_code=400,
            detail="At least one document ID must be provided."
        )
    
    # Validate document ID format (should be UUIDs)
    for doc_id in request.document_ids:
        try:
            uuid.UUID(doc_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid document ID format: {doc_id}"
            )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def validate_pdf_file(file: UploadFile) -> None:
    """Validate uploaded PDF file with comprehensive checks"""
    if not file or not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file provided or filename is missing."
        )
    
    # Sanitize filename - remove potentially dangerous characters
    filename = file.filename.strip()
    if not filename:
        raise HTTPException(
            status_code=400,
            detail="Filename cannot be empty."
        )
    
    # Check filename length
    if len(filename) > 255:
        raise HTTPException(
            status_code=400,
            detail="Filename is too long. Maximum length is 255 characters."
        )
    
    # Check for invalid characters in filename
    import re
    invalid_chars = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
    if invalid_chars.search(filename):
        raise HTTPException(
            status_code=400,
            detail="Filename contains invalid characters. Please remove special characters."
        )
    
    # Check file extension
    file_extension = Path(filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format '{file_extension}'. Only PDF files are allowed."
        )
    
    # Check MIME type
    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type '{file.content_type}'. Expected 'application/pdf'."
        )
    
    # Check file size (this is approximate since we haven't read the full file yet)
    if hasattr(file, 'size') and file.size is not None:
        if file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large ({file.size // (1024*1024)}MB). Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB."
            )
        
        # Check minimum file size
        if file.size < 1024:  # 1KB minimum
            raise HTTPException(
                status_code=400,
                detail="File appears to be empty or corrupted."
            )

@app.get("/")
async def root():
    return {"message": "PDF Chat App API is running"}

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy", 
        "service": "pdf-chat-api",
        "timestamp": time.time(),
        "environment": settings.environment
    }

@app.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with dependency status"""
    health_status = {
        "status": "healthy",
        "service": "pdf-chat-api",
        "timestamp": time.time(),
        "environment": settings.environment,
        "checks": {}
    }
    
    # Database check
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {"status": "healthy", "message": "Connected"}
    except Exception as e:
        health_status["checks"]["database"] = {"status": "unhealthy", "message": str(e)}
        health_status["status"] = "unhealthy"
    
    # Redis check
    if redis_client:
        try:
            redis_client.ping()
            health_status["checks"]["redis"] = {"status": "healthy", "message": "Connected"}
        except Exception as e:
            health_status["checks"]["redis"] = {"status": "unhealthy", "message": str(e)}
            health_status["status"] = "degraded"
    else:
        health_status["checks"]["redis"] = {"status": "unavailable", "message": "Not configured"}
    
    # RAGFlow check
    try:
        ragflow_result = await ragflow_client.test_connection()
        if ragflow_result.get("status") == "success":
            health_status["checks"]["ragflow"] = {"status": "healthy", "message": "Connected"}
        else:
            health_status["checks"]["ragflow"] = {"status": "unhealthy", "message": ragflow_result.get("message", "Connection failed")}
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["checks"]["ragflow"] = {"status": "unhealthy", "message": str(e)}
        health_status["status"] = "unhealthy"
    
    # File system check
    try:
        test_file = UPLOAD_DIR / ".health_check"
        test_file.write_text("test")
        test_file.unlink()
        health_status["checks"]["filesystem"] = {"status": "healthy", "message": "Read/write OK"}
    except Exception as e:
        health_status["checks"]["filesystem"] = {"status": "unhealthy", "message": str(e)}
        health_status["status"] = "unhealthy"
    
    return health_status

@app.get("/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    """Basic application metrics"""
    if not settings.enable_metrics:
        raise HTTPException(status_code=404, detail="Metrics not enabled")
    
    try:
        # Document counts
        total_documents = db.query(Document).count()
        processing_documents = db.query(Document).filter(Document.processing_status == "processing").count()
        completed_documents = db.query(Document).filter(Document.processing_status == "completed").count()
        failed_documents = db.query(Document).filter(Document.processing_status == "failed").count()
        
        # Conversation counts
        total_conversations = db.query(Conversation).count()
        total_messages = db.query(Message).count()
        
        # File system usage
        upload_dir_size = sum(f.stat().st_size for f in UPLOAD_DIR.rglob('*') if f.is_file())
        
        return {
            "timestamp": time.time(),
            "documents": {
                "total": total_documents,
                "processing": processing_documents,
                "completed": completed_documents,
                "failed": failed_documents
            },
            "conversations": {
                "total": total_conversations,
                "total_messages": total_messages
            },
            "storage": {
                "upload_dir_size_bytes": upload_dir_size,
                "upload_dir_size_mb": round(upload_dir_size / (1024 * 1024), 2)
            }
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@app.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Kubernetes readiness probe endpoint"""
    try:
        # Check database connection
        db.execute(text("SELECT 1"))
        
        # Check RAGFlow connection
        ragflow_result = await ragflow_client.test_connection()
        if ragflow_result.get("status") != "success":
            raise HTTPException(status_code=503, detail="RAGFlow not ready")
        
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service not ready")

@app.get("/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint"""
    return {"status": "alive", "timestamp": time.time()}

@app.get("/api/ragflow/test")
async def test_ragflow_connection():
    """Test RAGFlow connection"""
    result = await ragflow_client.test_connection()
    return result

@app.post("/api/documents/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a PDF document for processing"""
    try:
        # Validate the uploaded file
        validate_pdf_file(file)
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix.lower()
        unique_filename = f"{file_id}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename
        
        # Save file to disk
        with open(file_path, "wb") as buffer:
            content = await file.read()
            # Additional size check after reading full content
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB."
                )
            buffer.write(content)
        
        logger.info(f"File saved: {file_path}")
        
        # Create document record in database
        # For now, using a dummy user_id - this will be replaced with actual auth later
        dummy_user_id = str(uuid.uuid4())
        
        document = Document(
            user_id=dummy_user_id,
            filename=unique_filename,
            original_filename=file.filename,
            file_size=len(content),
            processing_status="pending"
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        logger.info(f"Document record created: {document.id}")
        
        # Upload to RAGFlow for processing
        ragflow_result = await ragflow_client.upload_document(
            str(file_path), 
            file.filename
        )
        
        if ragflow_result["status"] == "success":
            # Update document with RAGFlow document ID
            ragflow_doc_id = ragflow_result["data"].get("document_id")
            document.ragflow_document_id = ragflow_doc_id
            document.processing_status = "processing"
            db.commit()
            
            logger.info(f"Document uploaded to RAGFlow: {ragflow_doc_id}")
            
            # Start background polling for this document
            background_tasks.add_task(poll_document_status, str(document.id))
            
            return {
                "status": "success",
                "message": "Document uploaded successfully",
                "document_id": str(document.id),
                "filename": file.filename,
                "processing_status": "processing"
            }
        else:
            # Update status to failed if RAGFlow upload fails
            document.processing_status = "failed"
            db.commit()
            
            logger.error(f"RAGFlow upload failed: {ragflow_result['message']}")
            
            return {
                "status": "error",
                "message": f"Document upload failed: {ragflow_result['message']}",
                "document_id": str(document.id)
            }
            
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/documents/")
async def list_documents(db: Session = Depends(get_db)):
    """List all uploaded documents"""
    try:
        documents = db.query(Document).all()
        return {
            "status": "success",
            "documents": [
                {
                    "id": str(doc.id),
                    "filename": doc.original_filename,
                    "file_size": doc.file_size,
                    "upload_date": doc.upload_date.isoformat(),
                    "processing_status": doc.processing_status,
                    "page_count": doc.page_count
                }
                for doc in documents
            ]
        }
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.get("/api/documents/{document_id}")
async def get_document(document_id: str, db: Session = Depends(get_db)):
    """Get document details by ID"""
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "status": "success",
            "document": {
                "id": str(document.id),
                "filename": document.original_filename,
                "file_size": document.file_size,
                "upload_date": document.upload_date.isoformat(),
                "processing_status": document.processing_status,
                "page_count": document.page_count,
                "ragflow_document_id": document.ragflow_document_id
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")

@app.get("/api/documents/{document_id}/file")
async def serve_document_file(document_id: str, db: Session = Depends(get_db)):
    """Serve the PDF file for a document"""
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        file_path = UPLOAD_DIR / document.filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        return FileResponse(
            path=str(file_path),
            media_type="application/pdf",
            filename=document.original_filename
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving document file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to serve file: {str(e)}")

async def poll_document_status(document_id: str):
    """Background task to poll document processing status"""
    max_attempts = 60  # Poll for up to 10 minutes (60 * 10 seconds)
    attempt = 0
    
    while attempt < max_attempts:
        try:
            db = SessionLocal()
            document = db.query(Document).filter(Document.id == document_id).first()
            
            if not document or document.processing_status != "processing":
                db.close()
                break
                
            if document.ragflow_document_id:
                ragflow_status = await ragflow_client.get_document_status(document.ragflow_document_id)
                
                if ragflow_status["status"] == "success":
                    status_data = ragflow_status["data"]
                    
                    if status_data.get("status") == "completed":
                        document.processing_status = "completed"
                        document.page_count = status_data.get("page_count")
                        document.doc_metadata = status_data.get("metadata", {})
                        db.commit()
                        logger.info(f"Document {document_id} processing completed")
                        db.close()
                        break
                    elif status_data.get("status") == "failed":
                        document.processing_status = "failed"
                        db.commit()
                        logger.error(f"Document {document_id} processing failed")
                        db.close()
                        break
            
            db.close()
            attempt += 1
            await asyncio.sleep(10)  # Wait 10 seconds before next poll
            
        except Exception as e:
            logger.error(f"Error polling document status for {document_id}: {str(e)}")
            try:
                db.close()
            except:
                pass
            break

@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: str, db: Session = Depends(get_db)):
    """Delete a document and its associated file"""
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check if document is used in any conversations
        conversations_using_doc = db.query(Conversation).filter(
            Conversation.document_ids.contains([document.id])
        ).count()
        
        if conversations_using_doc > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete document. It is used in {conversations_using_doc} conversation(s). Delete those conversations first."
            )
        
        # Delete from RAGFlow if it exists there
        if document.ragflow_document_id:
            try:
                ragflow_result = await ragflow_client.delete_document(document.ragflow_document_id)
                if ragflow_result["status"] == "success":
                    logger.info(f"Successfully deleted document {document.ragflow_document_id} from RAGFlow")
                else:
                    logger.warning(f"Failed to delete document from RAGFlow: {ragflow_result['message']}")
            except Exception as e:
                logger.warning(f"Failed to delete document from RAGFlow: {str(e)}")
        
        # Delete physical file
        file_path = UPLOAD_DIR / document.filename
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted file: {file_path}")
        
        # Delete from database
        db.delete(document)
        db.commit()
        
        logger.info(f"Document deleted: {document_id}")
        
        return {
            "status": "success",
            "message": "Document deleted successfully",
            "document_id": document_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@app.get("/api/documents/{document_id}/status")
async def get_document_status(document_id: str, db: Session = Depends(get_db)):
    """Get document processing status"""
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # If document is still processing, check RAGFlow status
        if document.processing_status == "processing" and document.ragflow_document_id:
            ragflow_status = await ragflow_client.get_document_status(document.ragflow_document_id)
            
            if ragflow_status["status"] == "success":
                status_data = ragflow_status["data"]
                # Update local status based on RAGFlow response
                if status_data.get("status") == "completed":
                    document.processing_status = "completed"
                    document.page_count = status_data.get("page_count")
                    document.doc_metadata = status_data.get("metadata", {})
                    db.commit()
                elif status_data.get("status") == "failed":
                    document.processing_status = "failed"
                    db.commit()
        
        return {
            "status": "success",
            "document_id": str(document.id),
            "processing_status": document.processing_status,
            "page_count": document.page_count,
            "metadata": document.doc_metadata
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking document status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to check status: {str(e)}")

@app.post("/api/documents/poll-status")
async def poll_processing_documents(db: Session = Depends(get_db)):
    """Poll status for all processing documents"""
    try:
        processing_docs = db.query(Document).filter(
            Document.processing_status == "processing"
        ).all()
        
        updated_count = 0
        for document in processing_docs:
            if document.ragflow_document_id:
                ragflow_status = await ragflow_client.get_document_status(document.ragflow_document_id)
                
                if ragflow_status["status"] == "success":
                    status_data = ragflow_status["data"]
                    
                    if status_data.get("status") == "completed":
                        document.processing_status = "completed"
                        document.page_count = status_data.get("page_count")
                        document.doc_metadata = status_data.get("metadata", {})
                        updated_count += 1
                    elif status_data.get("status") == "failed":
                        document.processing_status = "failed"
                        updated_count += 1
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"Polled {len(processing_docs)} documents, updated {updated_count}",
            "processing_count": len(processing_docs) - updated_count
        }
    except Exception as e:
        logger.error(f"Error polling document statuses: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to poll statuses: {str(e)}")

# Chat endpoints
@app.get("/api/conversations/")
async def list_conversations(db: Session = Depends(get_db)):
    """List all conversations for the user"""
    try:
        # For now, get all conversations since we don't have user auth yet
        conversations = db.query(Conversation).order_by(Conversation.updated_at.desc()).all()
        
        conversation_list = []
        for conv in conversations:
            # Count messages for this conversation
            message_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
            
            conversation_list.append({
                "id": str(conv.id),
                "title": conv.title,
                "document_ids": [str(doc_id) for doc_id in conv.document_ids],
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "message_count": message_count
            })
        
        return {
            "status": "success",
            "conversations": conversation_list
        }
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {str(e)}")

@app.post("/api/conversations/")
async def create_conversation(
    request: CreateConversationRequest,
    db: Session = Depends(get_db)
):
    """Create a new conversation"""
    try:
        # Validate that all document IDs exist and are completed
        documents = db.query(Document).filter(
            Document.id.in_(request.document_ids),
            Document.processing_status == "completed"
        ).all()
        
        if len(documents) != len(request.document_ids):
            raise HTTPException(
                status_code=400,
                detail="One or more documents not found or not yet processed"
            )
        
        # Create conversation with dummy user_id for now
        dummy_user_id = str(uuid.uuid4())
        
        conversation = Conversation(
            user_id=dummy_user_id,
            document_ids=request.document_ids,
            title=request.title or f"Chat with {len(request.document_ids)} document(s)"
        )
        
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        logger.info(f"Created conversation: {conversation.id}")
        
        return {
            "status": "success",
            "conversation": {
                "id": str(conversation.id),
                "title": conversation.title,
                "document_ids": [str(doc_id) for doc_id in conversation.document_ids],
                "created_at": conversation.created_at.isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Get conversation details with message history"""
    try:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get messages for this conversation
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).all()
        
        return {
            "status": "success",
            "conversation": {
                "id": str(conversation.id),
                "title": conversation.title,
                "document_ids": [str(doc_id) for doc_id in conversation.document_ids],
                "created_at": conversation.created_at.isoformat(),
                "messages": [
                    {
                        "id": str(msg.id),
                        "role": msg.role,
                        "content": msg.content,
                        "citations": msg.citations,
                        "confidence_score": msg.confidence_score,
                        "created_at": msg.created_at.isoformat()
                    }
                    for msg in messages
                ]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")

@app.post("/api/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """Send a message in a conversation and get AI response"""
    try:
        # Validate the chat request
        validate_chat_request(request)
        
        # Verify conversation exists
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Use document IDs from conversation if not provided in request
        document_ids = request.document_ids if request.document_ids else conversation.document_ids
        
        # Validate documents exist and are processed
        documents = db.query(Document).filter(
            Document.id.in_([uuid.UUID(doc_id) for doc_id in document_ids]),
            Document.processing_status == "completed"
        ).all()
        
        if len(documents) != len(document_ids):
            raise HTTPException(
                status_code=400,
                detail="One or more documents not found or not yet processed"
            )
        
        # Get conversation history for context (last 10 messages)
        conversation_history = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).limit(10).all()
        
        # Reverse to get chronological order
        conversation_history.reverse()
        
        # Format conversation context for RAGFlow
        conversation_context = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in conversation_history
        ]
        
        # Save user message
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=request.question
        )
        db.add(user_message)
        db.commit()
        
        logger.info(f"User message saved: {user_message.id}")
        
        # Add the new user message to context
        conversation_context.append({
            "role": "user",
            "content": request.question
        })
        
        # Get RAGFlow document IDs
        ragflow_doc_ids = [doc.ragflow_document_id for doc in documents if doc.ragflow_document_id]
        
        if not ragflow_doc_ids:
            raise HTTPException(
                status_code=400,
                detail="No valid RAGFlow document IDs found"
            )
        
        # Query RAGFlow with conversation context
        ragflow_response = await ragflow_client.query_documents(
            question=request.question,
            document_ids=ragflow_doc_ids,
            conversation_context=conversation_context
        )
        
        if ragflow_response["status"] == "success":
            response_data = ragflow_response["data"]
            answer = response_data.get("answer", "I couldn't find an answer to your question.")
            confidence_score = response_data.get("confidence_score", 0.0)
            
            # Extract and format citations using the enhanced citation system
            try:
                extracted_citations = ragflow_client.extract_citations(response_data)
                citations_for_storage = ragflow_client.format_citations_for_storage(extracted_citations)
                
                # Map RAGFlow document IDs back to our document IDs for citations
                doc_id_mapping = {doc.ragflow_document_id: str(doc.id) for doc in documents}
                for citation in citations_for_storage:
                    ragflow_doc_id = citation.get("document_id", "")
                    if ragflow_doc_id in doc_id_mapping:
                        citation["document_id"] = doc_id_mapping[ragflow_doc_id]
                        # Add document filename for better display
                        matching_doc = next((doc for doc in documents if doc.ragflow_document_id == ragflow_doc_id), None)
                        if matching_doc:
                            citation["document_filename"] = matching_doc.original_filename
                
                logger.info(f"Successfully processed {len(citations_for_storage)} citations")
            except Exception as e:
                logger.error(f"Error processing citations: {str(e)}")
                citations_for_storage = []  # Fallback to empty citations if processing fails
            
            # Save assistant message with enhanced citations
            assistant_message = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=answer,
                citations=citations_for_storage,
                confidence_score=confidence_score
            )
            db.add(assistant_message)
            db.commit()
            
            logger.info(f"Assistant message saved with {len(citations_for_storage)} citations: {assistant_message.id}")
            
            return {
                "status": "success",
                "message": {
                    "id": str(assistant_message.id),
                    "role": "assistant",
                    "content": answer,
                    "citations": citations_for_storage,
                    "confidence_score": confidence_score,
                    "created_at": assistant_message.created_at.isoformat()
                }
            }
        else:
            # Save error response
            error_message = f"I'm sorry, I encountered an error while processing your question: {ragflow_response['message']}"
            assistant_message = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=error_message
            )
            db.add(assistant_message)
            db.commit()
            
            return {
                "status": "success",
                "message": {
                    "id": str(assistant_message.id),
                    "role": "assistant",
                    "content": error_message,
                    "citations": [],
                    "confidence_score": 0.0,
                    "created_at": assistant_message.created_at.isoformat()
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@app.post("/api/chat")
async def quick_chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Quick chat endpoint that creates a conversation if needed"""
    try:
        # If conversation_id is provided, use existing conversation
        if request.conversation_id:
            return await send_message(request.conversation_id, request, db)
        
        # Otherwise, create a new conversation
        create_request = CreateConversationRequest(
            document_ids=request.document_ids,
            title=f"Quick chat: {request.question[:50]}..."
        )
        
        conversation_response = await create_conversation(create_request, db)
        conversation_id = conversation_response["conversation"]["id"]
        
        # Send the message to the new conversation
        return await send_message(conversation_id, request, db)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in quick chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Quick chat failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)