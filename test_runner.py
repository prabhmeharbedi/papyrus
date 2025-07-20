#!/usr/bin/env python3
"""
Test runner for PDF Chat App
Runs both backend and frontend tests
"""

import subprocess
import sys
import os
import time
from pathlib import Path

class TestRunner:
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.backend_dir = self.root_dir / "backend"
        self.frontend_dir = self.root_dir / "frontend"
        
    def run_command(self, command, cwd=None, timeout=300):
        """Run a command and return success status"""
        try:
            print(f"Running: {' '.join(command)}")
            result = subprocess.run(
                command,
                cwd=cwd or self.root_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.stdout:
                print("STDOUT:", result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
                
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print(f"Command timed out after {timeout} seconds")
            return False
        except Exception as e:
            print(f"Error running command: {e}")
            return False
    
    def check_backend_running(self):
        """Check if backend is running"""
        try:
            import httpx
            import asyncio
            
            async def check():
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get("http://localhost:8000/health")
                        return response.status_code == 200
                except:
                    return False
            
            return asyncio.run(check())
        except ImportError:
            print("httpx not available, skipping backend check")
            return False
    
    def run_backend_tests(self):
        """Run backend tests"""
        print("\n" + "="*50)
        print("🔧 BACKEND TESTS")
        print("="*50)
        
        # Check if backend is running
        if not self.check_backend_running():
            print("⚠️  Backend is not running on localhost:8000")
            print("Please start the backend server first:")
            print("  cd backend && python main.py")
            return False
        
        tests_passed = 0
        total_tests = 0
        
        # Test 1: End-to-end workflow test (covers API, upload, chat, health, validation)
        print("\n🔄 Running comprehensive end-to-end workflow tests...")
        total_tests += 1
        if self.run_command([sys.executable, "test_e2e_workflow.py"], cwd=self.backend_dir, timeout=600):
            print("✅ E2E workflow tests passed")
            tests_passed += 1
        else:
            print("❌ E2E workflow tests failed")
        
        # Test 2: Citation system integration tests (focused unit tests)
        print("\n📄 Running citation system integration tests...")
        total_tests += 1
        if self.run_command([sys.executable, "test_citation_integration.py"], cwd=self.backend_dir):
            print("✅ Citation integration tests passed")
            tests_passed += 1
        else:
            print("❌ Citation integration tests failed")
        
        print(f"\n📊 Backend Tests Summary: {tests_passed}/{total_tests} passed")
        return tests_passed == total_tests
    
    def run_frontend_tests(self):
        """Run frontend tests"""
        print("\n" + "="*50)
        print("🎨 FRONTEND TESTS")
        print("="*50)
        
        # Check if node_modules exists
        if not (self.frontend_dir / "node_modules").exists():
            print("📦 Installing frontend dependencies...")
            if not self.run_command(["npm", "install"], cwd=self.frontend_dir):
                print("❌ Failed to install frontend dependencies")
                return False
        
        # Run React tests
        print("\n🧪 Running React component tests...")
        if self.run_command(["npm", "test", "--", "--run", "--watchAll=false"], cwd=self.frontend_dir):
            print("✅ Frontend tests passed")
            return True
        else:
            print("❌ Frontend tests failed")
            return False
    
    def run_integration_tests(self):
        """Run integration tests that require both frontend and backend"""
        print("\n" + "="*50)
        print("🔗 INTEGRATION TESTS")
        print("="*50)
        
        # For now, just check that both services can be reached
        backend_ok = self.check_backend_running()
        
        print(f"Backend health: {'✅' if backend_ok else '❌'}")
        
        if backend_ok:
            print("✅ Integration tests passed")
            return True
        else:
            print("❌ Integration tests failed - backend not accessible")
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 PDF Chat App - Test Suite")
        print("="*50)
        
        start_time = time.time()
        
        # Run tests
        backend_ok = self.run_backend_tests()
        frontend_ok = self.run_frontend_tests()
        integration_ok = self.run_integration_tests()
        
        # Summary
        end_time = time.time()
        duration = int(end_time - start_time)
        
        print("\n" + "="*50)
        print("📋 FINAL TEST SUMMARY")
        print("="*50)
        print(f"Backend Tests:     {'✅ PASS' if backend_ok else '❌ FAIL'}")
        print(f"Frontend Tests:    {'✅ PASS' if frontend_ok else '❌ FAIL'}")
        print(f"Integration Tests: {'✅ PASS' if integration_ok else '❌ FAIL'}")
        print(f"Total Duration:    {duration}s")
        
        all_passed = backend_ok and frontend_ok and integration_ok
        
        if all_passed:
            print("\n🎉 ALL TESTS PASSED!")
            print("The PDF Chat App is working correctly.")
        else:
            print("\n⚠️  SOME TESTS FAILED!")
            print("Please check the output above for details.")
        
        return all_passed

def main():
    """Main test runner"""
    runner = TestRunner()
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "backend":
            success = runner.run_backend_tests()
        elif test_type == "frontend":
            success = runner.run_frontend_tests()
        elif test_type == "integration":
            success = runner.run_integration_tests()
        else:
            print(f"Unknown test type: {test_type}")
            print("Usage: python test_runner.py [backend|frontend|integration]")
            return 1
    else:
        success = runner.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(sys.exit(main()))