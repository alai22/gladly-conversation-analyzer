import React, { useState, useEffect, useRef } from 'react';
import { Settings, Menu, LogOut } from 'lucide-react';
import PromptInput from './components/PromptInput';
import ConversationDisplay from './components/ConversationDisplay';
import Sidebar from './components/Sidebar';
import SettingsPanel from './components/SettingsPanel';
import Login from './components/Login';
import TabNavigation from './components/TabNavigation';
import DownloadManager from './components/DownloadManager';
import ZoomDownloadManager from './components/ZoomDownloadManager';
import ChurnTrendsChart from './components/ChurnTrendsChart';
import ConversationTrendsChart from './components/ConversationTrendsChart';
import ApiDataManager from './components/ApiDataManager';
import SurveyManager from './components/SurveyManager';
import Tools from './components/Tools';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import BugTriageCopilot from './components/BugTriageCopilot';
import JiraStatusView from './components/JiraStatusView';
import TextInterviewHub from './components/interview/TextInterviewHub';
import InterviewParticipantPage from './components/interview/InterviewParticipantPage';
import { useAnalytics } from './hooks/useAnalytics';
import axios from 'axios';
import { useSearchParams, useLocation, useNavigate } from 'react-router-dom';
import { getSurvicateDataSource } from './utils/constants';
import { getModeFromPath, getPathFromMode, isPathBasedMode, isInterviewParticipantPath } from './utils/routes';

// Configure axios to send credentials (cookies) with all requests
axios.defaults.withCredentials = true;

