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

  const handleExtractTopics = async () => {
    setTopicExtractionStatus({
      isRunning: true,
      progress: 'Starting topic extraction... This may take several minutes for large batches. Progress is saved incrementally every 10 conversations.',
      error: null,
      success: null
    });

    try {
      // For prototype, extract topics for Oct 20, 2025
      // In future, this could accept date range parameters
      const response = await axios.post('/api/conversations/extract-topics', {
        date: '2025-10-20'
      }, {
        timeout: 1800000 // 30 minute timeout for very large batches (allows ~3600 conversations at 0.5s delay)
      });

      if (response.data.success) {
        setTopicExtractionStatus({
          isRunning: false,
          progress: null,
          error: null,
          success: `Successfully extracted topics for ${response.data.processed_count || 0} conversations`
        });
      } else {
        const errorDetails = response.data.details || response.data.message || response.data.error || 'Failed to extract topics';
        setTopicExtractionStatus({
          isRunning: false,
          progress: null,
          error: errorDetails,
          success: null
        });
      }
    } catch (err) {
      let errorMessage = 'Failed to extract topics';
      let errorDetails = '';
      
      if (err.response) {
        // Server responded with error status
        const status = err.response.status;
        const data = err.response.data || {};
        
        if (status === 429) {
          errorMessage = 'Rate Limit Exceeded';
          errorDetails = data.details || data.message || 'Claude API rate limit reached. Please wait 1-2 minutes and try again.';
        } else if (status === 504) {
          errorMessage = 'Request Timeout';
          const partialCount = data.partial_count || 0;
          const partialMsg = partialCount > 0 ? ` ${partialCount} conversations were processed and saved before the timeout.` : '';
          errorDetails = (data.details || data.message || 'The request took too long. This can happen with large batches.') + partialMsg;
        } else {
          errorMessage = data.error || `Server error (${status})`;
          errorDetails = data.details || data.message || err.message;
        }
      } else if (err.request) {
        // Request made but no response
        if (err.code === 'ECONNABORTED') {
          errorMessage = 'Request Timeout';
          errorDetails = 'The request took too long to complete (30 minute limit). This can happen with very large batches. Progress is saved incrementally every 10 conversations - check the Conversation Trends tab to see what was extracted. You can try again later.';
        } else {
          errorMessage = 'Network Error';
          errorDetails = err.message || 'Unable to connect to server. Please check your connection.';
        }
      } else {
        errorMessage = 'Error';
        errorDetails = err.message || 'An unexpected error occurred';
      }
      
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
                      <span>Extract Topics for Oct 20, 2025</span>
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

