import React, { useState } from 'react';
import { X, Bot, Settings as SettingsIcon, Download, TrendingUp, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';
import axios from 'axios';

const SettingsPanel = ({ settings, setSettings, adminMode, setAdminMode, setCurrentMode, onClose }) => {
  const handleChange = (key, value) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const models = [
    // Claude 4 models (non-dated aliases - recommended for robustness)
    'claude-sonnet-4',
    'claude-opus-4',
    // Claude 3 models (dated snapshots)
    'claude-3-sonnet-20240229',
    'claude-3-opus-20240229',
    'claude-3-haiku-20240307',
    // Legacy Claude 3.5 models (will be aliased by backend)
    'claude-3-5-sonnet',
    'claude-3-5-sonnet-20241022',
    'claude-3-5-haiku-20241022'
  ];

  const [topicExtractionStatus, setTopicExtractionStatus] = useState({
    isRunning: false,
    progress: null,
    error: null,
    success: null
  });
  const [extractStartDate, setExtractStartDate] = useState('2025-10-20');
  const [extractEndDate, setExtractEndDate] = useState('2025-10-20');

  const handleExtractTopics = async () => {
    const startTime = Date.now();
    let progressInterval = null;
    const startDate = extractStartDate;
    const endDate = extractEndDate;
    
    // Validate date range
    if (!startDate || !endDate) {
      setTopicExtractionStatus({
        isRunning: false,
        progress: null,
        error: 'Please select both start and end dates',
        success: null
      });
      return;
    }
    
    if (startDate > endDate) {
      setTopicExtractionStatus({
        isRunning: false,
        progress: null,
        error: 'Start date must be before or equal to end date',
        success: null
      });
      return;
    }
    
    // Log start
    const getTimestamp = () => new Date().toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit'
    });
    
    const dateRangeStr = startDate === endDate ? startDate : `${startDate} to ${endDate}`;
    console.log(`[${getTimestamp()}] [TOPIC EXTRACTION] Starting topic extraction for ${dateRangeStr}...`);
    
    setTopicExtractionStatus({
      isRunning: true,
      progress: 'Starting topic extraction... This may take several minutes for large batches. Progress is saved incrementally every 10 conversations.',
      error: null,
      success: null
    });

    // Get conversation count first for accurate progress tracking
    let totalConversations = 0;
    try {
      const countResponse = await axios.get(`/api/conversations/conversation-count?start_date=${startDate}&end_date=${endDate}`);
      if (countResponse.data.success) {
        totalConversations = countResponse.data.count || 0;
        const estimatedBatches = Math.ceil(totalConversations / 10);
        const estimatedMinutes = Math.ceil((totalConversations * 0.5) / 60);
        console.log(`[${getTimestamp()}] [TOPIC EXTRACTION] Found ${totalConversations} conversations (${estimatedBatches} batches of 10)`);
        console.log(`[${getTimestamp()}] [TOPIC EXTRACTION] Estimated time: ~${estimatedMinutes} minutes`);
      }
    } catch (e) {
      console.warn(`[${getTimestamp()}] [TOPIC EXTRACTION] Could not get conversation count, will estimate progress`);
    }

    // Set up progress logging interval (logs every 10 seconds, matching backend's 10-conversation batches)
    // Backend processes ~1 conversation per second (0.5s delay + API time), so every 10 seconds = ~10 conversations
    let lastLoggedBatch = 0;
    progressInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      const minutes = Math.floor(elapsed / 60);
      const seconds = elapsed % 60;
      const timeStr = `${minutes}m ${seconds}s`;
      
      // Estimate: ~1 conversation per second (0.5s delay + ~0.5s API call)
      // Every 10 seconds = ~10 conversations processed (matching backend's batch logging)
      const estimatedBatch = Math.floor(elapsed / 10); // Every 10 seconds = 1 batch of 10
      const estimatedProcessed = estimatedBatch * 10;
      
      if (estimatedBatch > lastLoggedBatch) {
        lastLoggedBatch = estimatedBatch;
        if (totalConversations > 0) {
          const estimatedPercent = Math.min(100, Math.floor((estimatedProcessed / totalConversations) * 100));
          console.log(`[${getTimestamp()}] [TOPIC EXTRACTION PROGRESS] Batch ${estimatedBatch}: ~${estimatedProcessed}/${totalConversations} conversations (~${estimatedPercent}%) - Elapsed: ${timeStr}`);
        } else {
          console.log(`[${getTimestamp()}] [TOPIC EXTRACTION PROGRESS] Batch ${estimatedBatch}: ~${estimatedProcessed} conversations processed - Elapsed: ${timeStr}`);
        }
      }
    }, 10000); // Check every 10 seconds (matches backend's 10-conversation batch interval)

    try {
      // Start extraction (returns immediately, runs in background)
      const response = await axios.post('/api/conversations/extract-topics', {
        start_date: startDate,
        end_date: endDate
      }, {
        timeout: 10000 // 10 second timeout for starting the job
      });

      // Clear progress interval
      if (progressInterval) {
        clearInterval(progressInterval);
      }

      if (!response.data.success) {
        setTopicExtractionStatus({
          isRunning: false,
          progress: null,
          error: response.data.error || response.data.message || 'Failed to start extraction',
          success: null
        });
        return;
      }

      // Poll for status
      const statusInterval = setInterval(async () => {
        try {
          const statusResponse = await axios.get('/api/conversations/extract-topics-status');
          if (statusResponse.data.success) {
            const status = statusResponse.data;
            
            if (status.is_running) {
              const progressMsg = `Processing: ${status.current}/${status.total} conversations (${status.progress_percentage.toFixed(1)}%)`;
              const details = [];
              if (status.processed_count > 0) details.push(`${status.processed_count} processed`);
              if (status.skipped_count > 0) details.push(`${status.skipped_count} skipped`);
              const detailsMsg = details.length > 0 ? ` (${details.join(', ')})` : '';
              
              setTopicExtractionStatus({
                isRunning: true,
                progress: progressMsg + detailsMsg,
                error: null,
                success: null
              });
              
              // Log progress every 10 conversations
              if (status.current % 10 === 0 || status.current === status.total) {
                const elapsed = status.elapsed_time ? Math.floor(status.elapsed_time) : 0;
                const minutes = Math.floor(elapsed / 60);
                const seconds = elapsed % 60;
                console.log(`[${getTimestamp()}] [TOPIC EXTRACTION PROGRESS] ${status.current}/${status.total} (${status.progress_percentage.toFixed(1)}%) - Elapsed: ${minutes}m ${seconds}s`);
              }
            } else {
              // Completed
              clearInterval(statusInterval);
              const elapsed = status.elapsed_time ? Math.floor(status.elapsed_time) : 0;
              const minutes = Math.floor(elapsed / 60);
              const seconds = elapsed % 60;
              const elapsedTimeStr = `${minutes}m ${seconds}s`;
              
              if (status.error) {
                console.error(`[${getTimestamp()}] [TOPIC EXTRACTION] ❌ Failed: ${status.error}`);
                setTopicExtractionStatus({
                  isRunning: false,
                  progress: null,
                  error: status.error,
                  success: null
                });
              } else {
                let successMsg = `Successfully extracted topics for ${status.processed_count || 0} conversations`;
                if (status.skipped_count > 0) {
                  successMsg += `. Skipped ${status.skipped_count} already-extracted conversations.`;
                }
                
                console.log(`[${getTimestamp()}] [TOPIC EXTRACTION] ✅ Completed!`);
                console.log(`[${getTimestamp()}] [TOPIC EXTRACTION] Processed: ${status.processed_count}, Skipped: ${status.skipped_count}`);
                console.log(`[${getTimestamp()}] [TOPIC EXTRACTION] Time elapsed: ${elapsedTimeStr}`);
                
                setTopicExtractionStatus({
                  isRunning: false,
                  progress: null,
                  error: null,
                  success: successMsg
                });
              }
            }
          }
        } catch (statusErr) {
          console.error('Error polling extraction status:', statusErr);
        }
      }, 2000); // Poll every 2 seconds
    } catch (err) {
      // Clear progress interval
      if (progressInterval) {
        clearInterval(progressInterval);
      }
      
      let errorMessage = 'Failed to start extraction';
      let errorDetails = '';
      
      if (err.response) {
        const status = err.response.status;
        const data = err.response.data || {};
        
        if (status === 400 && data.error === 'Extraction already running') {
          errorMessage = 'Extraction Already Running';
          errorDetails = 'Topic extraction is already in progress. Please wait for it to complete.';
        } else {
          errorMessage = data.error || `Server error (${status})`;
          errorDetails = data.details || data.message || err.message;
        }
      } else {
        errorDetails = err.message || 'Unable to connect to server. Please check your connection.';
      }
      
      const timestamp = getTimestamp();
      console.error(`[${timestamp}] [TOPIC EXTRACTION] ❌ Failed to start: ${errorMessage}`);
      
      setTopicExtractionStatus({
        isRunning: false,
        progress: null,
        error: `${errorMessage}: ${errorDetails}`,
        success: null
      });
    }
  };

  return (
    <div className="bg-white border-b border-gray-200 p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <SettingsIcon className="h-6 w-6 text-gray-600" />
            <h2 className="text-lg font-semibold text-gray-900">Settings</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Admin Tools Section - Moved to Top */}
        <div className="mb-8 pb-8 border-b border-gray-200">
          <h3 className="text-sm font-medium text-gray-900 mb-4">Admin Tools</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Claude Chat */}
            <button
              onClick={() => {
                setAdminMode(adminMode === 'claude' ? null : 'claude');
                setCurrentMode('ask'); // Reset to a regular mode
                onClose();
              }}
              className={`p-4 border-2 rounded-lg text-left transition-all ${
                adminMode === 'claude'
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center space-x-3 mb-2">
                <Bot className={`h-5 w-5 ${adminMode === 'claude' ? 'text-blue-600' : 'text-gray-600'}`} />
                <h4 className={`font-medium ${adminMode === 'claude' ? 'text-blue-900' : 'text-gray-900'}`}>
                  Claude Chat
                </h4>
              </div>
              <p className="text-xs text-gray-600">
                Direct Claude API interaction (no RAG)
              </p>
              {adminMode === 'claude' && (
                <p className="text-xs text-blue-600 mt-2 font-medium">Active</p>
              )}
            </button>

            {/* Download Manager */}
            <button
              onClick={() => {
                setAdminMode(adminMode === 'download' ? null : 'download');
                setCurrentMode('ask'); // Reset to a regular mode
                onClose();
              }}
              className={`p-4 border-2 rounded-lg text-left transition-all ${
                adminMode === 'download'
                  ? 'border-orange-500 bg-orange-50'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center space-x-3 mb-2">
                <Download className={`h-5 w-5 ${adminMode === 'download' ? 'text-orange-600' : 'text-gray-600'}`} />
                <h4 className={`font-medium ${adminMode === 'download' ? 'text-orange-900' : 'text-gray-900'}`}>
                  Download Manager
                </h4>
              </div>
              <p className="text-xs text-gray-600">
                Download conversation data from Gladly
              </p>
              {adminMode === 'download' && (
                <p className="text-xs text-orange-600 mt-2 font-medium">Active</p>
              )}
            </button>

            {/* Extract Conversation Topics */}
            <div className="md:col-span-2">
              <div className={`p-4 border-2 rounded-lg ${
                topicExtractionStatus.isRunning
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 bg-gray-50'
              }`}>
                <div className="flex items-center space-x-3 mb-2">
                  <TrendingUp className="h-5 w-5 text-gray-600" />
                  <h4 className="font-medium text-gray-900">
                    Extract Conversation Topics
                  </h4>
                </div>
                <p className="text-xs text-gray-600 mb-3">
                  Pre-process conversations to extract topics for trend analysis. This uses Claude AI to analyze conversation transcripts.
                </p>
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Start Date</label>
                    <input
                      type="date"
                      value={extractStartDate}
                      onChange={(e) => setExtractStartDate(e.target.value)}
                      disabled={topicExtractionStatus.isRunning}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">End Date</label>
                    <input
                      type="date"
                      value={extractEndDate}
                      onChange={(e) => setExtractEndDate(e.target.value)}
                      disabled={topicExtractionStatus.isRunning}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                    />
                  </div>
                </div>
                <button
                  onClick={handleExtractTopics}
                  disabled={topicExtractionStatus.isRunning}
                  className={`px-4 py-2 text-sm rounded-lg transition-colors flex items-center space-x-2 ${
                    topicExtractionStatus.isRunning
                      ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                  }`}
                >
                  {topicExtractionStatus.isRunning ? (
                    <>
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      <span>Processing...</span>
                    </>
                  ) : (
                    <>
                      <TrendingUp className="h-4 w-4" />
                      <span>Extract Topics</span>
                    </>
                  )}
                </button>
                {topicExtractionStatus.progress && (
                  <p className="text-xs text-blue-600 mt-2">{topicExtractionStatus.progress}</p>
                )}
                {topicExtractionStatus.error && (
                  <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded">
                    <div className="flex items-start space-x-2">
                      <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-red-900 mb-1">Error</p>
                        <p className="text-xs text-red-700 whitespace-pre-wrap">{topicExtractionStatus.error}</p>
                      </div>
                    </div>
                  </div>
                )}
                {topicExtractionStatus.success && (
                  <div className="mt-2 flex items-start space-x-2">
                    <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-green-600">{topicExtractionStatus.success}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-4">
            Admin tools are for advanced users and system administration.
          </p>
        </div>

        {/* Claude Model Settings */}
        <div className="mt-6">
          <h3 className="text-sm font-medium text-gray-900 mb-4">Claude Model Settings</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Model Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Claude Model
            </label>
            <select
              value={settings.model}
              onChange={(e) => handleChange('model', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              {models.map(model => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Choose the Claude model for your requests
            </p>
          </div>

          {/* Max Tokens */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max Tokens
            </label>
            <input
              type="number"
              value={settings.maxTokens}
              onChange={(e) => handleChange('maxTokens', parseInt(e.target.value))}
              min="100"
              max="4000"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              Maximum tokens in Claude's response (100-4000)
            </p>
          </div>

          {/* System Prompt */}
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              System Prompt (Optional)
            </label>
            <textarea
              value={settings.systemPrompt}
              onChange={(e) => handleChange('systemPrompt', e.target.value)}
              placeholder="Enter a system prompt to guide Claude's behavior..."
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            />
            <p className="text-xs text-gray-500 mt-1">
              Optional system prompt to set Claude's behavior and context
            </p>
          </div>

          {/* Stream Option */}
          <div className="md:col-span-2">
            <div className="flex items-center space-x-3">
              <input
                type="checkbox"
                id="stream"
                checked={settings.stream}
                onChange={(e) => handleChange('stream', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="stream" className="text-sm font-medium text-gray-700">
                Enable Streaming
              </label>
            </div>
            <p className="text-xs text-gray-500 mt-1 ml-7">
              Stream responses for real-time output (experimental)
            </p>
          </div>
          </div>
        </div>

        {/* Current Settings Summary */}
        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <h3 className="text-sm font-medium text-gray-900 mb-2">Current Configuration</h3>
          <div className="text-xs text-gray-600 space-y-1">
            <div><strong>Model:</strong> {settings.model}</div>
            <div><strong>Max Tokens:</strong> {settings.maxTokens}</div>
            <div><strong>System Prompt:</strong> {settings.systemPrompt ? 'Set' : 'Not set'}</div>
            <div><strong>Streaming:</strong> {settings.stream ? 'Enabled' : 'Disabled'}</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;

