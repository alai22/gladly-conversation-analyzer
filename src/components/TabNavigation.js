import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Search, MessageSquare, BarChart3, FileText, TrendingUp, Wrench, Bug, Users, CircleDot } from 'lucide-react';
import { getPathFromMode, isPathBasedMode } from '../utils/routes';

const TabNavigation = ({ currentMode, setCurrentMode, adminMode }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const setModeAndUrl = (modeId) => {
    setCurrentMode(modeId);
    const path = getPathFromMode(modeId);
    if (path) {
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete('mode');
      navigate({ pathname: path, search: nextParams.toString() }, { replace: true });
    } else {
      setSearchParams({ mode: modeId }, { replace: true });
    }
  };
  const [activeTab, setActiveTab] = useState(() => {
    // Determine active tab based on current mode
    if (currentMode === 'bug-triage') {
      return 'bug-triage';
    }
    if (currentMode === 'text-interview') {
      return 'interviews';
    }
    if (currentMode === 'neck-fit-modeler') {
      return 'engineering';
    }
    if (['conversations', 'ask', 'conversation-trends'].includes(currentMode)) {
      return 'gladly';
    } else if (['churn-trends', 'survicate'].includes(currentMode)) {
      return 'churn';
    } else if (currentMode === 'survey-manager') {
      return 'surveys';
    } else if (['api-data-manager', 'tools', 'analytics', 'jira-status'].includes(currentMode) || adminMode === 'download' || adminMode === 'claude') {
      return 'tools';
    }
    // Default to churn if mode doesn't match
    return 'churn';
  });

  // Update active tab when currentMode or adminMode changes externally
  useEffect(() => {
    if (currentMode === 'bug-triage') {
      setActiveTab('bug-triage');
    } else if (currentMode === 'text-interview') {
      setActiveTab('interviews');
    } else if (currentMode === 'neck-fit-modeler') {
      setActiveTab('engineering');
    } else if (['conversations', 'ask', 'conversation-trends'].includes(currentMode)) {
      setActiveTab('gladly');
    } else if (['churn-trends', 'survicate'].includes(currentMode)) {
      setActiveTab('churn');
    } else if (currentMode === 'survey-manager') {
      setActiveTab('surveys');
    } else if (['api-data-manager', 'tools', 'analytics', 'jira-status'].includes(currentMode) || adminMode === 'download' || adminMode === 'claude') {
      setActiveTab('tools');
    } else {
      // Default to churn if mode doesn't match
      setActiveTab('churn');
    }
  }, [currentMode, adminMode]);

  const gladlyModes = [
    {
      id: 'conversation-trends',
      name: 'Conversation Trends',
      description: 'Visualize conversation topic trends',
      icon: TrendingUp,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200'
    },
    {
      id: 'conversations',
      name: 'Search Conversations',
      description: 'Search Gladly conversation data',
      icon: Search,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200'
    },
    {
      id: 'ask',
      name: 'Ask About Conversations',
      description: 'AI analysis of conversation data',
      icon: MessageSquare,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      borderColor: 'border-purple-200'
    }
  ];

  const churnModes = [
    {
      id: 'churn-trends',
      name: 'Churn Trends',
      description: 'Visualize cancellation trends',
      icon: BarChart3,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200'
    },
    {
      id: 'survicate',
      name: 'Ask About Churn',
      description: 'AI analysis of cancellation surveys',
      icon: FileText,
      color: 'text-teal-600',
      bgColor: 'bg-teal-50',
      borderColor: 'border-teal-200'
    }
  ];

  const handleModeChange = (modeId) => {
    setModeAndUrl(modeId);
  };

  const tabBtn = (active) =>
    `shrink-0 md:flex-1 md:min-w-0 px-3 sm:px-4 py-2.5 text-sm font-medium rounded-md transition-colors min-h-[44px] flex items-center justify-center gap-1.5 ${
      active ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'
    }`;

  return (
    <div className="flex flex-col space-y-3 min-w-0 w-full">
      {/* Main Tabs — horizontal scroll on narrow viewports */}
      <div className="overflow-x-auto min-w-0 -mx-1 px-1 sm:mx-0 sm:px-0 overscroll-x-contain [scrollbar-width:thin]">
        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg flex-nowrap w-max min-w-full md:w-full md:min-w-0">
        <button
          onClick={() => {
            setActiveTab('churn');
            if (!['churn-trends', 'survicate'].includes(currentMode)) {
              setModeAndUrl('churn-trends');
            }
          }}
          className={tabBtn(activeTab === 'churn')}
        >
          <span className="md:hidden whitespace-nowrap">Churn</span>
          <span className="hidden md:inline whitespace-nowrap">Churn Analysis</span>
        </button>
        <button
          onClick={() => {
            setActiveTab('surveys');
            if (currentMode !== 'survey-manager') {
              setModeAndUrl('survey-manager');
            }
          }}
          className={tabBtn(activeTab === 'surveys')}
        >
          <span className="md:hidden whitespace-nowrap">Surveys</span>
          <span className="hidden md:inline whitespace-nowrap">Survicate Surveys</span>
        </button>
        <button
          onClick={() => {
            setActiveTab('gladly');
            if (!['conversations', 'ask', 'conversation-trends'].includes(currentMode)) {
              setModeAndUrl('conversation-trends');
            }
          }}
          className={tabBtn(activeTab === 'gladly')}
        >
          <span className="md:hidden whitespace-nowrap">Gladly</span>
          <span className="hidden md:inline whitespace-nowrap">Gladly Conversations</span>
        </button>
        <button
          onClick={() => {
            setActiveTab('interviews');
            if (currentMode !== 'text-interview') {
              setModeAndUrl('text-interview');
            }
          }}
          className={tabBtn(activeTab === 'interviews')}
        >
          <Users className="h-4 w-4 shrink-0 hidden sm:block" />
          <span className="md:hidden whitespace-nowrap">Interviews</span>
          <span className="hidden md:inline whitespace-nowrap">Text Interviews</span>
        </button>
        <button
          onClick={() => {
            setActiveTab('tools');
            if (!['api-data-manager', 'tools', 'analytics'].includes(currentMode) && adminMode !== 'download' && adminMode !== 'claude') {
              setModeAndUrl('tools');
            }
          }}
          className={tabBtn(activeTab === 'tools')}
        >
          Tools
        </button>
        <button
          onClick={() => {
            setActiveTab('engineering');
            if (currentMode !== 'neck-fit-modeler') {
              setModeAndUrl('neck-fit-modeler');
            }
          }}
          className={tabBtn(activeTab === 'engineering')}
        >
          <CircleDot className="h-4 w-4 shrink-0 hidden sm:block" />
          <span className="md:hidden whitespace-nowrap">Engineering</span>
          <span className="hidden md:inline whitespace-nowrap">Engineering</span>
        </button>
        <button
          onClick={() => {
            setActiveTab('bug-triage');
            if (currentMode !== 'bug-triage') {
              setModeAndUrl('bug-triage');
            }
          }}
          className={tabBtn(activeTab === 'bug-triage')}
        >
          <Bug className="h-4 w-4 shrink-0" />
          <span className="md:hidden whitespace-nowrap">Triage</span>
          <span className="hidden md:inline whitespace-nowrap">Bug Triage</span>
        </button>
        </div>
      </div>

      {/* Sub-options for active tab */}
      {activeTab !== 'tools' && activeTab !== 'surveys' && activeTab !== 'bug-triage' && activeTab !== 'interviews' && activeTab !== 'engineering' && (
        <div className="flex gap-2 overflow-x-auto pb-1 min-w-0 -mx-1 px-1 sm:mx-0 sm:px-0 overscroll-x-contain [scrollbar-width:thin]">
          {(activeTab === 'gladly' ? gladlyModes : churnModes).map((mode) => {
            const Icon = mode.icon;
            const isActive = currentMode === mode.id;
            
            return (
              <button
                key={mode.id}
                onClick={() => handleModeChange(mode.id)}
                className={`flex items-center space-x-2 px-4 py-2.5 rounded-lg border-2 transition-all shrink-0 min-h-[44px] ${
                  isActive
                    ? `${mode.bgColor} ${mode.borderColor} border-2 ${mode.color}`
                    : 'bg-white border-gray-200 text-gray-700 hover:border-gray-300 hover:bg-gray-50'
                }`}
              >
                <Icon className={`h-4 w-4 shrink-0 ${isActive ? mode.color : 'text-gray-500'}`} />
                <div className="text-left">
                  <div className={`text-sm font-medium ${isActive ? mode.color : 'text-gray-900'}`}>
                    {mode.name}
                  </div>
                  <div className="text-xs text-gray-500 max-w-[14rem] sm:max-w-none">
                    {mode.description}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default TabNavigation;

