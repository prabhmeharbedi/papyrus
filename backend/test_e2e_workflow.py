#!/usr/bin/env python3
"""
End-to-end workflow test for PDF Chat App
Tests the complete workflow: upload -> process -> chat -> citations
"""

import asyncio
import httpx
import time
import json
from pathlib import Path
import tempfile
import sys
import os

# Add the backend directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class E2EWorkflowTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.client = None
        self.test_results = []
        
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    def log_test(self, test_name, success, message="", details=None):
        """Log test results"""
        status = "✓" if success else "✗"
        print(f"{status} {test_name}: {message}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "details": details
        })
        
        if details and not success:
            print(f"   Details: {details}")
    
    def create_test_pdf(self) -> bytes:
        """Create a simple test PDF with some text content"""
        # This creates a minimal valid PDF with some text
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
  /Font <<
    /F1 5 0 R
  >>
>>
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(This is a test PDF document for e2e testing.) Tj
ET
endstream
endobj

5 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
endobj

xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000274 00000 n 
0000000373 00000 n 
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
456
%%EOF"""
        return pdf_content
    
    async def test_health_check(self):
        """Test basic health check"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                self.log_test("Health Check", True, f"Service is {data.get('status', 'unknown')}")
                return True
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Check", False, f"Connection failed: {str(e)}")
            return False
    
    async def test_detailed_health_check(self):
        """Test detailed health check with dependencies"""
        try:
            response = await self.client.get(f"{self.base_url}/health/detailed")
            if response.status_code == 200:
                data = response.json()
                overall_status = data.get('status', 'unknown')
                checks = data.get('checks', {})
                
                # Check individual components
                db_status = checks.get('database', {}).get('status', 'unknown')
                ragflow_status = checks.get('ragflow', {}).get('status', 'unknown')
                
                self.log_test("Detailed Health Check", True, 
                             f"Overall: {overall_status}, DB: {db_status}, RAGFlow: {ragflow_status}")
                
                # Warn about unhealthy components
                for component, status_info in checks.items():
                    if status_info.get('status') == 'unhealthy':
                        print(f"   ⚠️  {component} is unhealthy: {status_info.get('message', 'Unknown error')}")
                
                return overall_status in ['healthy', 'degraded']
            else:
                self.log_test("Detailed Health Check", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Detailed Health Check", False, f"Error: {str(e)}")
            return False
    
    async def test_document_upload(self):
        """Test PDF document upload"""
        try:
            # Create test PDF
            pdf_content = self.create_test_pdf()
            
            # Upload the PDF
            files = {"file": ("test_e2e_document.pdf", pdf_content, "application/pdf")}
            response = await self.client.post(f"{self.base_url}/api/documents/upload", files=files)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    document_id = data.get("document_id")
                    self.log_test("Document Upload", True, f"Document uploaded: {document_id}")
                    return document_id
                else:
                    self.log_test("Document Upload", False, f"Upload failed: {data.get('message', 'Unknown error')}")
                    return None
            else:
                self.log_test("Document Upload", False, f"HTTP {response.status_code}: {response.text}")
                return None
        except Exception as e:
            self.log_test("Document Upload", False, f"Error: {str(e)}")
            return None
    
    async def test_document_processing_status(self, document_id, max_wait_time=120):
        """Test document processing status polling"""
        try:
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                response = await self.client.get(f"{self.base_url}/api/documents/{document_id}/status")
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("processing_status")
                    
                    if status == "completed":
                        page_count = data.get("page_count", 0)
                        self.log_test("Document Processing", True, 
                                    f"Processing completed in {int(time.time() - start_time)}s, {page_count} pages")
                        return True
                    elif status == "failed":
                        self.log_test("Document Processing", False, "Processing failed")
                        return False
                    elif status in ["pending", "processing"]:
                        print(f"   ⏳ Document processing status: {status} (waiting...)")
                        await asyncio.sleep(5)  # Wait 5 seconds before checking again
                    else:
                        self.log_test("Document Processing", False, f"Unknown status: {status}")
                        return False
                else:
                    self.log_test("Document Processing", False, f"HTTP {response.status_code}")
                    return False
            
            self.log_test("Document Processing", False, f"Timeout after {max_wait_time}s")
            return False
            
        except Exception as e:
            self.log_test("Document Processing", False, f"Error: {str(e)}")
            return False
    
    async def test_conversation_creation(self, document_id):
        """Test conversation creation"""
        try:
            payload = {
                "document_ids": [document_id],
                "title": "E2E Test Conversation"
            }
            
            response = await self.client.post(f"{self.base_url}/api/conversations/", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    conversation_id = data.get("conversation", {}).get("id")
                    self.log_test("Conversation Creation", True, f"Conversation created: {conversation_id}")
                    return conversation_id
                else:
                    self.log_test("Conversation Creation", False, f"Failed: {data.get('message', 'Unknown error')}")
                    return None
            else:
                self.log_test("Conversation Creation", False, f"HTTP {response.status_code}: {response.text}")
                return None
        except Exception as e:
            self.log_test("Conversation Creation", False, f"Error: {str(e)}")
            return None
    
    async def test_chat_functionality(self, conversation_id, document_id):
        """Test chat functionality with the uploaded document"""
        try:
            # Test a simple question
            payload = {
                "question": "What is this document about?",
                "document_ids": [document_id]
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/conversations/{conversation_id}/messages", 
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self.log_test("Chat Functionality", True, "AI response received")
                    
                    # Get the conversation to check messages
                    conv_response = await self.client.get(f"{self.base_url}/api/conversations/{conversation_id}")
                    if conv_response.status_code == 200:
                        conv_data = conv_response.json()
                        messages = conv_data.get("conversation", {}).get("messages", [])
                        
                        if len(messages) >= 2:  # User message + AI response
                            ai_message = messages[-1]  # Last message should be AI response
                            citations = ai_message.get("citations", [])
                            
                            self.log_test("Chat Response", True, 
                                        f"Response length: {len(ai_message.get('content', ''))} chars, "
                                        f"Citations: {len(citations)}")
                            
                            return True
                        else:
                            self.log_test("Chat Response", False, f"Expected 2+ messages, got {len(messages)}")
                            return False
                    else:
                        self.log_test("Chat Response", False, "Failed to retrieve conversation")
                        return False
                else:
                    self.log_test("Chat Functionality", False, f"Failed: {data.get('message', 'Unknown error')}")
                    return False
            else:
                self.log_test("Chat Functionality", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Chat Functionality", False, f"Error: {str(e)}")
            return False
    
    async def test_input_validation(self):
        """Test input validation and error handling"""
        validation_tests = []
        
        # Test empty question
        try:
            payload = {"question": "", "document_ids": ["dummy-id"]}
            response = await self.client.post(f"{self.base_url}/api/conversations/dummy/messages", json=payload)
            validation_tests.append(("Empty Question", response.status_code == 400))
        except:
            validation_tests.append(("Empty Question", False))
        
        # Test invalid document ID format
        try:
            payload = {"question": "test", "document_ids": ["invalid-uuid"]}
            response = await self.client.post(f"{self.base_url}/api/conversations/dummy/messages", json=payload)
            validation_tests.append(("Invalid UUID", response.status_code == 400))
        except:
            validation_tests.append(("Invalid UUID", False))
        
        # Test file upload validation (non-PDF)
        try:
            files = {"file": ("test.txt", b"not a pdf", "text/plain")}
            response = await self.client.post(f"{self.base_url}/api/documents/upload", files=files)
            validation_tests.append(("Non-PDF Upload", response.status_code == 400))
        except:
            validation_tests.append(("Non-PDF Upload", False))
        
        # Test oversized filename
        try:
            long_filename = "a" * 300 + ".pdf"
            files = {"file": (long_filename, self.create_test_pdf(), "application/pdf")}
            response = await self.client.post(f"{self.base_url}/api/documents/upload", files=files)
            validation_tests.append(("Long Filename", response.status_code == 400))
        except:
            validation_tests.append(("Long Filename", False))
        
        passed = sum(1 for _, success in validation_tests if success)
        total = len(validation_tests)
        
        self.log_test("Input Validation", passed == total, f"{passed}/{total} validation tests passed")
        
        for test_name, success in validation_tests:
            if not success:
                print(f"   ⚠️  {test_name} validation test failed")
        
        return passed == total
    
    async def test_error_handling(self):
        """Test error handling for various scenarios"""
        error_tests = []
        
        # Test non-existent document
        try:
            response = await self.client.get(f"{self.base_url}/api/documents/non-existent-id")
            error_tests.append(("Non-existent Document", response.status_code == 404))
        except:
            error_tests.append(("Non-existent Document", False))
        
        # Test non-existent conversation
        try:
            response = await self.client.get(f"{self.base_url}/api/conversations/non-existent-id")
            error_tests.append(("Non-existent Conversation", response.status_code == 404))
        except:
            error_tests.append(("Non-existent Conversation", False))
        
        # Test malformed JSON
        try:
            response = await self.client.post(
                f"{self.base_url}/api/conversations/",
                content="invalid json",
                headers={"Content-Type": "application/json"}
            )
            error_tests.append(("Malformed JSON", response.status_code == 422))
        except:
            error_tests.append(("Malformed JSON", False))
        
        passed = sum(1 for _, success in error_tests if success)
        total = len(error_tests)
        
        self.log_test("Error Handling", passed == total, f"{passed}/{total} error handling tests passed")
        
        for test_name, success in error_tests:
            if not success:
                print(f"   ⚠️  {test_name} error handling test failed")
        
        return passed == total
    
    async def run_full_workflow_test(self):
        """Run the complete end-to-end workflow test"""
        print("🚀 Starting End-to-End Workflow Test")
        print("=" * 50)
        
        # Step 1: Health checks
        if not await self.test_health_check():
            print("❌ Health check failed - aborting test")
            return False
        
        await self.test_detailed_health_check()
        
        # Step 2: Document upload
        document_id = await self.test_document_upload()
        if not document_id:
            print("❌ Document upload failed - aborting test")
            return False
        
        # Step 3: Wait for document processing
        if not await self.test_document_processing_status(document_id):
            print("❌ Document processing failed - aborting test")
            return False
        
        # Step 4: Create conversation
        conversation_id = await self.test_conversation_creation(document_id)
        if not conversation_id:
            print("❌ Conversation creation failed - aborting test")
            return False
        
        # Step 5: Test chat functionality
        if not await self.test_chat_functionality(conversation_id, document_id):
            print("❌ Chat functionality failed - aborting test")
            return False
        
        # Step 6: Test validation and error handling
        await self.test_input_validation()
        await self.test_error_handling()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Summary")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("\n🎉 All tests passed! The PDF Chat App is working correctly.")
            return True
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Please check the issues above.")
            return False

async def main():
    """Main test runner"""
    print("PDF Chat App - End-to-End Workflow Test")
    print("This test will verify the complete workflow from upload to chat")
    print()
    
    async with E2EWorkflowTest() as test_runner:
        success = await test_runner.run_full_workflow_test()
        
        if success:
            print("\n✅ E2E test completed successfully!")
            return 0
        else:
            print("\n❌ E2E test failed!")
            return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)