import React, { useState } from 'react';
import { Bot, User, Search, Database, Clock, AlertCircle, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';
import axios from 'axios';

function ConversationDisplay({ conversations, isLoading, error }) {
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [conversationDetails, setConversationDetails] = useState(null);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const getIcon = (type) => {
    switch (type) {
      case 'claude':
        return <Bot className="h-5 w-5 text-blue-600" />;
      case 'search':
        return <Search className="h-5 w-5 text-green-600" />;
      case 'ask':
        return <Database className="h-5 w-5 text-purple-600" />;
      default:
        return <User className="h-5 w-5 text-gray-600" />;
    }
  };

  const getTypeLabel = (type) => {
    switch (type) {
      case 'claude':
        return 'Claude Response';
      case 'search':
        return 'Search Results';
      case 'ask':
        return 'RAG Analysis';
      default:
        return 'Response';
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  // Detect if a string looks like a conversation ID (alphanumeric, typically 20+ chars)
  const isConversationId = (text) => {
    const cleanText = String(text).trim();
    // Conversation IDs are typically alphanumeric strings of reasonable length
    // Gladly conversation IDs are usually 20+ characters (but can be as short as 15)
    // Allow alphanumeric, underscores, hyphens, and spaces (some IDs have spaces)
    // Match strings that are 15+ characters and look like conversation IDs
    const idPattern = /^[a-zA-Z0-9_\-\s]{15,}$/;
    if (!idPattern.test(cleanText)) return false;
    
    // Additional check: should have mostly alphanumeric with few separators
    const alphaNumericCount = (cleanText.match(/[a-zA-Z0-9]/g) || []).length;
    return alphaNumericCount >= 12; // At least 12 alphanumeric chars
  };

  const handleConversationIdClick = async (conversationId) => {
    // Trim the conversation ID
    const cleanId = String(conversationId).trim();
    
    setSelectedConversationId(cleanId);
    setLoadingConversation(true);
    setConversationDetails(null);

    try {
      // Try with the ID as-is first (some IDs might have spaces)
      let response = await axios.get(`/api/conversations/${encodeURIComponent(cleanId)}`);
      
      // If that fails with 404, try without spaces (in case space is just formatting)
      if (!response.data.success && cleanId.includes(' ')) {
        const idWithoutSpaces = cleanId.replace(/\s+/g, '');
        response = await axios.get(`/api/conversations/${encodeURIComponent(idWithoutSpaces)}`);
      }
      
      if (response.data.success) {
        setConversationDetails(response.data);
      } else {
        setConversationDetails({ error: response.data.error || 'Conversation not found' });
      }
    } catch (error) {
      // If error and ID has spaces, try without spaces
      if (cleanId.includes(' ') && error.response?.status === 404) {
        try {
          const idWithoutSpaces = cleanId.replace(/\s+/g, '');
          const response = await axios.get(`/api/conversations/${encodeURIComponent(idWithoutSpaces)}`);
          if (response.data.success) {
            setConversationDetails(response.data);
            return;
          }
        } catch (retryError) {
          // Fall through to original error
        }
      }
      
      setConversationDetails({
        error: error.response?.data?.error || error.message || 'Failed to load conversation'
      });
    } finally {
      setLoadingConversation(false);
    }
  };

  const closeConversationModal = () => {
    setSelectedConversationId(null);
    setConversationDetails(null);
  };

  const renderMetadata = (metadata) => {
    if (!metadata || Object.keys(metadata).length === 0) return null;

    return (
      <div className="mt-3 p-3 bg-gray-50 rounded-lg text-xs text-gray-600">
        <div className="grid grid-cols-2 gap-2">
          {metadata.model && (
            <div>
              <span className="font-medium">Model:</span> {metadata.model}
            </div>
          )}
          {metadata.tokensUsed && (
            <div>
              <span className="font-medium">Tokens:</span> {metadata.tokensUsed}
            </div>
          )}
          {metadata.resultCount && (
            <div>
              <span className="font-medium">Results:</span> {metadata.resultCount}
            </div>
          )}
          {metadata.dataRetrieved && (
            <div>
              <span className="font-medium">Data Retrieved:</span> {metadata.dataRetrieved} items
            </div>
          )}
        </div>
        {metadata.ragProcess && (
          <div className="mt-2">
            <span className="font-medium">RAG Process:</span>
            <div className="ml-2 mt-1">
              {metadata.ragProcess.steps?.map((step, index) => (
                <div key={index} className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${
                    step.status === 'completed' ? 'bg-green-500' : 
                    step.status === 'running' ? 'bg-yellow-500' : 'bg-gray-400'
                  }`} />
                  <span className="text-xs">{step.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="text-center max-w-md">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Error</h3>
          <div className="text-gray-600 whitespace-pre-line text-left bg-red-50 p-4 rounded-lg border border-red-200">
            {error.split('\n').map((line, index) => (
              <p key={index} className={index === 0 ? 'font-medium mb-2' : index > 0 && line.trim() ? 'text-sm mb-1' : ''}>
                {line}
              </p>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (conversations.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="text-center">
          <Bot className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No conversations yet</h3>
          <p className="text-gray-600">Start by sending a message below</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      {conversations.map((conversation) => (
        <div key={conversation.id} className="space-y-4">
          {/* User Message */}
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <User className="h-6 w-6 text-gray-600" />
            </div>
            <div className="flex-1">
              <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-900">You</span>
                  <span className="text-xs text-gray-500 flex items-center">
                    <Clock className="h-3 w-3 mr-1" />
                    {formatTimestamp(conversation.timestamp)}
                  </span>
                </div>
                <p className="text-gray-800">{conversation.userMessage}</p>
              </div>
            </div>
          </div>

          {/* AI Response */}
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              {getIcon(conversation.type)}
            </div>
            <div className="flex-1">
              <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-900">
                    {getTypeLabel(conversation.type)}
                  </span>
                  <span className="text-xs text-gray-500 flex items-center">
                    <Clock className="h-3 w-3 mr-1" />
                    {formatTimestamp(conversation.timestamp)}
                  </span>
                </div>
                <div className="markdown-content">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      code({ node, inline, className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || '');
                        if (!inline && match) {
                          return (
                            <SyntaxHighlighter
                              style={tomorrow}
                              language={match[1]}
                              PreTag="div"
                              {...props}
                            >
                              {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                          );
                        }
                        
                        // Check if this inline code contains a conversation ID
                        const codeText = String(children).trim();
                        if (inline && isConversationId(codeText)) {
                          return (
                            <code 
                              className={className}
                              data-conversation-id={codeText}
                              style={{
                                color: '#2563eb',
                                cursor: 'pointer',
                                fontWeight: '600',
                                textDecoration: 'underline',
                                backgroundColor: '#eff6ff',
                                padding: '2px 4px',
                                borderRadius: '4px',
                                display: 'inline-block',
                              }}
                              onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                handleConversationIdClick(codeText);
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.color = '#1d4ed8';
                                e.currentTarget.style.backgroundColor = '#dbeafe';
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.color = '#2563eb';
                                e.currentTarget.style.backgroundColor = '#eff6ff';
                              }}
                              title="Click to view conversation"
                              role="button"
                              tabIndex={0}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                  e.preventDefault();
                                  handleConversationIdClick(codeText);
                                }
                              }}
                              {...props}
                            >
                              {children}
                            </code>
                          );
                        }
                        
                        return (
                          <code className={className} {...props}>
                            {children}
                          </code>
                        );
                      },
                    }}
                  >
                    {conversation.response}
                  </ReactMarkdown>
                </div>
                {renderMetadata(conversation.metadata)}
              </div>
            </div>
          </div>
        </div>
      ))}

      {/* Loading indicator */}
      {isLoading && (
        <div className="flex items-center justify-center p-6">
          <div className="flex items-center space-x-3">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            <span className="text-gray-600">Processing...</span>
          </div>
        </div>
      )}

      {/* Conversation Details Modal */}
      {selectedConversationId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <div className="flex items-center space-x-2">
                <Database className="h-5 w-5 text-purple-600" />
                <h2 className="text-lg font-semibold text-gray-900">
                  Conversation: <code className="text-blue-600">{selectedConversationId}</code>
                </h2>
              </div>
              <button
                onClick={closeConversationModal}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto p-4">
              {loadingConversation ? (
                <div className="flex items-center justify-center py-8">
                  <div className="flex items-center space-x-3">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                    <span className="text-gray-600">Loading conversation...</span>
                  </div>
                </div>
              ) : conversationDetails?.error ? (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-center space-x-2 text-red-800">
                    <AlertCircle className="h-5 w-5" />
                    <span>{conversationDetails.error}</span>
                  </div>
                </div>
              ) : conversationDetails?.items ? (
                <div className="space-y-4">
                  <div className="text-sm text-gray-600 mb-4">
                    Found {conversationDetails.count} item(s) in this conversation
                  </div>
                  {conversationDetails.items.map((item, index) => {
                    const content = item.content || {};
                    const contentType = content.type || 'Unknown';
                    return (
                      <div key={item.id || index} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded">
                              {contentType}
                            </span>
                            {item.timestamp && (
                              <span className="text-xs text-gray-500">
                                <Clock className="h-3 w-3 inline mr-1" />
                                {formatTimestamp(item.timestamp)}
                              </span>
                            )}
                          </div>
                        </div>
                        {item.customerId && (
                          <div className="text-sm text-gray-600 mb-2">
                            <span className="font-medium">Customer:</span> {item.customerId}
                          </div>
                        )}
                        {content.content && (
                          <div className="mt-2">
                            <div className="text-sm font-medium text-gray-700 mb-1">Content:</div>
                            <div className="text-sm text-gray-800 bg-white p-3 rounded border border-gray-200 whitespace-pre-wrap">
                              {content.content}
                            </div>
                          </div>
                        )}
                        {content.subject && (
                          <div className="mt-2">
                            <div className="text-sm font-medium text-gray-700 mb-1">Subject:</div>
                            <div className="text-sm text-gray-800">{content.subject}</div>
                          </div>
                        )}
                        {content.body && (
                          <div className="mt-2">
                            <div className="text-sm font-medium text-gray-700 mb-1">Body:</div>
                            <div className="text-sm text-gray-800 bg-white p-3 rounded border border-gray-200 whitespace-pre-wrap">
                              {content.body}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ConversationDisplay;

