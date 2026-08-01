import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Search,
  MessageSquare,
  BarChart3,
  FileText,
  TrendingUp,
  Bug,
  Users,
  Cpu,
  FlaskConical,
  ClipboardList,
  Home,
  Tags,
  ChevronDown,
} from 'lucide-react';
import { getPathFromMode, isHomeTabMode, isProductResearchMode, isHardwareMode } from '../utils/routes';

const TabNavigation = ({ currentMode, setCurrentMode, adminMode, setAdminMode }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [openMenu, setOpenMenu] = useState(null); // 'research' | 'gladly' | 'hardware' | null
  const closeTimerRef = useRef(null);
  const navRef = useRef(null);

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
    if (isHardwareMode(mode)) return 'hardware';
    if (['conversations', 'ask', 'conversation-trends'].includes(mode)) return 'gladly';
    if (isProductResearchMode(mode)) return 'research';
    if (isHomeTabMode(mode, admin)) return 'home';
    return 'home';
  };

  const activeTab = resolveActiveTab(currentMode, adminMode);

  useEffect(() => {
    const onDocClick = (e) => {
      if (navRef.current && !navRef.current.contains(e.target)) {
        setOpenMenu(null);
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  useEffect(() => () => {
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
  }, []);

  const productResearchModes = [
    {
      id: 'churn-trends',
      name: 'Churn Trends',
      description: 'Visualize cancellation trends',
      icon: BarChart3,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
    },
    {
      id: 'survicate',
      name: 'Ask About Churn',
      description: 'AI analysis of cancellation surveys',
      icon: FileText,
      color: 'text-teal-600',
      bgColor: 'bg-teal-50',
    },
    {
      id: 'survey-manager',
      name: 'Survicate Surveys',
      description: 'Browse and manage Survicate survey data',
      icon: ClipboardList,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
    },
    {
      id: 'halo-surveys',
      name: 'Halo Surveys',
      description: 'Design and publish branded survey campaigns',
      icon: ClipboardList,
      color: 'text-amber-600',
      bgColor: 'bg-amber-50',
    },
    {
      id: 'text-interview',
      name: 'Text Interviews',
      description: 'Run structured text-based research interviews',
      icon: Users,
      color: 'text-violet-600',
      bgColor: 'bg-violet-50',
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
    },
    {
      id: 'conversations',
      name: 'Search Conversations',
      description: 'Search Gladly conversation data',
      icon: Search,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      id: 'ask',
      name: 'Ask About Conversations',
      description: 'AI analysis of conversation data',
      icon: MessageSquare,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
  ];

  const hardwareModes = [
    {
      id: 'neck-fit-modeler',
      name: 'Neck Fit Modeler',
      description: 'Hardware fit modeling tools',
      icon: Cpu,
      color: 'text-slate-700',
      bgColor: 'bg-slate-50',
    },
    {
      id: 'labeling-data',
      name: 'Labeling Data',
      description: 'Activity labeling inventory and durations',
      icon: Tags,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-50',
    },
  ];

  const menus = {
    research: {
      label: 'Product Research',
      shortLabel: 'Research',
      icon: FlaskConical,
      defaultMode: 'churn-trends',
      items: productResearchModes,
      isActive: () => isProductResearchMode(currentMode),
    },
    gladly: {
      label: 'Gladly Conversations',
      shortLabel: 'Gladly',
      icon: null,
      defaultMode: 'conversation-trends',
      items: gladlyModes,
      isActive: () => ['conversations', 'ask', 'conversation-trends'].includes(currentMode),
    },
    hardware: {
      label: 'Hardware',
      shortLabel: 'Hardware',
      icon: Cpu,
      defaultMode: 'neck-fit-modeler',
      items: hardwareModes,
      isActive: () => isHardwareMode(currentMode),
    },
  };

  const clearCloseTimer = () => {
    if (closeTimerRef.current) {
      clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  };

  const scheduleClose = () => {
    clearCloseTimer();
    closeTimerRef.current = setTimeout(() => setOpenMenu(null), 160);
  };

  const openMenuFor = (key) => {
    clearCloseTimer();
    setOpenMenu(key);
  };

  const selectMode = (modeId) => {
    setModeAndUrl(modeId, null);
    setOpenMenu(null);
  };

  const tabBtn = (active) =>
    `shrink-0 md:flex-1 md:min-w-0 px-3 sm:px-4 py-2.5 text-sm font-medium rounded-md transition-colors min-h-[44px] flex items-center justify-center gap-1.5 ${
      active ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'
    }`;

  const renderMenuTab = (key) => {
    const menu = menus[key];
    const Icon = menu.icon;
    const isActive = activeTab === key;
    const isOpen = openMenu === key;

    return (
      <div
        key={key}
        className="relative shrink-0 md:flex-1 md:min-w-0"
        onMouseEnter={() => openMenuFor(key)}
        onMouseLeave={scheduleClose}
      >
        <button
          type="button"
          onClick={() => {
            if (isOpen) {
              setOpenMenu(null);
              return;
            }
            openMenuFor(key);
            if (!menu.isActive()) {
              setModeAndUrl(menu.defaultMode, null);
            }
          }}
          className={`${tabBtn(isActive)} w-full`}
          aria-expanded={isOpen}
          aria-haspopup="menu"
        >
          {Icon ? <Icon className="h-4 w-4 shrink-0 hidden sm:block" /> : null}
          <span className="md:hidden whitespace-nowrap">{menu.shortLabel}</span>
          <span className="hidden md:inline whitespace-nowrap">{menu.label}</span>
          <ChevronDown
            className={`h-3.5 w-3.5 shrink-0 text-gray-400 transition-transform ${
              isOpen ? 'rotate-180' : ''
            }`}
          />
        </button>

        {isOpen ? (
          <div
            role="menu"
            className="absolute left-0 top-full z-50 mt-1 w-72 max-w-[min(18rem,calc(100vw-2rem))] rounded-lg border border-gray-200 bg-white p-1.5 shadow-lg"
            onMouseEnter={clearCloseTimer}
            onMouseLeave={scheduleClose}
          >
            {menu.items.map((mode) => {
              const ItemIcon = mode.icon;
              const itemActive = currentMode === mode.id;
              return (
                <button
                  key={mode.id}
                  type="button"
                  role="menuitem"
                  onClick={() => selectMode(mode.id)}
                  className={`w-full flex items-start gap-3 px-3 py-2.5 rounded-md text-left transition-colors ${
                    itemActive
                      ? `${mode.bgColor} ${mode.color}`
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <ItemIcon
                    className={`h-4 w-4 mt-0.5 shrink-0 ${
                      itemActive ? mode.color : 'text-gray-400'
                    }`}
                  />
                  <span className="min-w-0">
                    <span
                      className={`block text-sm font-medium ${
                        itemActive ? mode.color : 'text-gray-900'
                      }`}
                    >
                      {mode.name}
                    </span>
                    <span className="block text-xs text-gray-500 mt-0.5">
                      {mode.description}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        ) : null}
      </div>
    );
  };

  return (
    <div className="min-w-0 w-full" ref={navRef}>
      <div className="overflow-x-auto min-w-0 -mx-1 px-1 sm:mx-0 sm:px-0 overscroll-x-contain [scrollbar-width:thin]">
        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg flex-nowrap w-max min-w-full md:w-full md:min-w-0">
          <button
            type="button"
            onClick={() => {
              setOpenMenu(null);
              setModeAndUrl('tools', null);
            }}
            className={tabBtn(activeTab === 'home')}
          >
            <Home className="h-4 w-4 shrink-0 hidden sm:block" />
            <span className="whitespace-nowrap">Home</span>
          </button>

          {renderMenuTab('research')}
          {renderMenuTab('gladly')}
          {renderMenuTab('hardware')}

          <button
            type="button"
            onClick={() => {
              setOpenMenu(null);
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
    </div>
  );
};

export default TabNavigation;
