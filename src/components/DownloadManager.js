import React, { useState, useEffect } from 'react';

const DownloadManager = () => {
  const [downloadStatus, setDownloadStatus] = useState(null);
  const [downloadStats, setDownloadStats] = useState(null);
  const [downloadHistory, setDownloadHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [batchSize, setBatchSize] = useState(500);
  const [maxDuration, setMaxDuration] = useState(30);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Fetch download status
  const fetchDownloadStatus = async () => {
    try {
      const response = await fetch('/api/download/status');
      const data = await response.json();
      if (data.status === 'success') {
        setDownloadStatus(data.data);
      }
    } catch (error) {
      console.error('Error fetching download status:', error);
    }
  };

  // Fetch download statistics
  const fetchDownloadStats = async () => {
    try {
      const response = await fetch('/api/download/stats');
      const data = await response.json();
      if (data.status === 'success') {
        setDownloadStats(data.data);
      }
    } catch (error) {
      console.error('Error fetching download stats:', error);
    }
  };

  // Fetch download history
  const fetchDownloadHistory = async () => {
    try {
      const response = await fetch('/api/download/history');
      const data = await response.json();
      if (data.status === 'success') {
        setDownloadHistory(data.data.conversations);
      }
    } catch (error) {
      console.error('Error fetching download history:', error);
    }
  };

  // Start download
  const startDownload = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/download/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          batch_size: batchSize,
          max_duration_minutes: maxDuration,
          start_date: startDate || null,
          end_date: endDate || null
        }),
      });
      
      const data = await response.json();
      if (data.status === 'success') {
        // Refresh data
        await Promise.all([
          fetchDownloadStatus(),
          fetchDownloadStats(),
          fetchDownloadHistory()
        ]);
      } else {
        alert(`Error: ${data.message}`);
      }
    } catch (error) {
      console.error('Error starting download:', error);
      alert('Error starting download');
    } finally {
      setIsLoading(false);
    }
  };

  // Stop download
  const stopDownload = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/download/stop', {
        method: 'POST',
      });
      
      const data = await response.json();
      if (data.status === 'success') {
        // Refresh data
        await Promise.all([
          fetchDownloadStatus(),
          fetchDownloadStats(),
          fetchDownloadHistory()
        ]);
      } else {
        alert(`Error: ${data.message}`);
      }
    } catch (error) {
      console.error('Error stopping download:', error);
      alert('Error stopping download');
    } finally {
      setIsLoading(false);
    }
  };

  // Auto-refresh when download is running
  useEffect(() => {
    const interval = setInterval(() => {
      if (downloadStatus?.is_running) {
        fetchDownloadStatus();
      }
    }, 2000); // Refresh every 2 seconds when running

    return () => clearInterval(interval);
  }, [downloadStatus?.is_running]);

  // Initial data fetch
  useEffect(() => {
    fetchDownloadStatus();
    fetchDownloadStats();
    fetchDownloadHistory();
  }, []);

  const formatTime = (seconds) => {
    if (!seconds) return '0s';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  };

  const formatFileSize = (sizeMB) => {
    if (sizeMB < 1) {
      return `${(sizeMB * 1024).toFixed(0)} KB`;
    } else {
      return `${sizeMB.toFixed(1)} MB`;
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h1 className="text-2xl font-bold text-gray-900">Gladly Download Manager</h1>
          <p className="text-gray-600 mt-1">Download and manage conversation data from Gladly API</p>
        </div>

        <div className="p-6">
          {/* Download Statistics */}
          {downloadStats && (
            <div className="mb-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Overall Progress</h2>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">{downloadStats.total_downloaded.toLocaleString()}</div>
                  <div className="text-sm text-gray-600">Downloaded</div>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">{downloadStats.total_in_csv.toLocaleString()}</div>
                  <div className="text-sm text-gray-600">Total in CSV</div>
                </div>
                <div className="bg-yellow-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-yellow-600">{downloadStats.remaining.toLocaleString()}</div>
                  <div className="text-sm text-gray-600">Remaining</div>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">{downloadStats.completion_percentage.toFixed(1)}%</div>
                  <div className="text-sm text-gray-600">Complete</div>
                </div>
              </div>
              
              <div className="mt-4">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${downloadStats.completion_percentage}%` }}
                  ></div>
                  </div>
                </div>
              </div>
            )}

          {/* Download Controls */}
          <div className="mb-8">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Download Controls</h2>
            
            {downloadStatus?.is_running ? (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-yellow-800">Download in Progress</h3>
                    <p className="text-yellow-700">
                      {downloadStatus.current_batch} / {downloadStatus.total_batches} conversations
                      ({downloadStatus.progress_percentage.toFixed(1)}%)
                    </p>
                    <p className="text-yellow-700">
                      Downloaded: {downloadStatus.downloaded_count} | Failed: {downloadStatus.failed_count}
                    </p>
                    {downloadStatus.elapsed_time && (
                      <p className="text-yellow-700">
                        Elapsed: {formatTime(downloadStatus.elapsed_time)}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={stopDownload}
                    disabled={isLoading}
                    className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg disabled:opacity-50"
                  >
                    {isLoading ? 'Stopping...' : 'Stop Download'}
                  </button>
                </div>
                
                {/* Progress bar */}
                <div className="mt-4">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-yellow-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${downloadStatus.progress_percentage}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Batch Size
                    </label>
                    <select
                      value={batchSize}
                      onChange={(e) => setBatchSize(parseInt(e.target.value))}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    >
                      <option value={100}>100 conversations (~0.2 min)</option>
                      <option value={500}>500 conversations (~1.2 min)</option>
                      <option value={1000}>1000 conversations (~2.5 min)</option>
                      <option value={2000}>2000 conversations (~5 min)</option>
                      <option value={5000}>5000 conversations (~12 min)</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Start Date (Optional)
                    </label>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2"
                      placeholder="YYYY-MM-DD"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      End Date (Optional)
                    </label>
                    <input
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2"
                      placeholder="YYYY-MM-DD"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Max Duration (minutes)
                    </label>
                    <input
                      type="number"
                      value={maxDuration}
                      onChange={(e) => setMaxDuration(parseInt(e.target.value))}
                      min="1"
                      max="120"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    />
                  </div>
                  
                  <div className="flex items-end">
                    <button
                      onClick={startDownload}
                      disabled={isLoading}
                      className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg disabled:opacity-50"
                    >
                      {isLoading ? 'Starting...' : 'Start Download'}
                    </button>
                  </div>
                </div>
                
                {/* Date Filter Help */}
                {(startDate || endDate) && (
                  <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-start">
                      <div className="flex-shrink-0">
                        <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <div className="ml-3">
                        <h3 className="text-sm font-medium text-blue-800">Date Range Filter Active</h3>
                        <div className="mt-1 text-sm text-blue-700">
                          <p>Only conversations from <strong>{startDate || 'beginning'}</strong> to <strong>{endDate || 'end'}</strong> will be downloaded.</p>
                          <p className="mt-1">Leave dates empty to download all conversations.</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                
                {downloadStatus?.error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3 mt-4">
                    <p className="text-red-800">Error: {downloadStatus.error}</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Download History */}
          <div>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Download History</h2>
            {downloadHistory.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Conversation ID
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Conversation Date
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Channel
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Agent
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Topics
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Downloaded At
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {downloadHistory.map((conversation, index) => (
                      <tr key={conversation.conversation_id || index}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          <span className="font-mono text-xs">{conversation.conversation_id}</span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {conversation.conversation_date}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                            conversation.channel === 'EMAIL' ? 'bg-blue-100 text-blue-800' :
                            conversation.channel === 'CHAT' ? 'bg-green-100 text-green-800' :
                            conversation.channel === 'PHONE' ? 'bg-purple-100 text-purple-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {conversation.channel || 'Unknown'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {conversation.agent || 'Unknown'}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-500 max-w-xs">
                          <div className="truncate" title={conversation.topics}>
                            {conversation.topics || 'No topics'}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {new Date(conversation.download_timestamp).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                
                {/* Pagination */}
                {downloadStats && downloadStats.total_downloaded > 100 && (
                  <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
                    <div className="flex-1 flex justify-between sm:hidden">
                      <button className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                        Previous
                      </button>
                      <button className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                        Next
                      </button>
                    </div>
                    <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                      <div>
                        <p className="text-sm text-gray-700">
                          Showing <span className="font-medium">1</span> to <span className="font-medium">100</span> of{' '}
                          <span className="font-medium">{downloadStats.total_downloaded.toLocaleString()}</span> conversations
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                No conversations downloaded yet
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DownloadManager;
