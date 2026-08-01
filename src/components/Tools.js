import React from 'react';
import {
  Download,
  Database,
  Bot,
  TrendingUp,
  Video,
  Activity,
  ExternalLink,
  Tags,
  Search,
  MessageSquare,
  BarChart3,
  FileText,
  Users,
  ClipboardList,
  Cpu,
  Bug,
  Home,
} from 'lucide-react';

const Tools = ({ currentMode, setCurrentMode, adminMode, setAdminMode }) => {
  const openTool = (mode, nextAdminMode = null) => {
    setAdminMode(nextAdminMode);
    setCurrentMode(mode);
  };

  const sections = [
    {
      id: 'research',
      title: 'Product Research',
      description: 'Churn, surveys, and interviews',
      tools: [
        {
          id: 'churn-trends',
          name: 'Churn Trends',
          description: 'Visualize cancellation trends',
          icon: BarChart3,
          color: 'text-red-600',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          action: () => openTool('churn-trends'),
        },
        {
          id: 'survicate',
          name: 'Ask About Churn',
          description: 'AI analysis of cancellation surveys',
          icon: FileText,
          color: 'text-teal-600',
          bgColor: 'bg-teal-50',
          borderColor: 'border-teal-200',
          action: () => openTool('survicate'),
        },
        {
          id: 'survey-manager',
          name: 'Survicate Surveys',
          description: 'Browse and manage Survicate survey data',
          icon: ClipboardList,
          color: 'text-orange-600',
          bgColor: 'bg-orange-50',
          borderColor: 'border-orange-200',
          action: () => openTool('survey-manager'),
        },
        {
          id: 'halo-surveys',
          name: 'Halo Surveys',
          description: 'Design and publish branded survey campaigns',
          icon: ClipboardList,
          color: 'text-amber-600',
          bgColor: 'bg-amber-50',
          borderColor: 'border-amber-200',
          action: () => openTool('halo-surveys'),
        },
        {
          id: 'text-interview',
          name: 'Text Interviews',
          description: 'Run structured text-based research interviews',
          icon: Users,
          color: 'text-violet-600',
          bgColor: 'bg-violet-50',
          borderColor: 'border-violet-200',
          action: () => openTool('text-interview'),
        },
      ],
    },
    {
      id: 'gladly',
      title: 'Gladly Conversations',
      description: 'Search and analyze support conversations',
      tools: [
        {
          id: 'conversation-trends',
          name: 'Conversation Trends',
          description: 'Visualize conversation topic trends',
          icon: TrendingUp,
          color: 'text-blue-600',
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200',
          action: () => openTool('conversation-trends'),
        },
        {
          id: 'conversations',
          name: 'Search Conversations',
          description: 'Search Gladly conversation data',
          icon: Search,
          color: 'text-green-600',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          action: () => openTool('conversations'),
        },
        {
          id: 'ask',
          name: 'Ask About Conversations',
          description: 'AI analysis of conversation data',
          icon: MessageSquare,
          color: 'text-purple-600',
          bgColor: 'bg-purple-50',
          borderColor: 'border-purple-200',
          action: () => openTool('ask'),
        },
      ],
    },
    {
      id: 'hardware',
      title: 'Hardware & ML',
      description: 'Device modeling and labeling pipelines',
      tools: [
        {
          id: 'neck-fit-modeler',
          name: 'Neck Fit Modeler',
          description: 'Hardware fit modeling tools',
          icon: Cpu,
          color: 'text-slate-700',
          bgColor: 'bg-slate-50',
          borderColor: 'border-slate-200',
          action: () => openTool('neck-fit-modeler'),
        },
        {
          id: 'labeling-data',
          name: 'Labeling Data',
          description: 'Activity labeling inventory, process staging, duration totals',
          icon: Tags,
          color: 'text-emerald-600',
          bgColor: 'bg-emerald-50',
          borderColor: 'border-emerald-200',
          action: () => openTool('labeling-data'),
        },
      ],
    },
    {
      id: 'data',
      title: 'Data & integrations',
      description: 'Downloads, analytics, and connected services',
      tools: [
        {
          id: 'api-data-manager',
          name: 'Survicate Download Manager',
          description: 'Download survey data from Survicate API',
          icon: Database,
          color: 'text-blue-600',
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200',
          action: () => openTool('api-data-manager'),
        },
        {
          id: 'download',
          name: 'Gladly Download Manager',
          description: 'Download conversation data from Gladly API',
          icon: Download,
          color: 'text-orange-600',
          bgColor: 'bg-orange-50',
          borderColor: 'border-orange-200',
          action: () => openTool('tools', 'download'),
        },
        {
          id: 'zoom',
          name: 'Zoom Download Manager',
          description: 'Download chat messages from Zoom API',
          icon: Video,
          color: 'text-indigo-600',
          bgColor: 'bg-indigo-50',
          borderColor: 'border-indigo-200',
          action: () => openTool('zoom'),
        },
        {
          id: 'analytics',
          name: 'Analytics Dashboard',
          description: 'View visitor and pageview analytics',
          icon: Activity,
          color: 'text-cyan-600',
          bgColor: 'bg-cyan-50',
          borderColor: 'border-cyan-200',
          action: () => openTool('analytics'),
        },
        {
          id: 'jira-status',
          name: 'Jira connection',
          description: 'Check if Jira (HALO) issues can be fetched for Bug Triage',
          icon: ExternalLink,
          color: 'text-amber-600',
          bgColor: 'bg-amber-50',
          borderColor: 'border-amber-200',
          action: () => openTool('jira-status'),
        },
      ],
    },
    {
      id: 'engineering',
      title: 'Engineering',
      description: 'Triage and internal utilities',
      tools: [
        {
          id: 'bug-triage',
          name: 'Bug Triage',
          description: 'Triage HALO issues with Jira context',
          icon: Bug,
          color: 'text-rose-600',
          bgColor: 'bg-rose-50',
          borderColor: 'border-rose-200',
          action: () => openTool('bug-triage'),
        },
        {
          id: 'claude',
          name: 'Claude Chat',
          description: 'Direct Claude API interaction (no RAG)',
          icon: Bot,
          color: 'text-blue-600',
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200',
          action: () => openTool('tools', 'claude'),
        },
      ],
    },
  ];

  const isToolActive = (tool) => {
    if (tool.id === 'download') return adminMode === 'download';
    if (tool.id === 'claude') return adminMode === 'claude';
    if (tool.id === 'tools') return false;
    return currentMode === tool.id && !adminMode;
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-lg bg-gray-100">
            <Home className="h-5 w-5 text-gray-700" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Halo Insight</h1>
        </div>
        <p className="text-gray-600">
          Pick a tool to get started. Use the top tabs as shortcuts into each area.
        </p>
      </div>

      <div className="space-y-10">
        {sections.map((section) => (
          <section key={section.id}>
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-gray-900">{section.title}</h2>
              <p className="text-sm text-gray-500">{section.description}</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {section.tools.map((tool) => {
                const Icon = tool.icon;
                const isActive = isToolActive(tool);

                return (
                  <button
                    key={tool.id}
                    type="button"
                    onClick={tool.action}
                    className={`p-5 border-2 rounded-lg text-left transition-all hover:shadow-md ${
                      isActive
                        ? `${tool.bgColor} ${tool.borderColor}`
                        : 'bg-white border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-start space-x-4">
                      <div className={`p-3 rounded-lg ${isActive ? tool.bgColor : 'bg-gray-50'}`}>
                        <Icon className={`h-5 w-5 ${isActive ? tool.color : 'text-gray-600'}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <h3
                            className={`text-base font-semibold ${
                              isActive ? tool.color : 'text-gray-900'
                            }`}
                          >
                            {tool.name}
                          </h3>
                          {isActive ? (
                            <span
                              className={`text-xs px-2 py-1 rounded shrink-0 ${tool.bgColor} ${tool.color} font-medium`}
                            >
                              Active
                            </span>
                          ) : null}
                        </div>
                        <p className="text-sm text-gray-600">{tool.description}</p>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
};

export default Tools;