// Add interceptor to include auth token in headers (temporary workaround for session issues)
axios.interceptors.request.use(
  (config) => {
    const authToken = localStorage.getItem('authToken');
    if (authToken) {
      config.headers['X-Auth-Token'] = authToken;
    }
    // Also include admin token for admin routes
    const adminToken = localStorage.getItem('adminToken');
    if (adminToken) {
      config.headers['X-Admin-Token'] = adminToken;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [conversations, setConversations] = useState({
    claude: [],
    conversations: [],
    ask: [],
    download: [],
    zoom: [],
    survicate: [],
    'churn-trends': [],
    'conversation-trends': [],
    'api-data-manager': [],
    'tools': [],
    'analytics': []
  });

  // Initialize currentMode: path takes precedence, then query mode, then default
  const [currentMode, setCurrentMode] = useState(() => {
    const pathMode = getModeFromPath(location.pathname);
    if (pathMode) return pathMode;
    const urlMode = searchParams.get('mode');
    if (urlMode) return urlMode;
    const savedMode = localStorage.getItem('gladly_current_mode');
    return savedMode || 'churn-trends';
  });
  
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
  const [adminMode, setAdminMode] = useState(null); // 'claude' or 'download' for admin tools
  const [isAdminAuthenticated, setIsAdminAuthenticated] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // Close mobile sidebar when resizing to desktop breakpoint
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 768px)');
    const onChange = () => {
      if (mq.matches) setMobileSidebarOpen(false);
    };
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);

  useEffect(() => {
    if (!mobileSidebarOpen) return;
    const onKey = (e) => {
      if (e.key === 'Escape') setMobileSidebarOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [mobileSidebarOpen]);
  
  // Ref to prevent infinite loops when syncing URL and currentMode
  const isSyncingRef = useRef(false);
  
  // Sync URL when currentMode changes: use path for path-based modes, else query
  useEffect(() => {
    if (isSyncingRef.current) return;
    if (isInterviewParticipantPath(location.pathname)) return;
    // Legacy /churn?mode=survicate: do not strip query here; URL→mode effect migrates to /churn/ask
    if (location.pathname === '/churn' && searchParams.get('mode') === 'survicate') {
      return;
    }
    const path = getPathFromMode(currentMode);
    const pathMatches = path && location.pathname === path;
    const queryMode = searchParams.get('mode');
    const queryMatches = queryMode === currentMode;
    if (pathMatches && !queryMode) return; // already on canonical path with no redundant mode param
    if (!pathMatches && queryMatches) return; // already on query-based URL with correct mode
    if (!currentMode) return;
    isSyncingRef.current = true;
    if (path) {
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete('mode');
      navigate({ pathname: path, search: nextParams.toString() }, { replace: true });
    } else {
      setSearchParams({ mode: currentMode }, { replace: true });
    }
    setTimeout(() => { isSyncingRef.current = false; }, 0);
  }, [currentMode, location.pathname, searchParams, setSearchParams, navigate]);

  // Sync currentMode when URL changes (path first, then query; redirect old ?mode= to path)
  useEffect(() => {
    if (isSyncingRef.current) return;
    if (isInterviewParticipantPath(location.pathname)) return;
    const pathMode = getModeFromPath(location.pathname);
    const queryMode = searchParams.get('mode');

    // Redirect / with path-based ?mode= to canonical path (e.g. ?mode=churn-trends -> /churn)
    if (location.pathname === '/' && queryMode && isPathBasedMode(queryMode)) {
      isSyncingRef.current = true;
      const path = getPathFromMode(queryMode);
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete('mode');
      navigate({ pathname: path, search: nextParams.toString() }, { replace: true });
      setCurrentMode(queryMode);
      setTimeout(() => { isSyncingRef.current = false; }, 0);
      return;
    }

    // Redirect / with no mode to /churn
    if (location.pathname === '/' && !queryMode) {
      isSyncingRef.current = true;
      navigate('/churn', { replace: true });
      if (currentMode !== 'churn-trends') setCurrentMode('churn-trends');
      setTimeout(() => { isSyncingRef.current = false; }, 0);
      return;
    }

    // Legacy: /churn?mode=survicate conflicted with pathname → churn-trends; move to canonical path
    if (location.pathname === '/churn' && queryMode === 'survicate') {
      const canonicalAskPath = getPathFromMode('survicate');
      if (canonicalAskPath) {
        isSyncingRef.current = true;
        const nextParams = new URLSearchParams(searchParams);
        nextParams.delete('mode');
        navigate({ pathname: canonicalAskPath, search: nextParams.toString() }, { replace: true });
        setCurrentMode('survicate');
        setTimeout(() => { isSyncingRef.current = false; }, 0);
        return;
      }
    }

    if (pathMode && pathMode !== currentMode) {
      isSyncingRef.current = true;
      setCurrentMode(pathMode);
      setTimeout(() => { isSyncingRef.current = false; }, 0);
      return;
    }
    if (!pathMode && queryMode && queryMode !== currentMode) {
      isSyncingRef.current = true;
      setCurrentMode(queryMode);
      setTimeout(() => { isSyncingRef.current = false; }, 0);
      return;
    }
    // URL has no mode and we're not on a path: push current mode to URL (query)
    if (!pathMode && !queryMode && currentMode && !isPathBasedMode(currentMode)) {
      isSyncingRef.current = true;
      setSearchParams({ mode: currentMode }, { replace: true });
      setTimeout(() => { isSyncingRef.current = false; }, 0);
    } else if (!pathMode && !queryMode && currentMode && isPathBasedMode(currentMode)) {
      isSyncingRef.current = true;
      navigate(getPathFromMode(currentMode), { replace: true });
      setTimeout(() => { isSyncingRef.current = false; }, 0);
    }
  }, [location.pathname, searchParams, currentMode, setSearchParams, navigate]);

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

    // URL mode takes precedence, so we don't override it here
    // The initial state already handles localStorage fallback
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

  // Check if user is already authenticated (check localStorage token first, then backend session)
  useEffect(() => {
    const checkAuthStatus = async () => {
      // Check authentication with backend session (works with Google SSO)
      try {
        const response = await axios.get('/api/auth/status', {
          withCredentials: true
        });
        
        if (response.data.authenticated) {
          console.log('Initial auth check - setting authenticated to true');
          setIsAuthenticated(true);
          
          // Also check admin status if authenticated
          try {
            const adminResponse = await axios.get('/api/auth/admin-status', {
              withCredentials: true
            });
            if (adminResponse.data.admin_authenticated) {
              console.log('Initial admin auth check - admin authenticated');
              setIsAdminAuthenticated(true);
            } else {
              setIsAdminAuthenticated(false);
            }
          } catch (adminError) {
            console.error('Error checking admin status:', adminError);
            setIsAdminAuthenticated(false);
          }
        } else {
          console.log('Initial auth check - not authenticated');
          setIsAuthenticated(false);
          setIsAdminAuthenticated(false);
        }
      } catch (error) {
        console.error('Error checking auth status:', error);
        setIsAuthenticated(false);
        setIsAdminAuthenticated(false);
      }
    };
    checkAuthStatus();
  }, []);

  // Check backend health on component mount (only when authenticated)
  useEffect(() => {
    if (isAuthenticated) {
      checkHealth();
    }
  }, [isAuthenticated]);

  // Track pageviews with analytics
  useAnalytics();

  const handleLogin = async () => {
    // Verify authentication with backend session (works with Google SSO)
    try {
      const response = await axios.get('/api/auth/status', {
        withCredentials: true
      });
      
      console.log('handleLogin - auth status response:', response.data);
      
      if (response.data.authenticated) {
        console.log('handleLogin - setting authenticated to true');
        setIsAuthenticated(true);
        
        // Also check admin status
        try {
          const adminResponse = await axios.get('/api/auth/admin-status', {
            withCredentials: true
          });
          if (adminResponse.data.admin_authenticated) {
            setIsAdminAuthenticated(true);
          }
        } catch (adminError) {
          console.error('Error checking admin status:', adminError);
        }
      } else {
        // If not authenticated, stay on login screen
        console.log('handleLogin - not authenticated');
        setIsAuthenticated(false);
        setIsAdminAuthenticated(false);
      }
    } catch (error) {
      console.error('Error checking auth status:', error);
      setIsAuthenticated(false);
      setIsAdminAuthenticated(false);
    }
  };

  const handleLogout = async () => {
    try {
      await axios.post('/api/auth/logout');
    } catch (error) {
      console.error('Error during logout:', error);
    } finally {
      // Clear localStorage auth token
      localStorage.removeItem('authToken');
      localStorage.removeItem('auth_method');
      localStorage.removeItem('adminToken');
      setIsAuthenticated(false);
      setIsAdminAuthenticated(false);
      setAdminMode(null);
    }
  };

  const checkHealth = async () => {
    try {
      const response = await axios.get('/api/health');
      setHealthStatus(response.data);
    } catch (error) {
      setHealthStatus({ status: 'unhealthy', error: error.message });
    }
  };

  // Handle admin authentication check
  const handleAdminLogin = async () => {
    // Check admin status from backend (works with Google SSO session)
    try {
      const response = await axios.get('/api/auth/admin-status', {
        withCredentials: true
      });
      if (response.data.admin_authenticated) {
        setIsAdminAuthenticated(true);
      } else {
        setIsAdminAuthenticated(false);
      }
    } catch (error) {
      console.error('Error checking admin status:', error);
      setIsAdminAuthenticated(false);
    }
  };

  // Check admin auth when trying to access admin tools or Tools page
  useEffect(() => {
    if (isAuthenticated) {
      // Check admin auth if:
      // 1. In admin mode (claude or download)
      // 2. On Tools page (currentMode === 'tools')
      // 3. On api-data-manager (Survicate admin)
      const needsAdminAuth = adminMode === 'claude' || 
                             adminMode === 'download' || 
                             currentMode === 'tools' ||
                             currentMode === 'api-data-manager' ||
                             currentMode === 'jira-status';
      
      if (needsAdminAuth) {
        const checkAdminAuth = async () => {
          // Check admin status from backend (works with Google SSO session)
          try {
            const response = await axios.get('/api/auth/admin-status', {
              withCredentials: true
            });
            if (response.data.admin_authenticated) {
              setIsAdminAuthenticated(true);
            } else {
              // Not admin authenticated, reset admin mode
              setIsAdminAuthenticated(false);
              setAdminMode(null);
              // Don't change currentMode if user is just browsing - only reset if they were in admin mode
              if (adminMode === 'claude' || adminMode === 'download') {
                setCurrentMode('churn-trends');
              }
            }
          } catch (error) {
            console.error('Error checking admin status:', error);
            // On error, assume not authenticated
            setIsAdminAuthenticated(false);
            setAdminMode(null);
            if (adminMode === 'claude' || adminMode === 'download') {
              setCurrentMode('churn-trends');
            }
          }
        };
        checkAdminAuth();
      } else if (!adminMode && currentMode !== 'tools' && currentMode !== 'api-data-manager' && currentMode !== 'jira-status') {
        // Not in admin mode or on admin pages, reset admin auth state
        setIsAdminAuthenticated(false);
      }
    }
  }, [adminMode, currentMode, isAuthenticated]);

  // Public participant interview — no Halo login required
  if (isInterviewParticipantPath(location.pathname)) {
    return <InterviewParticipantPage />;
  }

  // If not authenticated, show login screen
  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} onAdminLogin={handleAdminLogin} />;
  }

  // If trying to access admin tools or Tools page but not admin authenticated, show admin login
  if ((adminMode === 'claude' || adminMode === 'download' || currentMode === 'tools' || currentMode === 'api-data-manager' || currentMode === 'jira-status') && !isAdminAuthenticated) {
    return <Login onLogin={handleLogin} onAdminLogin={handleAdminLogin} requireAdmin={true} />;
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
    const mode = adminMode || currentMode;
    setConversations(prev => ({
      ...prev,
      [mode]: [...(prev[mode] || []), newConversation]
    }));
  };

  // Get current mode's conversations
  const getCurrentConversations = () => {
    const mode = adminMode || currentMode;
    return conversations[mode] || [];
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
      // Get data source from localStorage (set by Sidebar)
      const dataSource = getSurvicateDataSource();
      
      // Build conversation history from previous survicate conversations
      const survicateConversations = conversations.survicate || [];
      const conversationHistory = survicateConversations.flatMap(conv => [
        { role: 'user', content: conv.userMessage },
        { role: 'assistant', content: conv.response }
      ]);
      
      const response = await axios.post('/api/survicate/ask', {
        question,
        model: settings.model,
        max_tokens: settings.maxTokens,
        data_source: dataSource,
        conversation_history: conversationHistory.length > 0 ? conversationHistory : undefined
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

  const clearSurvicateConversations = () => {
    if (window.confirm('Are you sure you want to clear the conversation history? This will start a fresh conversation.')) {
      setConversations(prev => ({
        ...prev,
        survicate: []
      }));
    }
  };

  const handleSendMessage = (message) => {
    if (!message.trim()) return;

    // Check admin mode first
    if (adminMode === 'claude') {
      handleClaudeMessage(message);
      return;
    }

    switch (currentMode) {
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
        handleConversationAsk(message);
    }
  };

  // Clear conversations for the current mode only
  const clearCurrentConversations = () => {
    const mode = adminMode || currentMode;
    setConversations(prev => ({
      ...prev,
      [mode]: []
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
      survicate: [],
      'churn-trends': []
    });
    setError(null);
  };

  const getCurrentConversationCount = () => {
    return getCurrentConversations().length;
  };

  const getModeTitle = () => {
    const modeTitles = {
      'conversation-trends': 'Conversation Trends',
      'claude': 'Claude Chat',
      'conversations': 'Search Conversations', 
      'ask': 'Ask About Conversations',
      'download': 'Download Manager',
      'survicate': 'Ask About Churn',
      'churn-trends': 'Churn Trends',
      'api-data-manager': 'Data Management'
    };
    if (adminMode) {
      return modeTitles[adminMode] || 'Admin Mode';
    }
    return modeTitles[currentMode] || 'Unknown Mode';
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {mobileSidebarOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          aria-label="Close menu"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}
      {/* Sidebar */}
      <Sidebar 
        healthStatus={healthStatus}
        onRefreshHealth={checkHealth}
        currentMode={currentMode}
        setAdminMode={setAdminMode}
        setCurrentMode={setCurrentMode}
        onCloseSettings={() => setShowSettings(false)}
        mobileDrawerOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="bg-white shadow-sm border-b border-gray-200 px-3 py-3 sm:px-6 sm:py-4">
          <div className="flex items-center gap-2 min-w-0">
            <button
              type="button"
              onClick={() => setMobileSidebarOpen(true)}
              className="md:hidden shrink-0 p-2.5 -ml-1 rounded-lg text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="flex-1 min-w-0">
              {adminMode && currentMode !== 'tools' ? (
                <div className="flex flex-wrap items-center gap-2 px-3 py-2 bg-orange-50 border-2 border-orange-200 rounded-lg">
                  <span className="text-sm font-medium text-orange-900">
                    Admin Mode: {getModeTitle()}
                  </span>
                  <button
                    onClick={() => {
                      setAdminMode(null);
                      setCurrentMode('tools');
                    }}
                    className="text-xs text-orange-600 hover:text-orange-800 underline"
                  >
                    Exit
                  </button>
                </div>
              ) : (
                <TabNavigation 
                  currentMode={currentMode} 
                  setCurrentMode={setCurrentMode}
                  adminMode={adminMode}
                />
              )}
            </div>
            <div className="flex items-center gap-1 sm:gap-2 shrink-0">
              <button
                onClick={handleLogout}
                className="flex items-center justify-center gap-2 px-2.5 py-2 sm:px-3 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors min-h-[40px]"
                title="Logout"
              >
                <LogOut className="h-5 w-5 sm:hidden shrink-0" aria-hidden />
                <span className="hidden sm:inline">Logout</span>
              </button>
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="p-2.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors min-h-[40px] min-w-[40px] flex items-center justify-center"
                title="Settings"
              >
                <Settings className="h-5 w-5" />
              </button>
              {!adminMode && (
                <div className="hidden md:flex items-center space-x-2">
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
              )}
            </div>
          </div>
        </header>

        {/* Settings Panel */}
        {showSettings && (
          <SettingsPanel
            settings={settings}
            setSettings={setSettings}
            adminMode={adminMode}
            setAdminMode={setAdminMode}
            setCurrentMode={setCurrentMode}
            onClose={() => setShowSettings(false)}
          />
        )}

        {/* Main Content Area */}
        <div className={`flex-1 ${currentMode === 'churn-trends' || currentMode === 'conversation-trends' || currentMode === 'api-data-manager' || currentMode === 'survey-manager' || currentMode === 'tools' || currentMode === 'zoom' || currentMode === 'analytics' || currentMode === 'bug-triage' || currentMode === 'jira-status' || currentMode === 'text-interview' || adminMode === 'download' ? 'overflow-y-auto' : 'overflow-hidden'}`}>
          {/* Show actual tool components when active */}
          {currentMode === 'bug-triage' ? (
            <BugTriageCopilot />
          ) : currentMode === 'jira-status' ? (
            <JiraStatusView setCurrentMode={setCurrentMode} />
          ) : currentMode === 'api-data-manager' ? (
            <ApiDataManager />
          ) : currentMode === 'survey-manager' ? (
            <SurveyManager />
          ) : currentMode === 'zoom' ? (
            <ZoomDownloadManager />
          ) : currentMode === 'analytics' ? (
            <AnalyticsDashboard />
          ) : adminMode === 'download' ? (
            <DownloadManager />
          ) : adminMode === 'claude' ? (
            <ConversationDisplay
              conversations={getCurrentConversations()}
              isLoading={isLoading}
              error={error}
            />
          ) : currentMode === 'tools' ? (
            <Tools 
              currentMode={currentMode}
              setCurrentMode={setCurrentMode}
              adminMode={adminMode}
              setAdminMode={setAdminMode}
            />
          ) : currentMode === 'text-interview' ? (
            <TextInterviewHub />
          ) : currentMode === 'churn-trends' ? (
            <ChurnTrendsChart />
          ) : currentMode === 'conversation-trends' ? (
            <ConversationTrendsChart />
          ) : (
            <ConversationDisplay
              conversations={getCurrentConversations()}
              isLoading={isLoading}
              error={error}
            />
          )}
        </div>

        {/* Prompt Input */}
        {adminMode !== 'download' && currentMode !== 'churn-trends' && currentMode !== 'conversation-trends' && currentMode !== 'api-data-manager' && currentMode !== 'survey-manager' && currentMode !== 'tools' && currentMode !== 'zoom' && currentMode !== 'analytics' && currentMode !== 'bug-triage' && currentMode !== 'jira-status' && currentMode !== 'text-interview' && (
          <div className="bg-white border-t border-gray-200 p-6">
            {/* Clear Conversation Button for Survicate Mode */}
            {currentMode === 'survicate' && conversations.survicate && conversations.survicate.length > 0 && (
              <div className="mb-4 flex justify-end">
                <button
                  onClick={clearSurvicateConversations}
                  className="flex items-center space-x-2 px-4 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors border border-gray-300"
                  title="Clear conversation history and start fresh"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  <span>Clear Conversation</span>
                </button>
              </div>
            )}
            <PromptInput
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
              placeholder={
                adminMode === 'claude' ? 'Ask Claude anything...' :
                currentMode === 'conversations' ? 'Search Gladly conversation data...' :
                currentMode === 'survicate' ? 'Ask about cancellation survey data (e.g., "What are the main cancellation reasons?")' :
                'Ask Claude to analyze your conversation data (e.g., "What are the main customer complaints?")'
              }
              exampleQuestions={
                currentMode === 'ask' ? [
                  'What are the main customer complaints or issues mentioned in the conversations?',
                  'What are the most common topics or themes in the conversation data?',
                  'Analyze customer sentiment and satisfaction trends in the conversations'
                ] : currentMode === 'survicate' ? [
                  'What are the main reasons customers canceled their Halo Pack Membership?',
                  'How have GPS and location accuracy complaints changed over time?',
                  'What are the most common themes in customer feedback about battery life and charging issues?'
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
