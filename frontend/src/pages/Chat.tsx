import React, { useState, useEffect, useRef } from 'react';
import PDFViewer from '../components/PDFViewer';

interface Citation {
  document_id: string;
  document_filename?: string;
  page_number: number;
  text_excerpt: string;
  start_position?: number;
  end_position?: number;
  confidence: number;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  confidence_score?: number;
  created_at: string;
}

interface Document {
  id: string;
  filename: string;
  processing_status: string;
  page_count?: number;
}

interface Conversation {
  id: string;
  title: string;
  document_ids: string[];
  created_at: string;
  updated_at: string;
  message_count: number;
}



const Chat: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Conversation state
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [showConversationHistory, setShowConversationHistory] = useState(false);
  
  // PDF viewer state
  const [currentPdfDocument, setCurrentPdfDocument] = useState<Document | null>(null);
  const [highlightPage, setHighlightPage] = useState<number | undefined>(undefined);
  const [highlightInfo, setHighlightInfo] = useState<{
    page: number;
    text: string;
    startPosition?: number;
    endPosition?: number;
  } | undefined>(undefined);
  const [showPdfViewer, setShowPdfViewer] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Fetch available documents and conversations on component mount
  useEffect(() => {
    fetchDocuments();
    fetchConversations();
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Mobile detection
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Auto-select first document for PDF viewer when documents are loaded
  useEffect(() => {
    if (documents.length > 0 && !currentPdfDocument) {
      setCurrentPdfDocument(documents[0]);
      setShowPdfViewer(true);
    }
  }, [documents, currentPdfDocument]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchDocuments = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/documents/');
      const data = await response.json();
      
      if (data.status === 'success') {
        // Only show completed documents
        const completedDocs = data.documents.filter(
          (doc: Document) => doc.processing_status === 'completed'
        );
        setDocuments(completedDocs);
      }
    } catch (err) {
      console.error('Error fetching documents:', err);
      setError('Failed to load documents');
    }
  };

  const fetchConversations = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/conversations/');
      const data = await response.json();
      
      if (data.status === 'success') {
        setConversations(data.conversations);
      }
    } catch (err) {
      console.error('Error fetching conversations:', err);
      // Don't set error for conversations as it's not critical
    }
  };

  const createNewConversation = async (documentIds: string[], title?: string) => {
    try {
      const response = await fetch('http://localhost:8000/api/conversations/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_ids: documentIds,
          title: title || `Chat with ${documentIds.length} document(s)`
        }),
      });

      const data = await response.json();

      if (data.status === 'success') {
        const newConversation = data.conversation;
        setConversations(prev => [newConversation, ...prev]);
        setCurrentConversation(newConversation);
        return newConversation;
      } else {
        throw new Error(data.message || 'Failed to create conversation');
      }
    } catch (err) {
      console.error('Error creating conversation:', err);
      setError('Failed to create new conversation');
      return null;
    }
  };

  const loadConversation = async (conversationId: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/conversations/${conversationId}`);
      const data = await response.json();

      if (data.status === 'success') {
        const conversation = data.conversation;
        setCurrentConversation(conversation);
        setMessages(conversation.messages || []);
        setSelectedDocuments(conversation.document_ids);
        return conversation;
      } else {
        throw new Error(data.message || 'Failed to load conversation');
      }
    } catch (err) {
      console.error('Error loading conversation:', err);
      setError('Failed to load conversation');
      return null;
    }
  };

  const startNewChat = () => {
    setCurrentConversation(null);
    setMessages([]);
    setSelectedDocuments([]);
    setError(null);
  };

  const handleDocumentSelection = (documentId: string) => {
    setSelectedDocuments(prev => {
      if (prev.includes(documentId)) {
        return prev.filter(id => id !== documentId);
      } else {
        return [...prev, documentId];
      }
    });
  };

  const sendMessage = async () => {
    // Input validation and sanitization
    const trimmedMessage = currentMessage.trim();
    
    if (!trimmedMessage) {
      setError('Please enter a message');
      return;
    }
    
    if (trimmedMessage.length < 3) {
      setError('Message must be at least 3 characters long');
      return;
    }
    
    if (trimmedMessage.length > 10000) {
      setError('Message is too long. Please keep it under 10,000 characters');
      return;
    }
    
    if (selectedDocuments.length === 0) {
      setError('Please select at least one document to chat with');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      let conversationId = currentConversation?.id;

      // Create new conversation if none exists
      if (!conversationId) {
        const newConversation = await createNewConversation(
          selectedDocuments,
          `Chat: ${currentMessage.slice(0, 50)}...`
        );
        if (!newConversation) {
          setIsLoading(false);
          return;
        }
        conversationId = newConversation.id;
      }

      // Send message to conversation
      const response = await fetch(`http://localhost:8000/api/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: currentMessage,
          document_ids: selectedDocuments
        }),
      });

      const data = await response.json();

      if (data.status === 'success') {
        // Reload the conversation to get updated messages with proper IDs
        if (conversationId) {
          await loadConversation(conversationId);
        }
        // Refresh conversations list to update message count
        await fetchConversations();
      } else {
        setError('Failed to get response from AI');
      }
    } catch (err) {
      console.error('Error sending message:', err);
      setError('Failed to send message');
    } finally {
      setIsLoading(false);
      setCurrentMessage('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  // PDF viewer functions
  const handleCitationClick = (citation: Citation) => {
    // Find the document for this citation
    const citedDocument = documents.find(doc => doc.id === citation.document_id);
    if (citedDocument) {
      setCurrentPdfDocument(citedDocument);
      setHighlightPage(citation.page_number);
      
      // Set highlight information for text highlighting
      setHighlightInfo({
        page: citation.page_number,
        text: citation.text_excerpt,
        startPosition: citation.start_position,
        endPosition: citation.end_position
      });
      
      setShowPdfViewer(true);
    }
  };

  const handleDocumentViewerChange = (documentId: string) => {
    const document = documents.find(doc => doc.id === documentId);
    if (document) {
      setCurrentPdfDocument(document);
      setHighlightPage(undefined);
      setHighlightInfo(undefined); // Clear highlight info when switching documents
    }
  };

  const togglePdfViewer = () => {
    setShowPdfViewer(!showPdfViewer);
  };

  const getPdfUrl = (document: Document) => {
    return `http://localhost:8000/api/documents/${document.id}/file`;
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-gray-900">Chat with Your Documents</h1>
          
          <div className="flex items-center space-x-2">
            {/* Conversation History Toggle */}
            <button
              onClick={() => setShowConversationHistory(!showConversationHistory)}
              className="px-3 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 text-sm flex items-center space-x-1"
            >
              <span>💬</span>
              <span>History</span>
              {conversations.length > 0 && (
                <span className="bg-blue-500 text-white text-xs rounded-full px-2 py-1 ml-1">
                  {conversations.length}
                </span>
              )}
            </button>
            
            {/* New Chat Button */}
            {currentConversation && (
              <button
                onClick={startNewChat}
                className="px-3 py-2 bg-green-100 text-green-700 rounded-md hover:bg-green-200 text-sm flex items-center space-x-1"
              >
                <span>✨</span>
                <span>New Chat</span>
              </button>
            )}
            
            {/* PDF Viewer Toggle for Mobile */}
            {isMobile && documents.length > 0 && (
              <button
                onClick={togglePdfViewer}
                className="px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
              >
                {showPdfViewer ? 'Show Chat' : 'Show PDF'}
              </button>
            )}
          </div>
        </div>
        
        {/* Current Conversation Indicator */}
        {currentConversation && (
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-blue-900">Current Conversation</h3>
                <p className="text-sm text-blue-700">{currentConversation.title}</p>
              </div>
              <div className="text-xs text-blue-600">
                💬 {messages.length} messages
              </div>
            </div>
          </div>
        )}

        {/* Document Selection */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-700">
              {currentConversation ? 'Documents in this conversation:' : 'Select Documents to Chat With:'}
            </h3>
            {!currentConversation && documents.length > 0 && (
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setSelectedDocuments(documents.map(doc => doc.id))}
                  className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                  disabled={selectedDocuments.length === documents.length}
                >
                  Select All
                </button>
                <span className="text-gray-300">|</span>
                <button
                  onClick={() => setSelectedDocuments([])}
                  className="text-xs text-gray-600 hover:text-gray-800 font-medium"
                  disabled={selectedDocuments.length === 0}
                >
                  Clear All
                </button>
              </div>
            )}
          </div>
          
          {currentConversation && (
            <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-md">
              <div className="flex items-start space-x-2">
                <span className="text-blue-600 text-sm">💡</span>
                <div className="text-xs text-blue-700">
                  <strong>Multi-Document Context:</strong> This conversation maintains context across all selected documents. 
                  The AI can reference information from any of these documents and compare insights between them.
                </div>
              </div>
            </div>
          )}
          
          {documents.length === 0 ? (
            <div className="text-center py-6 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
              <p className="text-sm text-gray-500 mb-2">No processed documents available</p>
              <p className="text-xs text-gray-400">Please upload and process documents first in the Documents tab</p>
            </div>
          ) : (
            <div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {documents.map((doc) => (
                  <label
                    key={doc.id}
                    className={`relative flex items-center p-3 rounded-lg border-2 transition-all cursor-pointer ${
                      selectedDocuments.includes(doc.id)
                        ? 'bg-blue-50 border-blue-300 shadow-sm'
                        : currentConversation
                          ? 'bg-gray-50 border-gray-200 cursor-not-allowed opacity-60'
                          : 'bg-white border-gray-200 hover:border-gray-300 hover:shadow-sm'
                    }`}
                  >
                    <input
                      type="checkbox"
                      className="sr-only"
                      checked={selectedDocuments.includes(doc.id)}
                      onChange={() => handleDocumentSelection(doc.id)}
                      disabled={!!currentConversation}
                    />
                    
                    <div className="flex-shrink-0 mr-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${
                        selectedDocuments.includes(doc.id)
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-200 text-gray-600'
                      }`}>
                        {selectedDocuments.includes(doc.id) ? '✓' : '📄'}
                      </div>
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {doc.filename}
                      </p>
                      <div className="flex items-center space-x-2 mt-1">
                        {doc.page_count && (
                          <span className="text-xs text-gray-500">
                            {doc.page_count} pages
                          </span>
                        )}
                        <span className="text-xs text-green-600 bg-green-100 px-2 py-0.5 rounded-full">
                          Ready
                        </span>
                      </div>
                    </div>
                    
                    {selectedDocuments.includes(doc.id) && (
                      <div className="absolute top-2 right-2">
                        <div className="w-4 h-4 bg-blue-600 rounded-full flex items-center justify-center">
                          <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        </div>
                      </div>
                    )}
                  </label>
                ))}
              </div>
              
              {/* Selection Summary */}
              <div className="mt-3 flex items-center justify-between text-xs text-gray-600">
                <span>
                  {selectedDocuments.length} of {documents.length} documents selected
                  {selectedDocuments.length > 0 && (
                    <span className="ml-2 text-blue-600">
                      ({documents.filter(doc => selectedDocuments.includes(doc.id)).reduce((sum, doc) => sum + (doc.page_count || 0), 0)} total pages)
                    </span>
                  )}
                </span>
                {!currentConversation && selectedDocuments.length > 1 && (
                  <span className="text-blue-600 bg-blue-50 px-2 py-1 rounded">
                    Multi-document chat enabled
                  </span>
                )}
              </div>
              
              {currentConversation && (
                <p className="text-xs text-gray-500 mt-2 bg-gray-50 p-2 rounded border">
                  📌 Document selection is locked for existing conversations. Start a new chat to select different documents.
                </p>
              )}
            </div>
          )}
        </div>

        {/* PDF Document Selector for Viewer */}
        {documents.length > 0 && !isMobile && (
          <div className="mb-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">PDF Viewer:</h3>
            <div className="flex items-center space-x-2">
              <select
                value={currentPdfDocument?.id || ''}
                onChange={(e) => handleDocumentViewerChange(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {documents.map((doc) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.filename}
                  </option>
                ))}
              </select>
              <button
                onClick={togglePdfViewer}
                className={`px-3 py-2 text-sm rounded-md transition-colors ${
                  showPdfViewer
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {showPdfViewer ? 'Hide PDF' : 'Show PDF'}
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3 mb-4">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}
      </div>

      {/* Main Content Area - Side by Side Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Conversation History Sidebar */}
        {showConversationHistory && (
          <div className="w-80 bg-gray-50 border-r border-gray-200 flex flex-col">
            <div className="p-4 border-b border-gray-200 bg-white">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Conversation History</h3>
                <button
                  onClick={() => setShowConversationHistory(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4">
              {conversations.length === 0 ? (
                <div className="text-center text-gray-500 mt-8">
                  <p className="text-sm">No conversations yet</p>
                  <p className="text-xs mt-1">Start chatting to see your history here</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {conversations.map((conversation) => (
                    <div
                      key={conversation.id}
                      onClick={() => {
                        loadConversation(conversation.id);
                        setShowConversationHistory(false);
                      }}
                      className={`p-3 rounded-lg border cursor-pointer transition-all hover:shadow-md ${
                        currentConversation?.id === conversation.id
                          ? 'bg-blue-50 border-blue-200 shadow-sm'
                          : 'bg-white border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="text-sm font-medium text-gray-900 truncate flex-1 mr-2">
                          {conversation.title}
                        </h4>
                        <span className="text-xs text-gray-500 whitespace-nowrap">
                          {new Date(conversation.updated_at).toLocaleDateString()}
                        </span>
                      </div>
                      
                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <span>
                          📄 {conversation.document_ids.length} document{conversation.document_ids.length !== 1 ? 's' : ''}
                        </span>
                        <span>
                          💬 {conversation.message_count} message{conversation.message_count !== 1 ? 's' : ''}
                        </span>
                      </div>
                      
                      {/* Show document names */}
                      <div className="mt-2 flex flex-wrap gap-1">
                        {conversation.document_ids.slice(0, 2).map((docId) => {
                          const doc = documents.find(d => d.id === docId);
                          return doc ? (
                            <span
                              key={docId}
                              className="inline-block px-2 py-1 bg-gray-100 text-xs text-gray-600 rounded truncate max-w-24"
                              title={doc.filename}
                            >
                              {doc.filename}
                            </span>
                          ) : null;
                        })}
                        {conversation.document_ids.length > 2 && (
                          <span className="inline-block px-2 py-1 bg-gray-100 text-xs text-gray-600 rounded">
                            +{conversation.document_ids.length - 2} more
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Chat Panel */}
        <div className={`flex flex-col ${
          showConversationHistory 
            ? (isMobile ? 'hidden' : 'flex-1')
            : isMobile 
              ? (showPdfViewer ? 'hidden' : 'w-full')
              : showPdfViewer && currentPdfDocument 
                ? 'w-1/2 border-r border-gray-200' 
                : 'w-full'
        }`}>
          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center text-gray-500 mt-8">
                <p className="text-lg mb-2">Ready to chat!</p>
                <p className="text-sm">Select documents above and ask your first question.</p>
              </div>
            ) : (
              <>
                {messages.map((message) => (
                  <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-3xl px-4 py-2 rounded-lg ${
                      message.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{message.content}</div>
                    
                    {/* Enhanced Citations for assistant messages */}
                    {message.role === 'assistant' && message.citations && message.citations.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-300">
                        {/* Citation Summary */}
                        <div className="flex items-center justify-between mb-3">
                          <p className="text-xs font-medium text-gray-600">
                            📄 Sources ({message.citations.length} reference{message.citations.length !== 1 ? 's' : ''}):
                          </p>
                          {/* Show unique document count */}
                          {(() => {
                            const uniqueDocuments = Array.from(new Set(message.citations.map(c => c.document_id)));
                            return uniqueDocuments.length > 1 && (
                              <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded-full font-medium">
                                📚 {uniqueDocuments.length} documents
                              </span>
                            );
                          })()}
                        </div>
                        
                        {/* Group citations by document */}
                        {(() => {
                          const citationsByDoc = message.citations.reduce((acc, citation, index) => {
                            const docId = citation.document_id;
                            if (!acc[docId]) {
                              acc[docId] = [];
                            }
                            acc[docId].push({ ...citation, originalIndex: index });
                            return acc;
                          }, {} as Record<string, (Citation & { originalIndex: number })[]>);

                          return Object.entries(citationsByDoc).map(([docId, docCitations]) => (
                            <div key={docId} className="mb-3 last:mb-0">
                              {/* Document Header */}
                              <div className="flex items-center space-x-2 mb-2">
                                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                                <span className="text-xs font-semibold text-gray-800">
                                  {docCitations[0].document_filename || `Document ${docCitations[0].originalIndex + 1}`}
                                </span>
                                <span className="text-xs text-gray-500">
                                  ({docCitations.length} reference{docCitations.length !== 1 ? 's' : ''})
                                </span>
                              </div>
                              
                              {/* Citations for this document */}
                              <div className="space-y-2 ml-4">
                                {docCitations.map((citation, citationIndex) => (
                                  <div
                                    key={citationIndex}
                                    className="bg-gray-50 border border-gray-200 rounded-md p-3 text-xs hover:bg-blue-50 hover:border-blue-300 transition-all cursor-pointer group"
                                    onClick={() => handleCitationClick(citation)}
                                    title="Click to highlight text in PDF viewer"
                                  >
                                    <div className="flex items-start justify-between mb-2">
                                      <div className="flex items-center space-x-2">
                                        <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-medium group-hover:bg-blue-200 transition-colors">
                                          📄 Page {citation.page_number}
                                        </span>
                                        {citation.confidence > 0 && (
                                          <span className="text-gray-500 text-xs">
                                            {Math.round(citation.confidence * 100)}% match
                                          </span>
                                        )}
                                      </div>
                                      <span className="text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity">
                                        🔍 View
                                      </span>
                                    </div>
                                    
                                    {citation.text_excerpt && (
                                      <div className="text-gray-600 italic border-l-3 border-blue-200 pl-3 mt-2 bg-white p-2 rounded group-hover:border-blue-300 transition-colors">
                                        <span className="text-xs text-gray-500 block mb-1">📝 Excerpt:</span>
                                        <span className="text-gray-700">"{citation.text_excerpt}"</span>
                                      </div>
                                    )}
                                    
                                    <div className="mt-2 text-xs text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity">
                                      ✨ Click to highlight this text in the PDF
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ));
                        })()}
                        
                        <div className="mt-3 text-xs text-gray-500 bg-blue-50 p-2 rounded border border-blue-200">
                          💡 <strong>Multi-Document Support:</strong> This response draws from {Array.from(new Set(message.citations.map(c => c.document_id))).length > 1 ? 'multiple documents' : 'one document'}. Click any citation to jump to that page and highlight the referenced text.
                        </div>
                      </div>
                    )}

                    {/* Confidence score for assistant messages */}
                    {message.role === 'assistant' && message.confidence_score !== undefined && (
                      <div className="mt-1 text-xs text-gray-500">
                        Confidence: {Math.round(message.confidence_score * 100)}%
                      </div>
                    )}

                    <div className={`text-xs mt-1 ${
                      message.role === 'user' ? 'text-blue-200' : 'text-gray-500'
                    }`}>
                      {formatTimestamp(message.created_at)}
                    </div>
                  </div>
                </div>
              ))
              </>
            )}

            {/* Enhanced Loading indicator */}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 text-gray-900 max-w-3xl px-4 py-3 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                    </div>
                    <span className="text-sm">AI is analyzing your documents and preparing a response...</span>
                  </div>
                  <div className="mt-2 text-xs text-gray-500">
                    💡 This may take a few seconds for complex queries
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="bg-white border-t border-gray-200 p-4">
            <div className="flex space-x-4">
              <div className="flex-1">
                <textarea
                  value={currentMessage}
                  onChange={(e) => setCurrentMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={
                    selectedDocuments.length === 0
                      ? "Select documents above to start chatting..."
                      : "Ask a question about your documents..."
                  }
                  disabled={selectedDocuments.length === 0 || isLoading}
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none ${
                    currentMessage.length > 10000 
                      ? 'border-red-300 focus:ring-red-500' 
                      : 'border-gray-300'
                  }`}
                  rows={3}
                />
                <div className="flex justify-between items-center mt-1">
                  <p className="text-xs text-gray-500">
                    Press Enter to send, Shift+Enter for new line
                  </p>
                  <p className={`text-xs ${
                    currentMessage.length > 10000 
                      ? 'text-red-500' 
                      : currentMessage.length > 8000 
                        ? 'text-yellow-600' 
                        : 'text-gray-500'
                  }`}>
                    {currentMessage.length}/10,000 characters
                  </p>
                </div>
              </div>
              <button
                onClick={sendMessage}
                disabled={!currentMessage.trim() || selectedDocuments.length === 0 || isLoading}
                className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed self-start"
              >
                {isLoading ? 'Sending...' : 'Send'}
              </button>
            </div>
          </div>
        </div>

        {/* PDF Viewer Panel */}
        {showPdfViewer && currentPdfDocument && (
          <div className={`${
            isMobile ? 'w-full' : 'w-1/2'
          } bg-gray-50`}>
            <PDFViewer
              fileUrl={getPdfUrl(currentPdfDocument)}
              highlightPage={highlightPage}
              highlightInfo={highlightInfo}
              onLoadSuccess={(pdf) => {
                console.log('PDF loaded successfully:', pdf);
              }}
              onLoadError={(error) => {
                console.error('PDF load error:', error);
                setError('Failed to load PDF document');
              }}
              className="h-full"
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default Chat;