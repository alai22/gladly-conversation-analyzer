import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Search, MessageSquare, BarChart3, FileText, TrendingUp, Bug, Users, Cpu, FlaskConical, ClipboardList } from 'lucide-react';
import { getPathFromMode, isPlatformMode, isProductResearchMode } from '../utils/routes';

const TabNavigation = ({ currentMode, setCurrentMode, adminMode, setAdminMode }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const setModeAndUrl = (modeId, nextAdminMode = null) => {
    setCurrentMode(modeId);
    if (nextAdminMode !== undefined) {
      setAdminMode(nextAdminMode);
    }
    const path = getPathFromMode(modeId, nextAdminMode ?? adminMode);
    if (path) {
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete('mode');
      navigate({ pathname: path, search: nextParams.toString() }, { replace: true });
    } else {
      setSearchParams({ mode: modeId }, { replace: true });
    }
  };

  const resolveActiveTab = (mode, admin) => {
    if (mode === 'bug-triage') return 'bug-triage';
    if (mode === 'neck-fit-modeler') return 'hardware';
    if (['conversations', 'ask', 'conversation-trends'].includes(mode)) return 'gladly';
    if (isProductResearchMode(mode)) return 'research';
    if (isPlatformMode(mode, admin)) return 'platform';
    return 'research';
  };

  const [activeTab, setActiveTab] = useState(() => resolveActiveTab(currentMode, adminMode));

  useEffect(() => {
    setActiveTab(resolveActiveTab(currentMode, adminMode));
  }, [currentMode, adminMode]);

  const productResearchModes = [
    {
      id: 'churn-trends',
      name: 'Churn Trends',
      description: 'Visualize cancellation trends',
      icon: BarChart3,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
    },
    {
      id: 'survicate',
      name: 'Ask About Churn',
      description: 'AI analysis of cancellation surveys',
      icon: FileText,
      color: 'text-teal-600',
      bgColor: 'bg-teal-50',
      borderColor: 'border-teal-200',
    },
    {
      id: 'survey-manager',
      name: 'Survicate Surveys',
      description: 'Browse and manage Survicate survey data',
      icon: ClipboardList,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
      borderColor: 'border-orange-200',
    },
    {
      id: 'halo-surveys',
      name: 'Halo Surveys',
      description: 'Design and publish branded survey campaigns',
      icon: ClipboardList,
      color: 'text-amber-600',
      bgColor: 'bg-amber-50',
      borderColor: 'border-amber-200',
    },
    {
      id: 'text-interview',
      name: 'Text Interviews',
      description: 'Run structured text-based research interviews',
      icon: Users,
      color: 'text-violet-600',
      bgColor: 'bg-violet-50',
      borderColor: 'border-violet-200',
    },
  ];

  const gladlyModes = [
    {
      id: 'conversation-trends',
      name: 'Conversation Trends',
      description: 'Visualize conversation topic trends',
      icon: TrendingUp,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
    },
    {
      id: 'conversations',
      name: 'Search Conversations',
      description: 'Search Gladly conversation data',
      icon: Search,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
    },
    {
      id: 'ask',
      name: 'Ask About Conversations',
      description: 'AI analysis of conversation data',
      icon: MessageSquare,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      borderColor: 'border-purple-200',
    },
  ];

  const handleModeChange = (modeId) => {
    setModeAndUrl(modeId, null);
  };

  const tabBtn = (active) =>
    `shrink-0 md:flex-1 md:min-w-0 px-3 sm:px-4 py-2.5 text-sm font-medium rounded-md transition-colors min-h-[44px] flex items-center justify-center gap-1.5 ${
      active ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'
    }`;

  const platformActive = isPlatformMode(currentMode, adminMode);
  const researchActive = isProductResearchMode(currentMode);

  const subNavModes =
    activeTab === 'gladly' ? gladlyModes : activeTab === 'research' ? productResearchModes : [];

  return (
    <div className="flex flex-col space-y-3 min-w-0 w-full">
      <div className="overflow-x-auto min-w-0 -mx-1 px-1 sm:mx-0 sm:px-0 overscroll-x-contain [scrollbar-width:thin]">
        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg flex-nowrap w-max min-w-full md:w-full md:min-w-0">
        <button
          onClick={() => {
            setActiveTab('research');
            if (!researchActive) {
              setModeAndUrl('churn-trends', null);
            }
          }}
          className={tabBtn(activeTab === 'research')}
        >
          <FlaskConical className="h-4 w-4 shrink-0 hidden sm:block" />
          <span className="md:hidden whitespace-nowrap">Research</span>
          <span className="hidden md:inline whitespace-nowrap">Product Research</span>
        </button>
        <button
          onClick={() => {
            setActiveTab('gladly');
            if (!['conversations', 'ask', 'conversation-trends'].includes(currentMode)) {
              setModeAndUrl('conversation-trends', null);
            }
          }}
          className={tabBtn(activeTab === 'gladly')}
        >
          <span className="md:hidden whitespace-nowrap">Gladly</span>
          <span className="hidden md:inline whitespace-nowrap">Gladly Conversations</span>
        </button>
        <button
          onClick={() => {
            setActiveTab('platform');
            if (!platformActive || adminMode) {
              setModeAndUrl('tools', null);
            }
          }}
          className={tabBtn(activeTab === 'platform')}
        >
          <span className="whitespace-nowrap">Platform</span>
        </button>
        <button
          onClick={() => {
            setActiveTab('hardware');
            if (currentMode !== 'neck-fit-modeler') {
              setModeAndUrl('neck-fit-modeler', null);
            }
          }}
          className={tabBtn(activeTab === 'hardware')}
        >
          <Cpu className="h-4 w-4 shrink-0 hidden sm:block" />
          <span className="whitespace-nowrap">Hardware</span>
        </button>
        <button
          onClick={() => {
            setActiveTab('bug-triage');
            if (currentMode !== 'bug-triage') {
              setModeAndUrl('bug-triage', null);
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

      {subNavModes.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-1 min-w-0 -mx-1 px-1 sm:mx-0 sm:px-0 overscroll-x-contain [scrollbar-width:thin]">
          {subNavModes.map((mode) => {
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
