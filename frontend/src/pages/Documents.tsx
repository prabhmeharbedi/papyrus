import React, { useState, useRef, useEffect } from 'react';

interface Document {
  id: string;
  filename: string;
  file_size: number;
  upload_date: string;
  processing_status: string;
  page_count?: number;
}

interface UploadResponse {
  status: string;
  message?: string;
  document_id?: string;
  filename?: string;
  processing_status?: string;
}

const Documents: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [processingNotifications, setProcessingNotifications] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load documents on component mount and set up polling
  useEffect(() => {
    loadDocuments();
    
    // Set up polling for processing documents
    const pollInterval = setInterval(() => {
      pollProcessingDocuments();
    }, 5000); // Poll every 5 seconds
    
    return () => clearInterval(pollInterval);
  }, []);

  const loadDocuments = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/documents/');
      const data = await response.json();
      if (data.status === 'success') {
        setDocuments(data.documents);
      }
    } catch (error) {
      console.error('Error loading documents:', error);
    }
  };

  const pollProcessingDocuments = async () => {
    try {
      // Check if there are any processing documents
      const hasProcessingDocs = documents.some(doc => doc.processing_status === 'processing');
      
      if (hasProcessingDocs) {
        // Store current processing documents to detect completion
        const currentProcessingDocs = documents.filter(doc => doc.processing_status === 'processing');
        
        const response = await fetch('http://localhost:8000/api/documents/poll-status', {
          method: 'POST',
        });
        const data = await response.json();
        
        if (data.status === 'success') {
          // Reload documents to get updated statuses
          const updatedResponse = await fetch('http://localhost:8000/api/documents/');
          const updatedData = await updatedResponse.json();
          
          if (updatedData.status === 'success') {
            const updatedDocs = updatedData.documents;
            
            // Check for newly completed documents
            currentProcessingDocs.forEach(oldDoc => {
              const updatedDoc = updatedDocs.find((doc: Document) => doc.id === oldDoc.id);
              if (updatedDoc && updatedDoc.processing_status === 'completed') {
                // Add completion notification
                setProcessingNotifications(prev => [
                  ...prev,
                  `${updatedDoc.filename} has finished processing and is ready for chat!`
                ]);
                
                // Remove notification after 5 seconds
                setTimeout(() => {
                  setProcessingNotifications(prev => 
                    prev.filter(notif => !notif.includes(updatedDoc.filename))
                  );
                }, 5000);
              }
            });
            
            setDocuments(updatedDocs);
          }
        }
      }
    } catch (error) {
      console.error('Error polling document statuses:', error);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileUpload(e.target.files[0]);
    }
  };

  const validateFile = (file: File): string | null => {
    // Check if file exists
    if (!file) {
      return 'No file selected.';
    }
    
    // Check file type
    if (file.type !== 'application/pdf') {
      return `Invalid file type: ${file.type || 'unknown'}. Please select a PDF file.`;
    }
    
    // Check file extension as backup
    const fileName = file.name.toLowerCase();
    if (!fileName.endsWith('.pdf')) {
      return 'File must have a .pdf extension.';
    }
    
    // Check file size (50MB limit)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
      return `File size (${formatFileSize(file.size)}) exceeds the 50MB limit.`;
    }
    
    // Check minimum file size (1KB)
    const minSize = 1024;
    if (file.size < minSize) {
      return 'File appears to be empty or corrupted.';
    }
    
    // Check filename length
    if (file.name.length > 255) {
      return 'Filename is too long. Please rename the file to be shorter than 255 characters.';
    }
    
    // Check for invalid characters in filename
    const invalidChars = /[<>:"/\\|?*]/;
    if (invalidChars.test(file.name)) {
      return 'Filename contains invalid characters. Please remove: < > : " / \\ | ? *';
    }
    
    return null;
  };

  const handleFileUpload = async (file: File) => {
    setUploadError(null);
    setUploadSuccess(null);
    
    // Validate file
    const validationError = validateFile(file);
    if (validationError) {
      setUploadError(validationError);
      return;
    }

    setUploading(true);
    
    // Show progress feedback
    console.log(`Starting upload of ${file.name} (${formatFileSize(file.size)})`);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:8000/api/documents/upload', {
        method: 'POST',
        body: formData,
      });

      const data: UploadResponse = await response.json();

      if (data.status === 'success') {
        setUploadSuccess(`${data.filename} uploaded successfully and is being processed.`);
        // Reload documents list
        await loadDocuments();
        // Clear file input
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      } else {
        setUploadError(data.message || 'Upload failed');
      }
    } catch (error) {
      setUploadError('Upload failed. Please try again.');
      console.error('Upload error:', error);
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-100';
      case 'processing':
        return 'text-yellow-600 bg-yellow-100';
      case 'failed':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const handleDeleteDocument = async (documentId: string, filename: string) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"? This action cannot be undone.`)) {
      return;
    }

    try {
      const response = await fetch(`http://localhost:8000/api/documents/${documentId}`, {
        method: 'DELETE',
      });

      const data = await response.json();

      if (data.status === 'success') {
        setUploadSuccess(`Document "${filename}" deleted successfully.`);
        // Reload documents list
        await loadDocuments();
        
        // Clear success message after 3 seconds
        setTimeout(() => {
          setUploadSuccess(null);
        }, 3000);
      } else {
        setUploadError(data.message || 'Failed to delete document');
        
        // Clear error message after 5 seconds
        setTimeout(() => {
          setUploadError(null);
        }, 5000);
      }
    } catch (error) {
      console.error('Error deleting document:', error);
      setUploadError('Failed to delete document. Please try again.');
      
      // Clear error message after 5 seconds
      setTimeout(() => {
        setUploadError(null);
      }, 5000);
    }
  };

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">
          Document Management
        </h1>
        <p className="text-gray-600">
          Upload PDF documents to start chatting with them
        </p>
      </div>

      {/* Upload Area */}
      <div className="mb-8">
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragActive
              ? 'border-blue-400 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <div className="space-y-4">
            <div className="flex justify-center">
              <svg
                className="w-12 h-12 text-gray-400"
                stroke="currentColor"
                fill="none"
                viewBox="0 0 48 48"
              >
                <path
                  d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <div>
              <p className="text-lg font-medium text-gray-900">
                {dragActive ? 'Drop your PDF here' : 'Upload a PDF document'}
              </p>
              <p className="text-sm text-gray-500 mt-1">
                Drag and drop or click to select (Max 50MB)
              </p>
            </div>
            <div>
              <button
                type="button"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
              >
                {uploading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Uploading...
                  </>
                ) : (
                  'Select PDF'
                )}
              </button>
            </div>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileSelect}
            className="hidden"
          />
        </div>

        {/* Upload Status Messages */}
        {uploadError && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{uploadError}</p>
          </div>
        )}
        {uploadSuccess && (
          <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-md">
            <p className="text-sm text-green-600">{uploadSuccess}</p>
          </div>
        )}
        
        {/* Processing Completion Notifications */}
        {processingNotifications.map((notification, index) => (
          <div key={index} className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-blue-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <p className="text-sm text-blue-600">{notification}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Documents List */}
      <div>
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          Uploaded Documents ({documents.length})
        </h2>
        
        {documents.length === 0 ? (
          <div className="text-center py-8 bg-gray-50 rounded-lg">
            <p className="text-gray-500">No documents uploaded yet</p>
          </div>
        ) : (
          <div className="bg-white shadow overflow-hidden sm:rounded-md">
            <ul className="divide-y divide-gray-200">
              {documents.map((doc) => (
                <li key={doc.id} className="px-6 py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center">
                        <div className="flex-shrink-0">
                          <svg
                            className="w-8 h-8 text-red-500"
                            fill="currentColor"
                            viewBox="0 0 20 20"
                          >
                            <path
                              fillRule="evenodd"
                              d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
                              clipRule="evenodd"
                            />
                          </svg>
                        </div>
                        <div className="ml-4">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {doc.filename}
                          </p>
                          <p className="text-sm text-gray-500">
                            {formatFileSize(doc.file_size)} • Uploaded {formatDate(doc.upload_date)}
                            {doc.page_count && ` • ${doc.page_count} pages`}
                          </p>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(
                          doc.processing_status
                        )}`}
                      >
                        {doc.processing_status === 'processing' && (
                          <svg className="animate-spin -ml-1 mr-2 h-3 w-3 text-yellow-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                        )}
                        {doc.processing_status === 'completed' && (
                          <svg className="-ml-1 mr-2 h-3 w-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        )}
                        {doc.processing_status === 'failed' && (
                          <svg className="-ml-1 mr-2 h-3 w-3 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                          </svg>
                        )}
                        {doc.processing_status}
                      </span>
                      
                      {/* Document Actions */}
                      <div className="flex items-center space-x-2">
                        {/* View/Download Button */}
                        <button
                          onClick={() => window.open(`http://localhost:8000/api/documents/${doc.id}/file`, '_blank')}
                          className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                          title="View PDF"
                        >
                          📄 View
                        </button>
                        
                        {/* Delete Button */}
                        <button
                          onClick={() => handleDeleteDocument(doc.id, doc.filename)}
                          className="text-red-600 hover:text-red-800 text-sm font-medium"
                          title="Delete document"
                        >
                          🗑️ Delete
                        </button>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default Documents;