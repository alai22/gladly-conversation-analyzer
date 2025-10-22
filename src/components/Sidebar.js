import React from 'react';
import { Database, RefreshCw, CheckCircle, XCircle } from 'lucide-react';

const Sidebar = ({ healthStatus, onRefreshHealth }) => {
  const getHealthStatusIcon = () => {
    if (!healthStatus) return <RefreshCw className="h-4 w-4 animate-spin" />;
    if (healthStatus.status === 'healthy') return <CheckCircle className="h-4 w-4 text-green-500" />;
    return <XCircle className="h-4 w-4 text-red-500" />;
  };

  const getHealthStatusText = () => {
    if (!healthStatus) return 'Checking...';
    if (healthStatus.status === 'healthy') return 'Connected';
    return 'Disconnected';
  };

  const getHealthStatusColor = () => {
    if (!healthStatus) return 'text-gray-500';
    if (healthStatus.status === 'healthy') return 'text-green-600';
    return 'text-red-600';
  };

  return (
    <div className="w-64 bg-white shadow-lg border-r border-gray-200 flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center space-x-3 mb-4">
          <Database className="h-8 w-8 text-blue-600" />
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Gladly Tester</h2>
            <p className="text-sm text-gray-500">Conversation Analysis</p>
          </div>
        </div>
        
        {/* Health Status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {getHealthStatusIcon()}
            <span className={`text-sm font-medium ${getHealthStatusColor()}`}>
              {getHealthStatusText()}
            </span>
          </div>
          <button
            onClick={onRefreshHealth}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            title="Refresh connection"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-auto p-6 border-t border-gray-200">
        <div className="text-xs text-gray-500">
          <div className="mb-2">
            <strong>Backend Status:</strong>
          </div>
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${
                healthStatus?.claude_initialized ? 'bg-green-400' : 'bg-red-400'
              }`} />
              <span>Claude API</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${
                healthStatus?.conversation_analyzer_initialized ? 'bg-green-400' : 'bg-red-400'
              }`} />
              <span>Data Analyzer</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
