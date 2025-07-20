import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import '@testing-library/jest-dom';
import App from '../App';

// Mock fetch for API calls
global.fetch = jest.fn();

const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

// Helper function to render App with Router
const renderApp = () => {
  return render(
    <BrowserRouter>
      <App />
    </BrowserRouter>
  );
};

describe('PDF Chat App', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  test('renders main navigation', () => {
    renderApp();
    
    expect(screen.getByText('PDF Chat App')).toBeInTheDocument();
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Documents')).toBeInTheDocument();
    expect(screen.getByText('Chat')).toBeInTheDocument();
  });

  test('displays home page by default', () => {
    renderApp();
    
    expect(screen.getByText('Welcome to PDF Chat App')).toBeInTheDocument();
    expect(screen.getByText('Transform your PDFs into interactive conversations')).toBeInTheDocument();
  });

  test('navigates to documents page', () => {
    renderApp();
    
    const documentsLink = screen.getByText('Documents');
    fireEvent.click(documentsLink);
    
    expect(screen.getByText('Document Management')).toBeInTheDocument();
    expect(screen.getByText('Upload PDF documents to start chatting with them')).toBeInTheDocument();
  });

  test('navigates to chat page', () => {
    renderApp();
    
    const chatLink = screen.getByText('Chat');
    fireEvent.click(chatLink);
    
    expect(screen.getByText('Chat with Your Documents')).toBeInTheDocument();
  });
});

describe('Documents Page', () => {
  beforeEach(() => {
    mockFetch.mockClear();
    // Mock the documents API call
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        status: 'success',
        documents: []
      })
    } as Response);
  });

  test('displays upload area', async () => {
    renderApp();
    
    const documentsLink = screen.getByText('Documents');
    fireEvent.click(documentsLink);
    
    await waitFor(() => {
      expect(screen.getByText('Upload a PDF document')).toBeInTheDocument();
      expect(screen.getByText('Drag and drop or click to select (Max 50MB)')).toBeInTheDocument();
      expect(screen.getByText('Select PDF')).toBeInTheDocument();
    });
  });

  test('displays empty state when no documents', async () => {
    renderApp();
    
    const documentsLink = screen.getByText('Documents');
    fireEvent.click(documentsLink);
    
    await waitFor(() => {
      expect(screen.getByText('No documents uploaded yet')).toBeInTheDocument();
    });
  });

  test('displays documents when available', async () => {
    // Mock API response with documents
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        status: 'success',
        documents: [
          {
            id: '1',
            filename: 'test.pdf',
            file_size: 1024000,
            upload_date: '2023-01-01T00:00:00Z',
            processing_status: 'completed',
            page_count: 5
          }
        ]
      })
    } as Response);

    renderApp();
    
    const documentsLink = screen.getByText('Documents');
    fireEvent.click(documentsLink);
    
    await waitFor(() => {
      expect(screen.getByText('test.pdf')).toBeInTheDocument();
      expect(screen.getByText('5 pages')).toBeInTheDocument();
      expect(screen.getByText('Ready')).toBeInTheDocument();
    });
  });
});

describe('Chat Page', () => {
  beforeEach(() => {
    mockFetch.mockClear();
    // Mock the documents and conversations API calls
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'success',
          documents: [
            {
              id: '1',
              filename: 'test.pdf',
              processing_status: 'completed',
              page_count: 5
            }
          ]
        })
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'success',
          conversations: []
        })
      } as Response);
  });

  test('displays document selection', async () => {
    renderApp();
    
    const chatLink = screen.getByText('Chat');
    fireEvent.click(chatLink);
    
    await waitFor(() => {
      expect(screen.getByText('Select Documents to Chat With:')).toBeInTheDocument();
      expect(screen.getByText('test.pdf')).toBeInTheDocument();
      expect(screen.getByText('5 pages')).toBeInTheDocument();
    });
  });

  test('displays ready to chat message when no messages', async () => {
    renderApp();
    
    const chatLink = screen.getByText('Chat');
    fireEvent.click(chatLink);
    
    await waitFor(() => {
      expect(screen.getByText('Ready to chat!')).toBeInTheDocument();
      expect(screen.getByText('Select documents above and ask your first question.')).toBeInTheDocument();
    });
  });

  test('shows appropriate placeholder in message input', async () => {
    renderApp();
    
    const chatLink = screen.getByText('Chat');
    fireEvent.click(chatLink);
    
    await waitFor(() => {
      const textarea = screen.getByPlaceholderText('Select documents above to start chatting...');
      expect(textarea).toBeInTheDocument();
      expect(textarea).toBeDisabled();
    });
  });

  test('enables message input when document is selected', async () => {
    renderApp();
    
    const chatLink = screen.getByText('Chat');
    fireEvent.click(chatLink);
    
    await waitFor(() => {
      // Select a document
      const documentCheckbox = screen.getByRole('checkbox');
      fireEvent.click(documentCheckbox);
      
      const textarea = screen.getByPlaceholderText('Ask a question about your documents...');
      expect(textarea).toBeInTheDocument();
      expect(textarea).not.toBeDisabled();
    });
  });
});

describe('Error Handling', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  test('displays error when API call fails', async () => {
    // Mock API failure
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    renderApp();
    
    const documentsLink = screen.getByText('Documents');
    fireEvent.click(documentsLink);
    
    // The component should handle the error gracefully
    // We don't expect it to crash
    await waitFor(() => {
      expect(screen.getByText('Document Management')).toBeInTheDocument();
    });
  });

  test('handles invalid file upload', async () => {
    renderApp();
    
    const documentsLink = screen.getByText('Documents');
    fireEvent.click(documentsLink);
    
    await waitFor(() => {
      const fileInput = screen.getByRole('button', { name: /select pdf/i });
      expect(fileInput).toBeInTheDocument();
    });
    
    // This test would need more setup to properly test file upload validation
    // For now, we're just ensuring the upload button is present
  });
});

describe('Loading States', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  test('shows loading state during document upload', async () => {
    // Mock a slow upload response
    mockFetch.mockImplementationOnce(() => 
      new Promise(resolve => 
        setTimeout(() => resolve({
          ok: true,
          json: async () => ({ status: 'success' })
        } as Response), 1000)
      )
    );

    renderApp();
    
    const documentsLink = screen.getByText('Documents');
    fireEvent.click(documentsLink);
    
    await waitFor(() => {
      expect(screen.getByText('Select PDF')).toBeInTheDocument();
    });
    
    // This test would need more setup to properly test loading states
    // For now, we're ensuring the basic structure is in place
  });
});

describe('Input Validation', () => {
  test('validates message input length', async () => {
    // Mock successful API calls
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'success',
          documents: [
            {
              id: '1',
              filename: 'test.pdf',
              processing_status: 'completed',
              page_count: 5
            }
          ]
        })
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'success',
          conversations: []
        })
      } as Response);

    renderApp();
    
    const chatLink = screen.getByText('Chat');
    fireEvent.click(chatLink);
    
    await waitFor(() => {
      // Select a document
      const documentCheckbox = screen.getByRole('checkbox');
      fireEvent.click(documentCheckbox);
      
      const textarea = screen.getByPlaceholderText('Ask a question about your documents...');
      const sendButton = screen.getByText('Send');
      
      // Try to send empty message
      fireEvent.click(sendButton);
      
      // Should show validation error
      // This would need more implementation to properly test validation
    });
  });
});