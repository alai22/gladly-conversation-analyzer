import React, { useState, useEffect } from 'react';
import { Download, Database, Bot, TrendingUp, Wrench, Video, Activity, ExternalLink, CircleDot } from 'lucide-react';

const Tools = ({ currentMode, setCurrentMode, adminMode, setAdminMode }) => {
  const [activeSection, setActiveSection] = useState(() => {
    // Determine section based on current mode/adminMode
    if (currentMode === 'neck-fit-modeler') {
      return 'engineering';
    }
    if (adminMode === 'download' || currentMode === 'api-data-manager' || currentMode === 'zoom' || currentMode === 'analytics') {
      return 'data-management';
    }
    if (adminMode === 'claude') {
      return 'admin-tools';
    }
    return 'data-management'; // Default to data management
  });

  // Update active section when mode changes
  useEffect(() => {
    if (currentMode === 'neck-fit-modeler') {
      setActiveSection('engineering');
    } else if (adminMode === 'download' || currentMode === 'api-data-manager' || currentMode === 'zoom' || currentMode === 'analytics') {
      setActiveSection('data-management');
    } else if (adminMode === 'claude') {
      setActiveSection('admin-tools');
    }
  }, [currentMode, adminMode]);

  const dataManagementTools = [
    {
      id: 'api-data-manager',
      name: 'Survicate Download Manager',
      description: 'Download survey data from Survicate API',
      icon: Database,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      action: () => {
        setCurrentMode('api-data-manager');
        setAdminMode(null);
      }
    },
    {
      id: 'download',
      name: 'Gladly Download Manager',
      description: 'Download conversation data from Gladly API',
      icon: Download,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
      borderColor: 'border-orange-200',
      action: () => {
        setAdminMode('download');
        setCurrentMode('tools');
      }
    },
    {
      id: 'zoom',
      name: 'Zoom Download Manager',
      description: 'Download chat messages from Zoom API',
      icon: Video,
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-50',
      borderColor: 'border-indigo-200',
      action: () => {
        setCurrentMode('zoom');
        setAdminMode(null);
      }
    },
    {
      id: 'analytics',
      name: 'Analytics Dashboard',
      description: 'View visitor and pageview analytics',
      icon: Activity,
      color: 'text-cyan-600',
      bgColor: 'bg-cyan-50',
      borderColor: 'border-cyan-200',
      action: () => {
        setCurrentMode('analytics');
        setAdminMode(null);
      }
    },
    {
      id: 'jira-status',
      name: 'Jira connection',
      description: 'Check if Jira (HALO) issues can be fetched for Bug Triage',
      icon: ExternalLink,
      color: 'text-amber-600',
      bgColor: 'bg-amber-50',
      borderColor: 'border-amber-200',
      action: () => {
        setCurrentMode('jira-status');
        setAdminMode(null);
      }
    }
  ];

  const engineeringTools = [
    {
      id: 'neck-fit-modeler',
      name: 'Halo Collar 6 Neck Fit Modeler',
      description: 'Model collar component fit around dog neck cross sections',
      icon: CircleDot,
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-50',
      borderColor: 'border-indigo-200',
      action: () => {
        setCurrentMode('neck-fit-modeler');
        setAdminMode(null);
      }
    }
  ];

  const adminTools = [
    {
      id: 'claude',
      name: 'Claude Chat',
      description: 'Direct Claude API interaction (no RAG)',
      icon: Bot,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      action: () => {
        setAdminMode('claude');
        setCurrentMode('tools');
      }
    },
    {
      id: 'extract-topics',
      name: 'Extract Conversation Topics',
      description: 'Run topic extraction on conversation data',
      icon: TrendingUp,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      borderColor: 'border-purple-200',
      action: () => {
        // This will be handled by SettingsPanel, but we can navigate there
        // For now, just show a message or handle via settings
        alert('Topic extraction is available in Settings > Admin Tools');
      }
    }
  ];

  const isToolActive = (tool) => {
    if (tool.id === 'api-data-manager') {
      return currentMode === 'api-data-manager';
    }
    if (tool.id === 'download') {
      return adminMode === 'download';
    }
    if (tool.id === 'zoom') {
      return currentMode === 'zoom';
    }
    if (tool.id === 'analytics') {
      return currentMode === 'analytics';
    }
    if (tool.id === 'jira-status') {
      return currentMode === 'jira-status';
    }
    if (tool.id === 'neck-fit-modeler') {
      return currentMode === 'neck-fit-modeler';
    }
    if (tool.id === 'claude') {
      return adminMode === 'claude';
    }
    return false;
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Tools</h1>
        <p className="text-gray-600 mt-1">Manage data downloads and admin tools</p>
      </div>

      {/* Section Tabs */}
      <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg mb-6">
        <button
          onClick={() => setActiveSection('data-management')}
          className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
            activeSection === 'data-management'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Data Management
        </button>
        <button
          onClick={() => setActiveSection('engineering')}
          className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
            activeSection === 'engineering'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Engineering
        </button>
        <button
          onClick={() => setActiveSection('admin-tools')}
          className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
            activeSection === 'admin-tools'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Admin Tools
        </button>
      </div>

      {/* Data Management Section */}
      {activeSection === 'data-management' && (
        <div className="space-y-4">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Data Management</h2>
            <p className="text-sm text-gray-600">Download and manage data from external APIs</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {dataManagementTools.map((tool) => {
              const Icon = tool.icon;
              const isActive = isToolActive(tool);
              
              return (
                <button
                  key={tool.id}
                  onClick={tool.action}
                  className={`p-6 border-2 rounded-lg text-left transition-all hover:shadow-md ${
                    isActive
                      ? `${tool.bgColor} ${tool.borderColor} border-2`
                      : 'bg-white border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-start space-x-4">
                    <div className={`p-3 rounded-lg ${isActive ? tool.bgColor : 'bg-gray-50'}`}>
                      <Icon className={`h-6 w-6 ${isActive ? tool.color : 'text-gray-600'}`} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className={`text-lg font-semibold ${isActive ? tool.color : 'text-gray-900'}`}>
                          {tool.name}
                        </h3>
                        {isActive && (
                          <span className={`text-xs px-2 py-1 rounded ${tool.bgColor} ${tool.color} font-medium`}>
                            Active
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600">{tool.description}</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Engineering Section */}
      {activeSection === 'engineering' && (
        <div className="space-y-4">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Engineering</h2>
            <p className="text-sm text-gray-600">Mechanical modeling and product design tools</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {engineeringTools.map((tool) => {
              const Icon = tool.icon;
              const isActive = isToolActive(tool);

              return (
                <button
                  key={tool.id}
                  onClick={tool.action}
                  className={`p-6 border-2 rounded-lg text-left transition-all hover:shadow-md ${
                    isActive
                      ? `${tool.bgColor} ${tool.borderColor} border-2`
                      : 'bg-white border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-start space-x-4">
                    <div className={`p-3 rounded-lg ${isActive ? tool.bgColor : 'bg-gray-50'}`}>
                      <Icon className={`h-6 w-6 ${isActive ? tool.color : 'text-gray-600'}`} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className={`text-lg font-semibold ${isActive ? tool.color : 'text-gray-900'}`}>
                          {tool.name}
                        </h3>
                        {isActive && (
                          <span className={`text-xs px-2 py-1 rounded ${tool.bgColor} ${tool.color} font-medium`}>
                            Active
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600">{tool.description}</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Admin Tools Section */}
      {activeSection === 'admin-tools' && (
        <div className="space-y-4">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Admin Tools</h2>
            <p className="text-sm text-gray-600">Processing and analysis tools</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {adminTools.map((tool) => {
              const Icon = tool.icon;
              const isActive = isToolActive(tool);
              
              return (
                <button
                  key={tool.id}
                  onClick={tool.action}
                  className={`p-6 border-2 rounded-lg text-left transition-all hover:shadow-md ${
                    isActive
                      ? `${tool.bgColor} ${tool.borderColor} border-2`
                      : 'bg-white border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-start space-x-4">
                    <div className={`p-3 rounded-lg ${isActive ? tool.bgColor : 'bg-gray-50'}`}>
                      <Icon className={`h-6 w-6 ${isActive ? tool.color : 'text-gray-600'}`} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className={`text-lg font-semibold ${isActive ? tool.color : 'text-gray-900'}`}>
                          {tool.name}
                        </h3>
                        {isActive && (
                          <span className={`text-xs px-2 py-1 rounded ${tool.bgColor} ${tool.color} font-medium`}>
                            Active
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600">{tool.description}</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default Tools;

