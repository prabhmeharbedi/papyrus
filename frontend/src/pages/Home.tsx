import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

const Home: React.FC = () => {
  const [apiStatus, setApiStatus] = useState<'loading' | 'connected' | 'error'>('loading');
  const [ragflowStatus, setRagflowStatus] = useState<'loading' | 'connected' | 'error'>('loading');

  useEffect(() => {
    // Test API connection
    fetch('http://localhost:8000/health')
      .then(response => response.json())
      .then(() => setApiStatus('connected'))
      .catch(() => setApiStatus('error'));

    // Test RAGFlow connection
    fetch('http://localhost:8000/api/ragflow/test')
      .then(response => response.json())
      .then(data => {
        if (data.status === 'connected') {
          setRagflowStatus('connected');
        } else {
          setRagflowStatus('error');
        }
      })
      .catch(() => setRagflowStatus('error'));
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'text-green-600';
      case 'error': return 'text-red-600';
      default: return 'text-yellow-600';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'connected': return 'Connected';
      case 'error': return 'Error';
      default: return 'Checking...';
    }
  };

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="border-4 border-dashed border-gray-200 rounded-lg p-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Welcome to PDF Chat App
          </h1>
          <p className="text-lg text-gray-600 mb-8">
            Transform your PDFs into interactive conversations with AI-powered insights
          </p>
          
          {/* System Status */}
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">System Status</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <span className="font-medium text-gray-700">API Backend</span>
                <span className={`font-semibold ${getStatusColor(apiStatus)}`}>
                  {getStatusText(apiStatus)}
                </span>
              </div>
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <span className="font-medium text-gray-700">RAGFlow Integration</span>
                <span className={`font-semibold ${getStatusColor(ragflowStatus)}`}>
                  {getStatusText(ragflowStatus)}
                </span>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Link
              to="/documents"
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 px-6 rounded-lg transition duration-200"
            >
              Upload Documents
            </Link>
            <Link
              to="/chat"
              className="bg-green-600 hover:bg-green-700 text-white font-bold py-4 px-6 rounded-lg transition duration-200"
            >
              Start Chatting
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;