import React, { useState, useEffect, useCallback } from 'react';
import { Database, RefreshCw, CheckCircle, XCircle, Download, FileDown, ChevronDown, ChevronUp, X } from 'lucide-react';
import { getSurvicateDataSource } from '../utils/constants';

const Sidebar = ({ healthStatus, onRefreshHealth, currentMode, setAdminMode, setCurrentMode, onCloseSettings, mobileDrawerOpen = false, onCloseMobile }) => {
  const [downloadStats, setDownloadStats] = useState(null);
  const [surveyStats, setSurveyStats] = useState(null);
  const [dataSource, setDataSource] = useState(getSurvicateDataSource());
  const [cacheStatus, setCacheStatus] = useState(null);
  const [isDataManagementExpanded, setIsDataManagementExpanded] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [augmentedFiles, setAugmentedFiles] = useState([]);
  const [rawFiles, setRawFiles] = useState([]);
  const [selectedFileKey, setSelectedFileKey] = useState(
    localStorage.getItem('survicate_selected_file_key') || 'latest'
  );
  const [isAugmenting, setIsAugmenting] = useState(false);

  // Fetch download stats
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('/api/download/stats');
        const data = await response.json();
        if (data.status === 'success') {
          setDownloadStats(data.data);
        }
      } catch (error) {
        console.error('Error fetching download stats:', error);
      }
    };

    fetchStats();
    // Refresh every 30 seconds
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  // Fetch cache status function (memoized with useCallback)
  const fetchCacheStatus = useCallback(async () => {
    if ((currentMode === 'survicate' || currentMode === 'churn-trends') && dataSource === 'api') {
      try {
        const response = await fetch('/api/survicate/cache-status');
        const data = await response.json();
        if (data.success) {
          setCacheStatus(data.cache_status);
        } else {
          // Show error but don't switch modes - let user see the error and fix it
          console.error('Cache status error:', data.error);
          setCacheStatus({
            ...data.cache_status,
            refresh_error: data.error || 'Failed to fetch cache status'
          });
        }
      } catch (error) {
        console.error('Error fetching cache status:', error);
        setCacheStatus({
          refresh_error: `Network error: ${error.message}`
        });
      }
    } else {
      setCacheStatus(null);
    }
  }, [currentMode, dataSource]);

  // Fetch survey stats when in survicate or churn-trends mode
  useEffect(() => {
    const fetchSurveyStats = async () => {
      if (currentMode === 'survicate' || currentMode === 'churn-trends') {
        try {
          const response = await fetch(`/api/survicate/summary?data_source=${dataSource}`);
          const data = await response.json();
          if (data.success) {
            setSurveyStats(data.summary);
          } else {
            // Show error but don't switch modes - let user see the error and fix it
            console.error('Survey stats error:', data.error);
            setSurveyStats({
              total_responses: 0,
              error: data.error || 'Failed to fetch survey stats'
            });
          }
        } catch (error) {
          console.error('Error fetching survey stats:', error);
          setSurveyStats({
            total_responses: 0,
            error: `Network error: ${error.message}`
          });
        }
      } else {
        setSurveyStats(null);
      }
    };

    fetchSurveyStats();
  }, [currentMode, dataSource]);

  // Fetch cache status when in API mode
  useEffect(() => {
    fetchCacheStatus();
    // Poll cache status every 10 seconds when in API mode
    if ((currentMode === 'survicate' || currentMode === 'churn-trends') && dataSource === 'api') {
      const interval = setInterval(fetchCacheStatus, 10000);
      return () => clearInterval(interval);
    }
  }, [currentMode, dataSource, fetchCacheStatus]);

  // Fetch augmented files list when in API mode
  useEffect(() => {
    const fetchAugmentedFiles = async () => {
      if ((currentMode === 'survicate' || currentMode === 'churn-trends') && dataSource === 'api') {
        try {
          const response = await fetch('/api/survicate/augmented-files');
          const data = await response.json();
          if (data.success) {
            setAugmentedFiles(data.files || []);
          }
        } catch (error) {
          console.error('Error fetching augmented files:', error);
        }
      } else {
        setAugmentedFiles([]);
      }
    };

    fetchAugmentedFiles();
    // Refresh files list every 30 seconds when in API mode
    if ((currentMode === 'survicate' || currentMode === 'churn-trends') && dataSource === 'api') {
      const interval = setInterval(fetchAugmentedFiles, 30000);
      return () => clearInterval(interval);
    }
  }, [currentMode, dataSource]);

  // Fetch raw files list when in API mode
  useEffect(() => {
    const fetchRawFiles = async () => {
      if ((currentMode === 'survicate' || currentMode === 'churn-trends') && dataSource === 'api') {
        try {
          const response = await fetch('/api/survicate/raw-files');
          const data = await response.json();
          if (data.success) {
            setRawFiles(data.files || []);
          }
        } catch (error) {
          console.error('Error fetching raw files:', error);
        }
      } else {
        setRawFiles([]);
      }
    };

    fetchRawFiles();
    // Refresh files list every 30 seconds when in API mode
    if ((currentMode === 'survicate' || currentMode === 'churn-trends') && dataSource === 'api') {
      const interval = setInterval(fetchRawFiles, 30000);
      return () => clearInterval(interval);
    }
  }, [currentMode, dataSource]);

  const handleFileSelectionChange = (fileKey) => {
    setSelectedFileKey(fileKey);
    localStorage.setItem('survicate_selected_file_key', fileKey);
    // Trigger chart refresh by reloading the page data
    if (currentMode === 'churn-trends') {
      // Force chart refresh by triggering a custom event
      window.dispatchEvent(new CustomEvent('survicate-file-changed', { detail: { fileKey } }));
    }
  };

  const handleTriggerAugmentation = async (rawFileKey) => {
    if (isAugmenting) return;
    
    setIsAugmenting(true);
    try {
      const response = await fetch('/api/survicate/augment', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          raw_file_key: rawFileKey
        }),
      });
      
      const data = await response.json();
      if (data.success) {
        alert('Augmentation started in background. This may take a few minutes. The augmented file will appear when complete.');
        // Refresh files list after a delay
        setTimeout(() => {
          fetch('/api/survicate/augmented-files')
            .then(res => res.json())
            .then(data => {
              if (data.success) {
                setAugmentedFiles(data.files || []);
              }
            })
            .catch(err => console.error('Error refreshing augmented files:', err));
        }, 5000);
      } else {
        alert(data.error || 'Failed to start augmentation');
      }
    } catch (error) {
      console.error('Error triggering augmentation:', error);
      alert('Failed to trigger augmentation');
    } finally {
      setIsAugmenting(false);
    }
  };

  const handleDataSourceChange = async (newSource) => {
    setDataSource(newSource);
    localStorage.setItem('survicate_data_source', newSource);
    
    // Refresh survey stats with new source
    if (currentMode === 'survicate' || currentMode === 'churn-trends') {
      try {
        const response = await fetch(`/api/survicate/summary?data_source=${newSource}`);
        const data = await response.json();
        if (data.success) {
          setSurveyStats(data.summary);
        }
      } catch (error) {
        console.error('Error refreshing survey stats:', error);
      }
    }
  };

  const handleDownloadFromApi = async () => {
    if (isRefreshing) return;
    
    setIsRefreshing(true);
    try {
      const response = await fetch('/api/survicate/refresh-api', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      const data = await response.json();
      if (data.success) {
        // Refresh cache status and survey stats after a short delay
        setTimeout(() => {
          fetchCacheStatus();
          // Also refresh survey stats to show updated data
          fetch(`/api/survicate/summary?data_source=api`)
            .then(res => res.json())
            .then(data => {
              if (data.success) {
                setSurveyStats(data.summary);
              }
            })
            .catch(err => console.error('Error refreshing survey stats:', err));
        }, 1000);
      } else {
        alert(data.message || 'Failed to download from API');
      }
    } catch (error) {
      console.error('Error downloading from API:', error);
      alert('Failed to download from API');
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleReloadCache = async () => {
    try {
      const response = await fetch('/api/survicate/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          data_source: 'api'
        }),
      });
      
      const data = await response.json();
      if (data.success) {
        // Refresh survey stats to show reloaded data
        const summaryResponse = await fetch(`/api/survicate/summary?data_source=api`);
        const summaryData = await summaryResponse.json();
        if (summaryData.success) {
          setSurveyStats(summaryData.summary);
        }
        // Also refresh cache status
        fetchCacheStatus();
      } else {
        alert(data.error || 'Failed to reload cache');
      }
    } catch (error) {
      console.error('Error reloading cache:', error);
      alert('Failed to reload cache');
    }
  };

  const getHealthStatusIcon = () => {
    if (!healthStatus) return <RefreshCw className="h-4 w-4 animate-spin" />;
    if (healthStatus.status === 'healthy') return <CheckCircle className="h-4 w-4 text-green-500" />;
    return <XCircle className="h-4 w-4 text-red-500" />;
  };

  const getHealthStatusText = () => {
    if (!healthStatus) return 'Checking...';
    if (healthStatus.status === 'healthy') return 'Connected';
    
    // Build detailed status message
    const issues = [];
    
    if (!healthStatus.claude_initialized) {
      issues.push('Claude API');
    }
    if (!healthStatus.conversation_analyzer_initialized) {
      issues.push('Conversation Analyzer');
    }
    
    // Note about S3 on localhost
    if (healthStatus.storage_type === 's3' && !healthStatus.storage_available) {
      // S3 not configured, but this is expected on localhost
      const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
      if (isLocalhost) {
        // Don't add S3 to issues list on localhost - it's expected
      } else {
        issues.push('S3 Storage');
      }
    }
    
    if (issues.length === 0) {
      return 'Disconnected';
    }
    
    return `Disconnected: ${issues.join(', ')}`;
  };

  const getHealthStatusColor = () => {
    if (!healthStatus) return 'text-gray-500';
    if (healthStatus.status === 'healthy') return 'text-green-600';
    
    // For localhost with S3 unavailable, use yellow/warning instead of red
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (isLocalhost && healthStatus.storage_type === 's3' && !healthStatus.storage_available) {
      // If only S3 is unavailable on localhost, and other services are OK, use warning color
      if (healthStatus.claude_initialized && healthStatus.conversation_analyzer_initialized) {
        return 'text-yellow-600';
      }
    }
    
    return 'text-red-600';
  };

  const getHealthStatusDetails = () => {
    if (!healthStatus || healthStatus.status === 'healthy') return null;
    
    const details = [];
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    
    // Claude status
    if (!healthStatus.claude_initialized) {
      details.push('Claude API: Not initialized (check ANTHROPIC_API_KEY)');
    }
    
    // Conversation analyzer status
    if (!healthStatus.conversation_analyzer_initialized) {
      details.push('Conversation Analyzer: Not available');
    }
    
    // Storage status with helpful context
    if (healthStatus.storage_type === 's3') {
      if (!healthStatus.storage_available) {
        if (isLocalhost) {
          details.push('S3 Storage: Not configured (expected on localhost - using local files)');
        } else {
          details.push('S3 Storage: Not configured (check S3_BUCKET_NAME)');
        }
      } else {
        if (isLocalhost) {
          details.push('S3 Storage: Configured (may not be accessible on localhost)');
        }
      }
    } else if (healthStatus.storage_type === 'local') {
      details.push('Storage: Using local files');
    }
    
    if (healthStatus.error) {
      details.push(`Error: ${healthStatus.error}`);
    }
    
    return details.length > 0 ? details : null;
  };

  return (
    <div
      className={`
        bg-white shadow-lg border-r border-gray-200 flex flex-col w-64 shrink-0 overflow-y-auto
        fixed inset-y-0 left-0 z-50 h-full max-w-[min(20rem,calc(100vw-2rem))]
        transition-transform duration-200 ease-out
        md:relative md:inset-auto md:z-auto md:h-auto md:max-w-none md:translate-x-0
        ${mobileDrawerOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}
    >
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-start justify-between gap-2 mb-4">
          <button
            type="button"
            onClick={() => {
              setAdminMode?.(null);
              setCurrentMode?.('tools');
              onCloseMobile?.();
            }}
            className="flex items-center space-x-3 min-w-0 text-left rounded-lg hover:bg-gray-50 -m-1 p-1 transition-colors"
            title="Go to Home"
          >
            <img 
              src="/dog-spark.jpg" 
              alt="Halo Insight Logo" 
              className="h-10 w-10 rounded-full object-cover shrink-0"
            />
            <div className="min-w-0">
              <h2 className="text-lg font-semibold text-gray-900">Halo Insight</h2>
              <p className="text-sm text-gray-500">Customer Intelligence</p>
            </div>
          </button>
          {onCloseMobile && (
            <button
              type="button"
              onClick={onCloseMobile}
              className="md:hidden shrink-0 p-2 -mr-2 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-800"
              aria-label="Close menu"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>
        
        {/* Health Status */}
        <div className="space-y-2">
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
          {getHealthStatusDetails() && (
            <div className="text-xs text-gray-500 space-y-1 pl-6">
              {getHealthStatusDetails().map((detail, index) => (
                <div key={index}>{detail}</div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Conversation Stats - Only show in Gladly Conversations mode */}
      {downloadStats && (currentMode === 'conversations' || currentMode === 'ask') && (
        <div className="p-6 border-t border-gray-200">
          <div className="text-xs text-gray-500">
            <div className="mb-2">
              <strong>Conversations:</strong>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Available</span>
                <span className="font-semibold text-blue-600">{downloadStats.total_in_csv?.toLocaleString() || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Downloaded</span>
                <span className="font-semibold text-green-600">{downloadStats.total_downloaded?.toLocaleString() || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Remaining</span>
                <span className="font-semibold text-yellow-600">{downloadStats.remaining?.toLocaleString() || 0}</span>
              </div>
              {downloadStats.completion_percentage !== undefined && (
                <div className="mt-2">
                  <div className="w-full bg-gray-200 rounded-full h-1.5">
                    <div 
                      className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                      style={{ width: `${Math.min(downloadStats.completion_percentage, 100)}%` }}
                    ></div>
                  </div>
                  <div className="text-center mt-1 text-xs">
                    {downloadStats.completion_percentage.toFixed(1)}% Complete
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Churn Trends Stats */}
      {(surveyStats || (currentMode === 'churn-trends' && dataSource === 'api')) && currentMode === 'churn-trends' && (
        <div className="p-6 border-t border-gray-200">
          <div className="text-xs text-gray-500">
            <div className="mb-2">
              <strong>Churn Trends Data:</strong>
            </div>
            {surveyStats?.error ? (
              <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-800">
                <div className="font-semibold mb-1">API Error:</div>
                <div>{surveyStats.error}</div>
                <div className="mt-2 text-xs text-red-700">
                  Check API configuration and try downloading from API using the button above.
                </div>
              </div>
            ) : surveyStats ? (
              <>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Survey Responses</span>
                    <span className="font-semibold text-blue-600">{surveyStats.total_responses?.toLocaleString() || 0}</span>
                  </div>
                  {surveyStats.date_range && (
                    <div className="flex flex-col space-y-1">
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">Start Date</span>
                        <span className="font-semibold text-gray-700 text-xs">
                          {surveyStats.date_range.start !== 'Unknown' ? (
                            new Date(surveyStats.date_range.start).toLocaleDateString()
                          ) : 'N/A'}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">End Date</span>
                        <span className="font-semibold text-gray-700 text-xs">
                          {surveyStats.date_range.end !== 'Unknown' ? (
                            new Date(surveyStats.date_range.end).toLocaleDateString()
                          ) : 'N/A'}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
                {surveyStats.total_responses === 0 && (
                  <div className="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
                    {dataSource === 'api' 
                      ? 'No survey data loaded. Use "Download from API" button above to fetch data.'
                      : 'No survey data loaded. Ensure the CSV file is in the data directory.'}
                  </div>
                )}
              </>
            ) : (
              <div className="text-xs text-gray-400">Loading survey stats...</div>
            )}
          </div>
        </div>
      )}

      {/* Data Source Toggle - Show for survicate and churn-trends modes */}
      {(currentMode === 'survicate' || currentMode === 'churn-trends') && (
        <div className="p-6 border-t border-gray-200">
          <div className="text-xs text-gray-500">
            <div className="mb-2">
              <strong>Data Source:</strong>
            </div>
            <select
              value={dataSource}
              onChange={(e) => handleDataSourceChange(e.target.value)}
              className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="api">API (Live)</option>
              <option value="file">File (CSV)</option>
            </select>
          </div>
        </div>
      )}

      {/* Data Management Section - Collapsible when in API mode */}
      {dataSource === 'api' && (currentMode === 'survicate' || currentMode === 'churn-trends' || currentMode === 'api-data-manager') && (
        <div className="border-t border-gray-200">
          {/* Collapsible Header */}
          <button
            onClick={() => setIsDataManagementExpanded(!isDataManagementExpanded)}
            className="w-full px-6 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center space-x-2">
              <Database className="h-4 w-4 text-gray-600" />
              <span className="text-sm font-semibold text-gray-700">Data Management</span>
            </div>
            {isDataManagementExpanded ? (
              <ChevronUp className="h-4 w-4 text-gray-500" />
            ) : (
              <ChevronDown className="h-4 w-4 text-gray-500" />
            )}
          </button>

          {/* Collapsible Content */}
          {isDataManagementExpanded && (
            <div className="px-6 pb-6 space-y-4">
              {/* Raw Files - Hide when in api-data-manager mode (shown in main area) */}
              {currentMode !== 'api-data-manager' && (currentMode === 'survicate' || currentMode === 'churn-trends') && rawFiles.length > 0 && (
                <div>
                  <div className="text-xs text-gray-500 mb-2">
                    <strong>Downloaded Files:</strong>
                  </div>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {rawFiles.slice(0, 5).map((file) => (
                      <div key={file.key} className="p-2 bg-gray-50 rounded border border-gray-200">
                        <div className="flex justify-between items-start mb-1">
                          <div className="flex-1 min-w-0">
                            <div className="text-xs font-medium text-gray-700 truncate" title={file.display_name}>
                              {file.display_name}
                            </div>
                            <div className="text-xs text-gray-500 mt-0.5">
                              {file.response_count.toLocaleString()} responses • {new Date(file.last_modified).toLocaleString()}
                            </div>
                          </div>
                          <div className="flex items-center space-x-1 ml-2">
                            <a
                              href={`/api/survicate/raw-files/download?file_key=${encodeURIComponent(file.key)}`}
                              download={file.display_name}
                              className="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 flex items-center space-x-1"
                              title="Download CSV file"
                            >
                              <FileDown className="h-3 w-3" />
                              <span>Download</span>
                            </a>
                            {!file.has_augmentation && (
                              <button
                                onClick={() => handleTriggerAugmentation(file.key)}
                                disabled={isAugmenting}
                                className="px-2 py-1 text-xs bg-purple-500 text-white rounded hover:bg-purple-600 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center space-x-1"
                                title="Run augmentation with LLM"
                              >
                                {isAugmenting ? (
                                  <RefreshCw className="h-3 w-3 animate-spin" />
                                ) : (
                                  <span>Augment</span>
                                )}
                              </button>
                            )}
                            {file.has_augmentation && (
                              <span className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded">
                                Augmented
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                    {rawFiles.length > 5 && (
                      <div className="text-xs text-gray-400 text-center">
                        +{rawFiles.length - 5} more files
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Augmented File Selection - Hide when in api-data-manager mode (shown in main area) */}
              {currentMode !== 'api-data-manager' && (currentMode === 'survicate' || currentMode === 'churn-trends') && augmentedFiles.length > 0 && (
                <div>
                  <div className="text-xs text-gray-500 mb-2">
                    <strong>Augmented File:</strong>
                  </div>
                  <select
                    value={selectedFileKey}
                    onChange={(e) => handleFileSelectionChange(e.target.value)}
                    className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="latest">Latest ({augmentedFiles[0]?.response_count || 0} responses)</option>
                    {augmentedFiles.map((file) => (
                      <option key={file.key} value={file.key}>
                        {file.display_name} ({file.response_count} responses) - {new Date(file.timestamp).toLocaleString()}
                      </option>
                    ))}
                  </select>
                  {augmentedFiles.length > 1 && (
                    <div className="mt-1 text-xs text-gray-400">
                      {augmentedFiles.length} files available
                    </div>
                  )}
                </div>
              )}

              {/* Cache Status */}
              <div>
                <div className="text-xs text-gray-500 mb-2">
                  <strong>Cache Status:</strong>
                </div>
                {cacheStatus ? (
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">Status</span>
                      <span className={`font-semibold ${cacheStatus.is_fresh ? 'text-green-600' : 'text-yellow-600'}`}>
                        {cacheStatus.is_fresh ? 'Fresh' : 'Stale'}
                      </span>
                    </div>
                    {cacheStatus.cache_age_hours !== null && (
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">Age</span>
                        <span className="font-semibold text-gray-700">
                          {Math.round(cacheStatus.cache_age_hours)}h ago
                        </span>
                      </div>
                    )}
                    {cacheStatus.refresh_in_progress && (
                      <div className="flex items-center text-blue-600 mt-2">
                        <RefreshCw className="h-3 w-3 animate-spin mr-1" />
                        <span className="text-xs">Downloading from API...</span>
                      </div>
                    )}
                    {cacheStatus.refresh_error && (
                      <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-800">
                        Error: {cacheStatus.refresh_error}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-xs text-gray-400 mb-2">Loading cache status...</div>
                )}
                
                {/* Action Buttons - Hide when in api-data-manager mode (shown in main area) */}
                {currentMode !== 'api-data-manager' && (
                  <div className="mt-3 space-y-2">
                    <button
                      onClick={handleDownloadFromApi}
                      disabled={isRefreshing || (cacheStatus && cacheStatus.refresh_in_progress)}
                      className="w-full px-3 py-2 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center space-x-1"
                      title="Download fresh data from Survicate API and save to cache"
                    >
                      <Download className={`h-3 w-3 ${(isRefreshing || (cacheStatus && cacheStatus.refresh_in_progress)) ? 'animate-spin' : ''}`} />
                      <span>Download from API</span>
                    </button>
                    <button
                      onClick={handleReloadCache}
                      disabled={isRefreshing || (cacheStatus && cacheStatus.refresh_in_progress)}
                      className="w-full px-3 py-2 text-xs bg-green-500 text-white rounded hover:bg-green-600 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center space-x-1"
                      title="Reload data from existing cache (use already downloaded data)"
                    >
                      <RefreshCw className="h-3 w-3" />
                      <span>Reload Cache</span>
                    </button>
                  </div>
                )}
                {/* Link to Data Manager when in API mode but not already there */}
                {currentMode !== 'api-data-manager' && (currentMode === 'survicate' || currentMode === 'churn-trends') && (
                  <div className="mt-3">
                    <button
                      onClick={() => {
                        setCurrentMode('api-data-manager');
                        onCloseMobile?.();
                      }}
                      className="w-full px-3 py-2 text-xs bg-purple-500 text-white rounded hover:bg-purple-600 flex items-center justify-center space-x-1"
                      title="Open Data Management in main area"
                    >
                      <Database className="h-3 w-3" />
                      <span>Manage Data</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Survey Stats */}
      {(surveyStats || (currentMode === 'survicate' && dataSource === 'api')) && currentMode === 'survicate' && (
        <div className="p-6 border-t border-gray-200">
          <div className="text-xs text-gray-500">
            <div className="mb-2">
              <strong>Survey Responses:</strong>
            </div>
            {surveyStats?.error ? (
              <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-800">
                <div className="font-semibold mb-1">API Error:</div>
                <div>{surveyStats.error}</div>
                <div className="mt-2 text-xs text-red-700">
                  Check API configuration and try downloading from API using the button above.
                </div>
              </div>
            ) : surveyStats ? (
              <>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Available in RAG</span>
                    <span className="font-semibold text-blue-600">{surveyStats.total_responses?.toLocaleString() || 0}</span>
                  </div>
                  {surveyStats.date_range && (
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">Date Range</span>
                      <span className="font-semibold text-gray-700 text-xs">
                        {surveyStats.date_range.start !== 'Unknown' && surveyStats.date_range.end !== 'Unknown' ? (
                          <>{new Date(surveyStats.date_range.start).toLocaleDateString()} - {new Date(surveyStats.date_range.end).toLocaleDateString()}</>
                        ) : 'N/A'}
                      </span>
                    </div>
                  )}
                </div>
                {surveyStats.total_responses === 0 && (
                  <div className="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
                    {dataSource === 'api' 
                      ? 'No survey data loaded. Use "Download from API" button above to fetch data.'
                      : 'No survey data loaded. Ensure the CSV file is in the data directory.'}
                  </div>
                )}
              </>
            ) : (
              <div className="text-xs text-gray-400">Loading survey stats...</div>
            )}
          </div>
        </div>
      )}

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
            {healthStatus?.error && !healthStatus.claude_initialized && (
              <div className="ml-4 text-xs text-red-600 mt-1">
                {healthStatus.error}
              </div>
            )}
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
