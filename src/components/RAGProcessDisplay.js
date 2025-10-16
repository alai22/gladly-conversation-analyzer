import React, { useState } from 'react';
import { CheckCircle, Clock, AlertCircle, Brain, Database, Search, BarChart3, ChevronDown, ChevronRight } from 'lucide-react';

const RAGProcessDisplay = ({ ragProcess, isVisible = true }) => {
  const [expandedSteps, setExpandedSteps] = useState({});
  const [showDetails, setShowDetails] = useState(false);

  if (!ragProcess || !isVisible) return null;

  const toggleStepExpansion = (stepNumber) => {
    setExpandedSteps(prev => ({
      ...prev,
      [stepNumber]: !prev[stepNumber]
    }));
  };

  const getStepIcon = (step, status) => {
    if (status === 'completed') return <CheckCircle className="h-5 w-5 text-green-500" />;
    if (status === 'running') return <Clock className="h-5 w-5 text-blue-500 animate-spin" />;
    if (status === 'error') return <AlertCircle className="h-5 w-5 text-red-500" />;
    return <Clock className="h-5 w-5 text-gray-400" />;
  };

  const getStepIconByNumber = (stepNumber) => {
    switch (stepNumber) {
      case 1: return <Brain className="h-4 w-4" />;
      case 2: return <Search className="h-4 w-4" />;
      case 3: return <BarChart3 className="h-4 w-4" />;
      default: return <Database className="h-4 w-4" />;
    }
  };

  const formatSearchTerms = (terms) => {
    if (!terms || terms.length === 0) return 'None';
    return terms.slice(0, 5).join(', ') + (terms.length > 5 ? ` (+${terms.length - 5} more)` : '');
  };

  const formatContentTypes = (types) => {
    if (!types || types.length === 0) return 'All types';
    return types.join(', ');
  };

  return (
    <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Brain className="h-5 w-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">RAG Process</h3>
          <span className="text-sm text-gray-600">(Retrieval-Augmented Generation)</span>
        </div>
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-sm text-blue-600 hover:text-blue-800 flex items-center space-x-1"
        >
          {showDetails ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          <span>{showDetails ? 'Hide' : 'Show'} Details</span>
        </button>
      </div>

      {/* Process Steps */}
      <div className="space-y-3">
        {ragProcess.steps?.map((step) => (
          <div key={step.step} className="bg-white rounded-lg p-3 border border-gray-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                {getStepIcon(step.step, step.status)}
                <div className="flex items-center space-x-2">
                  {getStepIconByNumber(step.step)}
                  <div>
                    <div className="font-medium text-gray-900">
                      Step {step.step}: {step.name}
                    </div>
                    <div className="text-sm text-gray-600">{step.description}</div>
                  </div>
                </div>
              </div>
              <button
                onClick={() => toggleStepExpansion(step.step)}
                className="text-gray-400 hover:text-gray-600"
              >
                {expandedSteps[step.step] ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </button>
            </div>

            {/* Step Details */}
            {expandedSteps[step.step] && step.details && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                {step.step === 1 && (
                  <div className="space-y-2">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <div className="text-sm font-medium text-gray-700">Search Terms</div>
                        <div className="text-sm text-gray-600">{formatSearchTerms(step.details.search_terms)}</div>
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-700">Content Types</div>
                        <div className="text-sm text-gray-600">{formatContentTypes(step.details.content_types)}</div>
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-700">Time Filter</div>
                        <div className="text-sm text-gray-600">{step.details.time_filters}</div>
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-700">Max Items</div>
                        <div className="text-sm text-gray-600">{step.details.max_items}</div>
                      </div>
                    </div>
                    <div>
                      <div className="text-sm font-medium text-gray-700">Analysis Focus</div>
                      <div className="text-sm text-gray-600">{step.details.analysis_focus}</div>
                    </div>
                    {step.warning && (
                      <div className="bg-yellow-50 border border-yellow-200 rounded p-2">
                        <div className="text-sm text-yellow-800">{step.warning}</div>
                      </div>
                    )}
                  </div>
                )}

                {step.step === 2 && (
                  <div className="space-y-2">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="bg-blue-50 p-2 rounded">
                        <div className="text-sm font-medium text-blue-800">Total Searched</div>
                        <div className="text-lg font-bold text-blue-900">{step.details.total_searched}</div>
                      </div>
                      <div className="bg-green-50 p-2 rounded">
                        <div className="text-sm font-medium text-green-800">Final Count</div>
                        <div className="text-lg font-bold text-green-900">{step.details.final_count}</div>
                      </div>
                      <div className="bg-orange-50 p-2 rounded">
                        <div className="text-sm font-medium text-orange-800">Duplicates Removed</div>
                        <div className="text-lg font-bold text-orange-900">{step.details.duplicates_removed}</div>
                      </div>
                      <div className="bg-red-50 p-2 rounded">
                        <div className="text-sm font-medium text-red-800">Filtered Out</div>
                        <div className="text-lg font-bold text-red-900">{step.details.filtered_out}</div>
                      </div>
                    </div>
                    
                    {Object.keys(step.details.by_content_type).length > 0 && (
                      <div>
                        <div className="text-sm font-medium text-gray-700 mb-2">Content Types Found</div>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(step.details.by_content_type).map(([type, count]) => (
                            <span key={type} className="bg-gray-100 px-2 py-1 rounded text-sm">
                              {type}: {count}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {Object.keys(step.details.by_search_term).length > 0 && (
                      <div>
                        <div className="text-sm font-medium text-gray-700 mb-2">Results by Search Term</div>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(step.details.by_search_term).map(([term, count]) => (
                            <span key={term} className="bg-blue-100 px-2 py-1 rounded text-sm">
                              "{term}": {count}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {step.step === 3 && (
                  <div className="space-y-2">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-sm font-medium text-gray-700">Model Used</div>
                        <div className="text-sm text-gray-600">{step.details.model_used}</div>
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-700">Tokens Used</div>
                        <div className="text-sm text-gray-600">{step.details.tokens_used}</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Data Summary */}
      {showDetails && ragProcess.data_summary && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <h4 className="font-medium text-gray-900 mb-3">Data Summary</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white p-3 rounded border">
              <div className="text-sm font-medium text-gray-700">Total Conversations</div>
              <div className="text-lg font-bold text-gray-900">{ragProcess.data_summary.total_conversations}</div>
            </div>
            <div className="bg-white p-3 rounded border">
              <div className="text-sm font-medium text-gray-700">Retrieved Items</div>
              <div className="text-lg font-bold text-gray-900">{ragProcess.data_summary.retrieved_items}</div>
            </div>
            <div className="bg-white p-3 rounded border">
              <div className="text-sm font-medium text-gray-700">Content Types</div>
              <div className="text-sm text-gray-600">
                {ragProcess.data_summary.content_types_found?.join(', ') || 'None'}
              </div>
            </div>
          </div>
          
          {ragProcess.data_summary.date_range && (
            <div className="mt-3 bg-white p-3 rounded border">
              <div className="text-sm font-medium text-gray-700 mb-2">Date Range</div>
              <div className="text-sm text-gray-600">
                <div>Earliest: {ragProcess.data_summary.date_range.earliest}</div>
                <div>Latest: {ragProcess.data_summary.date_range.latest}</div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default RAGProcessDisplay;

