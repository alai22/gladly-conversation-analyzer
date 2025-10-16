import React from 'react';
import { Bot, Database, Search, MessageSquare, RefreshCw, CheckCircle, XCircle } from 'lucide-react';

const Sidebar = ({ currentMode, setCurrentMode, healthStatus, onRefreshHealth }) => {
  const modes = [
    {
      id: 'claude',
      name: 'Claude Chat',
      description: 'Direct Claude API interaction',
      icon: Bot,
      color: 'text-blue-600 bg-blue-50 hover:bg-blue-100'
    },
    {
      id: 'conversations',
      name: 'Search Data',
      description: 'Search conversation data',
      icon: Search,
      color: 'text-green-600 bg-green-50 hover:bg-green-100'
    },
    {
      id: 'ask',
      name: 'Ask Claude (RAG)',
      description: 'RAG-powered analysis of conversation data',
      icon: MessageSquare,
      color: 'text-purple-600 bg-purple-50 hover:bg-purple-100'
    }
  ];

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

      {/* Mode Selection */}
      <div className="flex-1 p-6">
        <h3 className="text-sm font-medium text-gray-900 mb-4">Modes</h3>
        <div className="space-y-2">
          {modes.map((mode) => {
            const Icon = mode.icon;
            const isActive = currentMode === mode.id;
            
            return (
              <button
                key={mode.id}
                onClick={() => setCurrentMode(mode.id)}
                className={`w-full flex items-start space-x-3 p-3 rounded-lg text-left transition-colors ${
                  isActive 
                    ? mode.color 
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                <Icon className="h-5 w-5 mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{mode.name}</div>
                  <div className="text-xs opacity-75 mt-0.5">{mode.description}</div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Footer */}
      <div className="p-6 border-t border-gray-200">
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
