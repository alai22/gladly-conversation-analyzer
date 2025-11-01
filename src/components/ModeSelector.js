import React, { useState, useEffect, useRef } from 'react';
import { Bot, Database, Search, MessageSquare, ChevronDown, Download, FileText } from 'lucide-react';

const ModeSelector = ({ currentMode, setCurrentMode }) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const modes = [
    {
      id: 'claude',
      name: 'Claude Chat',
      description: 'Direct Claude API interaction',
      icon: Bot,
      color: 'text-blue-600'
    },
    {
      id: 'conversations',
      name: 'Search Data',
      description: 'Search conversation data',
      icon: Search,
      color: 'text-green-600'
    },
    {
      id: 'ask',
      name: 'Ask Claude (RAG)',
      description: 'RAG-powered analysis of conversation data',
      icon: MessageSquare,
      color: 'text-purple-600'
    },
    {
      id: 'download',
      name: 'Download Manager',
      description: 'Download conversation data from Gladly',
      icon: Download,
      color: 'text-orange-600'
    },
    {
      id: 'survicate',
      name: 'Survicate Surveys',
      description: 'RAG-powered analysis of cancellation surveys',
      icon: FileText,
      color: 'text-teal-600'
    }
  ];

  const currentModeData = modes.find(mode => mode.id === currentMode);

  const handleModeChange = (modeId) => {
    setCurrentMode(modeId);
    setIsOpen(false);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-3 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors"
      >
        <div className="flex items-center space-x-2">
          {currentModeData && (
            <>
              <currentModeData.icon className={`h-5 w-5 ${currentModeData.color}`} />
              <div className="text-left">
                <div className="text-sm font-medium text-gray-900">
                  {currentModeData.name}
                </div>
                <div className="text-xs text-gray-500">
                  {currentModeData.description}
                </div>
              </div>
            </>
          )}
        </div>
        <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-80 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
          <div className="py-2">
            {modes.map((mode) => {
              const Icon = mode.icon;
              const isActive = currentMode === mode.id;
              
              return (
                <button
                  key={mode.id}
                  onClick={() => handleModeChange(mode.id)}
                  className={`w-full flex items-start space-x-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors ${
                    isActive ? 'bg-blue-50' : ''
                  }`}
                >
                  <Icon className={`h-5 w-5 mt-0.5 flex-shrink-0 ${mode.color}`} />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-900">{mode.name}</div>
                    <div className="text-xs text-gray-500 mt-0.5">{mode.description}</div>
                  </div>
                  {isActive && (
                    <div className="flex-shrink-0">
                      <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default ModeSelector;
