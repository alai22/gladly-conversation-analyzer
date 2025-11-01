import React, { useState, useEffect } from 'react';
import { Send, Bot, User, Settings, Database, MessageSquare, Search, Download } from 'lucide-react';
import PromptInput from './components/PromptInput';
import ConversationDisplay from './components/ConversationDisplay';
import Sidebar from './components/Sidebar';
import SettingsPanel from './components/SettingsPanel';
import Login from './components/Login';
import ModeSelector from './components/ModeSelector';
import DownloadManager from './components/DownloadManager';
import axios from 'axios';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [conversations, setConversations] = useState({
    claude: [],
    conversations: [],
    ask: [],
    download: [],
    survicate: []
  });
  const [currentMode, setCurrentMode] = useState('ask'); // 'claude', 'conversations', 'ask', 'download', 'survicate'
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState({
    model: 'claude-sonnet-4',  // Default to Sonnet 4 (non-dated alias)
    maxTokens: 1000,
    systemPrompt: '',
    stream: false
  });
  const [healthStatus, setHealthStatus] = useState(null);

  // Load conversations and settings from localStorage on mount
  useEffect(() => {
    try {
      const savedConversations = localStorage.getItem('gladly_conversations');
      if (savedConversations) {
        const parsed = JSON.parse(savedConversations);
        setConversations(prev => ({
          ...prev,
          ...parsed
        }));
      }
    } catch (error) {
      console.error('Error loading conversations from localStorage:', error);
    }

    try {
      const savedSettings = localStorage.getItem('gladly_settings');
      if (savedSettings) {
        const parsed = JSON.parse(savedSettings);
        setSettings(prev => ({
          ...prev,
          ...parsed
        }));
      }
    } catch (error) {
      console.error('Error loading settings from localStorage:', error);
    }

    const savedMode = localStorage.getItem('gladly_current_mode');
    if (savedMode) {
      setCurrentMode(savedMode);
    }
  }, []);

  // Save conversations to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem('gladly_conversations', JSON.stringify(conversations));
    } catch (error) {
      console.error('Error saving conversations to localStorage:', error);
    }
  }, [conversations]);

  // Save settings to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem('gladly_settings', JSON.stringify(settings));
    } catch (error) {
      console.error('Error saving settings to localStorage:', error);
    }
  }, [settings]);

  // Save current mode to localStorage whenever it changes
  useEffect(() => {
    try {
      localStorage.setItem('gladly_current_mode', currentMode);
    } catch (error) {
      console.error('Error saving current mode to localStorage:', error);
    }
  }, [currentMode]);

  // Check if user is already authenticated (from sessionStorage)
  useEffect(() => {
    const authenticated = sessionStorage.getItem('authenticated');
    if (authenticated === 'true') {
      setIsAuthenticated(true);
    }
  }, []);

  // Check backend health on component mount (only when authenticated)
  useEffect(() => {
    if (isAuthenticated) {
      checkHealth();
    }
  }, [isAuthenticated]);

  const handleLogin = () => {
    setIsAuthenticated(true);
    sessionStorage.setItem('authenticated', 'true');
  };

  const checkHealth = async () => {
    try {
      const response = await axios.get('/api/health');
      setHealthStatus(response.data);
    } catch (error) {
      setHealthStatus({ status: 'unhealthy', error: error.message });
    }
  };

  // If not authenticated, show login screen
  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />;
  }

  const addConversation = (type, userMessage, response, metadata = {}) => {
    const newConversation = {
      id: Date.now(),
      type,
      timestamp: new Date().toISOString(),
      userMessage,
      response,
      metadata
    };
    setConversations(prev => ({
      ...prev,
      [currentMode]: [...prev[currentMode], newConversation]
    }));
  };

  // Get current mode's conversations
  const getCurrentConversations = () => {
    return conversations[currentMode] || [];
  };

  const handleClaudeMessage = async (message) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await axios.post('/api/claude/chat', {
        message,
        model: settings.model,
        max_tokens: settings.maxTokens,
        system_prompt: settings.systemPrompt || undefined,
        stream: settings.stream
      });

      if (response.data.success) {
        let responseText = '';
        if (response.data.streamed) {
          // Process streamed response
          for (const chunk of response.data.response) {
            if (chunk.content && chunk.content.length > 0) {
              for (const contentBlock of chunk.content) {
                if (contentBlock.type === 'text') {
                  responseText += contentBlock.text;
                }
              }
            }
          }
        } else {
          // Process regular response
          if (response.data.response.content && response.data.response.content.length > 0) {
            for (const contentBlock of response.data.response.content) {
              if (contentBlock.type === 'text') {
                responseText += contentBlock.text;
              }
            }
          }
        }

        addConversation('claude', message, responseText, {
          model: settings.model,
          tokens: response.data.response.usage?.output_tokens || 0
        });
      } else {
        throw new Error(response.data.error || 'Unknown error');
      }
    } catch (error) {
      setError(error.response?.data?.error || error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConversationSearch = async (query) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await axios.post('/api/conversations/search', {
        query,
        limit: 10
      });

      if (response.data.success) {
        const results = response.data.results;
        const formattedResults = results.map((item, index) => {
          const content = item.content || {};
          return `**Result ${index + 1}**\n` +
                 `Type: ${content.type || 'Unknown'}\n` +
                 `Timestamp: ${item.timestamp || 'Unknown'}\n` +
                 `Customer: ${item.customerId || 'Unknown'}\n` +
                 `Content: ${content.content || content.subject || content.body || 'No content'}\n`;
        }).join('\n---\n');

        addConversation('search', query, formattedResults, {
          resultCount: results.length
        });
      } else {
        throw new Error(response.data.error || 'Unknown error');
      }
    } catch (error) {
      const errorMessage = error.response?.data?.error || error.message;
      const errorDetails = error.response?.data?.details;
      setError(errorDetails ? `${errorMessage}\n\n${errorDetails}` : errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConversationAsk = async (question) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await axios.post('/api/conversations/ask', {
        question,
        model: settings.model,
        max_tokens: settings.maxTokens
      }, {
        timeout: 120000 // 2 minutes timeout for RAG requests
      });

      if (response.data.success) {
        let responseText = '';
        if (response.data.response.content && response.data.response.content.length > 0) {
          for (const contentBlock of response.data.response.content) {
            if (contentBlock.type === 'text') {
              responseText += contentBlock.text;
            }
          }
        }

        addConversation('ask', question, responseText, {
          dataRetrieved: response.data.data_retrieved,
          plan: response.data.plan,
          ragProcess: response.data.rag_process,
          tokensUsed: response.data.response.usage?.output_tokens || 0,
          model: settings.model
        });
      } else {
        throw new Error(response.data.error || 'Unknown error');
      }
    } catch (error) {
      const errorMessage = error.response?.data?.error || error.message;
      const errorDetails = error.response?.data?.details;
      setError(errorDetails ? `${errorMessage}\n\n${errorDetails}` : errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSurvicateAsk = async (question) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await axios.post('/api/survicate/ask', {
        question,
        model: settings.model,
        max_tokens: settings.maxTokens
      }, {
        timeout: 120000 // 2 minutes timeout for RAG requests
      });

      if (response.data.success) {
        let responseText = '';
        if (response.data.response.content && response.data.response.content.length > 0) {
          for (const contentBlock of response.data.response.content) {
            if (contentBlock.type === 'text') {
              responseText += contentBlock.text;
            }
          }
        }

        addConversation('survicate', question, responseText, {
          dataRetrieved: response.data.data_retrieved,
          plan: response.data.plan,
          ragProcess: response.data.rag_process,
          tokensUsed: response.data.response.usage?.output_tokens || 0,
          model: settings.model
        });
      } else {
        throw new Error(response.data.error || 'Unknown error');
      }
    } catch (error) {
      const errorMessage = error.response?.data?.error || error.message;
      const errorDetails = error.response?.data?.details;
      setError(errorDetails ? `${errorMessage}\n\n${errorDetails}` : errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = (message) => {
    if (!message.trim()) return;

    switch (currentMode) {
      case 'claude':
        handleClaudeMessage(message);
        break;
      case 'conversations':
        handleConversationSearch(message);
        break;
      case 'ask':
        handleConversationAsk(message);
        break;
      case 'survicate':
        handleSurvicateAsk(message);
        break;
      default:
        handleClaudeMessage(message);
    }
  };

  // Clear conversations for the current mode only
  const clearCurrentConversations = () => {
    setConversations(prev => ({
      ...prev,
      [currentMode]: []
    }));
    setError(null);
  };

  // Clear all conversations across all modes
  const clearAllConversations = () => {
    setConversations({
      claude: [],
      conversations: [],
      ask: [],
      download: [],
      survicate: []
    });
    setError(null);
  };

  const getCurrentConversationCount = () => {
    return getCurrentConversations().length;
  };

  const getModeTitle = () => {
    const modeTitles = {
      'claude': 'Claude Chat',
      'conversations': 'Search Data', 
      'ask': 'Ask Claude (RAG)',
      'download': 'Download Manager',
      'survicate': 'Survicate Surveys'
    };
    return modeTitles[currentMode] || 'Unknown Mode';
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <Sidebar 
        healthStatus={healthStatus}
        onRefreshHealth={checkHealth}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <ModeSelector 
                currentMode={currentMode} 
                setCurrentMode={setCurrentMode} 
              />
              {getCurrentConversationCount() > 0 && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {getCurrentConversationCount()} messages
                </span>
              )}
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                title="Settings"
              >
                <Settings className="h-5 w-5" />
              </button>
              <div className="flex items-center space-x-2">
                <button
                  onClick={clearCurrentConversations}
                  disabled={getCurrentConversationCount() === 0}
                  className="px-3 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Clear {getModeTitle()}
                </button>
                <button
                  onClick={clearAllConversations}
                  className="px-3 py-2 text-sm text-red-600 hover:text-red-800 hover:bg-red-50 rounded-lg transition-colors"
                >
                  Clear All
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Settings Panel */}
        {showSettings && (
          <SettingsPanel
            settings={settings}
            setSettings={setSettings}
            onClose={() => setShowSettings(false)}
          />
        )}

        {/* Main Content Area */}
        <div className="flex-1 overflow-hidden">
          {currentMode === 'download' ? (
            <DownloadManager />
          ) : (
            <ConversationDisplay
              conversations={getCurrentConversations()}
              isLoading={isLoading}
              error={error}
            />
          )}
        </div>

        {/* Prompt Input */}
        {currentMode !== 'download' && (
          <div className="bg-white border-t border-gray-200 p-6">
            <PromptInput
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
              placeholder={
                currentMode === 'claude' ? 'Ask Claude anything...' :
                currentMode === 'conversations' ? 'Search conversation data...' :
                'Ask Claude to analyze your conversation data (e.g., "What are the main customer complaints?")'
              }
              exampleQuestions={
                currentMode === 'ask' ? [
                  'What are the main customer complaints or issues mentioned in the conversations?',
                  'What are the most common topics or themes in the conversation data?',
                  'Analyze customer sentiment and satisfaction trends in the conversations'
                ] : []
              }
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
