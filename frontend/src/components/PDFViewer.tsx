import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Set up PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

interface HighlightInfo {
  page: number;
  text: string;
  startPosition?: number;
  endPosition?: number;
}

interface PDFViewerProps {
  fileUrl: string;
  onLoadSuccess?: (pdf: any) => void;
  onLoadError?: (error: Error) => void;
  highlightPage?: number;
  highlightInfo?: HighlightInfo;
  className?: string;
}

const PDFViewer: React.FC<PDFViewerProps> = ({
  fileUrl,
  onLoadSuccess,
  onLoadError,
  highlightPage,
  highlightInfo,
  className = ''
}) => {
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const pageRef = useRef<HTMLDivElement>(null);

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setIsLoading(false);
    setError(null);
    if (onLoadSuccess) {
      onLoadSuccess({ numPages });
    }
  }, [onLoadSuccess]);

  const onDocumentLoadError = useCallback((error: Error) => {
    setIsLoading(false);
    setError('Failed to load PDF document');
    console.error('PDF load error:', error);
    if (onLoadError) {
      onLoadError(error);
    }
  }, [onLoadError]);

  const goToPage = useCallback((pageNumber: number) => {
    if (pageNumber >= 1 && pageNumber <= numPages) {
      setCurrentPage(pageNumber);
    }
  }, [numPages]);

  const zoomIn = () => {
    setScale(prev => Math.min(prev + 0.25, 3.0));
  };

  const zoomOut = () => {
    setScale(prev => Math.max(prev - 0.25, 0.5));
  };

  const resetZoom = () => {
    setScale(1.0);
  };

  // Navigate to highlighted page when highlightPage changes
  React.useEffect(() => {
    if (highlightPage && highlightPage !== currentPage) {
      goToPage(highlightPage);
    }
  }, [highlightPage, currentPage, goToPage]);

  const clearHighlights = useCallback(() => {
    if (!pageRef.current) return;
    
    const highlightedElements = pageRef.current.querySelectorAll('.pdf-highlight');
    highlightedElements.forEach(element => {
      const htmlElement = element as HTMLElement;
      htmlElement.style.backgroundColor = '';
      htmlElement.style.borderRadius = '';
      htmlElement.style.padding = '';
      htmlElement.classList.remove('pdf-highlight');
    });
  }, []);

  const highlightTextInPage = useCallback((searchText: string) => {
    if (!pageRef.current || !searchText) return;

    // Clear previous highlights
    clearHighlights();

    // Wait for text layer to be rendered
    setTimeout(() => {
      const textLayer = pageRef.current?.querySelector('.react-pdf__Page__textContent');
      if (!textLayer) return;

      // Find and highlight text
      const textItems = textLayer.querySelectorAll('span');
      let foundText = '';
      let highlightElements: HTMLElement[] = [];

      // Search for the text across multiple spans
      for (let i = 0; i < textItems.length; i++) {
        const span = textItems[i] as HTMLElement;
        const spanText = span.textContent || '';
        
        // Check if this span contains part of our search text
        const searchLower = searchText.toLowerCase();
        const combinedText = (foundText + spanText).toLowerCase();
        
        if (combinedText.includes(searchLower)) {
          // Found the text, highlight relevant spans
          const startIndex = combinedText.indexOf(searchLower);
          const endIndex = startIndex + searchLower.length;
          
          // Determine which spans to highlight
          let currentLength = foundText.length;
          for (let j = Math.max(0, i - 10); j <= Math.min(textItems.length - 1, i + 10); j++) {
            const currentSpan = textItems[j] as HTMLElement;
            const currentSpanText = currentSpan.textContent || '';
            const spanStart = currentLength;
            const spanEnd = currentLength + currentSpanText.length;
            
            // Check if this span overlaps with our highlight range
            if (spanEnd > startIndex && spanStart < endIndex) {
              highlightElements.push(currentSpan);
            }
            
            currentLength += currentSpanText.length;
          }
          break;
        }
        
        foundText += spanText;
        
        // Limit search to prevent performance issues
        if (foundText.length > searchText.length + 1000) {
          foundText = foundText.slice(-500); // Keep last 500 chars
        }
      }

      // Apply highlights
      highlightElements.forEach(element => {
        element.style.backgroundColor = 'rgba(255, 255, 0, 0.3)';
        element.style.borderRadius = '2px';
        element.style.padding = '1px 2px';
        element.classList.add('pdf-highlight');
      });

      // Scroll to first highlighted element
      if (highlightElements.length > 0) {
        highlightElements[0].scrollIntoView({ 
          behavior: 'smooth', 
          block: 'center' 
        });
      }
    }, 500); // Wait for text layer to render
  }, [clearHighlights]);

  // Highlight text when highlightInfo changes
  useEffect(() => {
    if (highlightInfo && highlightInfo.page === currentPage && pageRef.current) {
      highlightTextInPage(highlightInfo.text);
    }
  }, [highlightInfo, currentPage, highlightTextInPage]);

  // Clear highlights when page changes
  useEffect(() => {
    clearHighlights();
  }, [currentPage, clearHighlights]);

  if (error) {
    return (
      <div className={`flex items-center justify-center h-full bg-gray-50 ${className}`}>
        <div className="text-center">
          <div className="text-red-500 text-lg mb-2">⚠️</div>
          <p className="text-gray-600">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-full bg-gray-50 ${className}`}>
      {/* PDF Controls */}
      <div className="bg-white border-b border-gray-200 p-3 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center space-x-2">
          <button
            onClick={() => goToPage(currentPage - 1)}
            disabled={currentPage <= 1}
            className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ←
          </button>
          <span className="text-sm text-gray-600">
            Page {currentPage} of {numPages}
          </span>
          <button
            onClick={() => goToPage(currentPage + 1)}
            disabled={currentPage >= numPages}
            className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            →
          </button>
        </div>

        <div className="flex items-center space-x-2">
          {/* Highlight Status Indicator */}
          {highlightInfo && highlightInfo.page === currentPage && (
            <div className="flex items-center space-x-2 px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs">
              <span className="w-2 h-2 bg-yellow-400 rounded-full"></span>
              <span>Text highlighted</span>
              <button
                onClick={clearHighlights}
                className="ml-1 text-yellow-600 hover:text-yellow-800"
                title="Clear highlights"
              >
                ✕
              </button>
            </div>
          )}
          
          <button
            onClick={zoomOut}
            disabled={scale <= 0.5}
            className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            −
          </button>
          <span className="text-sm text-gray-600 min-w-[60px] text-center">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={zoomIn}
            disabled={scale >= 3.0}
            className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            +
          </button>
          <button
            onClick={resetZoom}
            className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
          >
            Reset
          </button>
        </div>
      </div>

      {/* PDF Document */}
      <div className="flex-1 overflow-auto p-4">
        {isLoading && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
              <p className="text-gray-600">Loading PDF...</p>
            </div>
          </div>
        )}

        <div className="flex justify-center" ref={pageRef}>
          <Document
            file={fileUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading=""
            error=""
          >
            <Page
              pageNumber={currentPage}
              scale={scale}
              className={`shadow-lg ${highlightPage === currentPage ? 'ring-4 ring-yellow-400' : ''}`}
              loading={
                <div className="flex items-center justify-center h-96 bg-gray-100">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                </div>
              }
            />
          </Document>
        </div>
      </div>

      {/* Page Navigation Input */}
      <div className="bg-white border-t border-gray-200 p-3">
        <div className="flex items-center justify-center space-x-2">
          <label htmlFor="pageInput" className="text-sm text-gray-600">
            Go to page:
          </label>
          <input
            id="pageInput"
            type="number"
            min={1}
            max={numPages}
            value={currentPage}
            onChange={(e) => {
              const page = parseInt(e.target.value);
              if (!isNaN(page)) {
                goToPage(page);
              }
            }}
            className="w-16 px-2 py-1 border border-gray-300 rounded text-center text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>
    </div>
  );
};

export default PDFViewer;