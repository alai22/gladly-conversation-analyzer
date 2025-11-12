import React from 'react';
import { X, Bot, Settings as SettingsIcon, Download } from 'lucide-react';

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

        {/* Admin Tools Section */}
        <div className="mt-8 pt-8 border-t border-gray-200">
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
          </div>
          <p className="text-xs text-gray-500 mt-4">
            Admin tools are for advanced users and system administration. Click to activate.
          </p>
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;

