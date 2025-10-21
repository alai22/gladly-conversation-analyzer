import React from 'react';
import { Bot, User, Search, Database, Clock, AlertCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';

function ConversationDisplay({ conversations, isLoading, error }) {
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
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Error</h3>
          <p className="text-gray-600">{error}</p>
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
                        return !inline && match ? (
                          <SyntaxHighlighter
                            style={tomorrow}
                            language={match[1]}
                            PreTag="div"
                            {...props}
                          >
                            {String(children).replace(/\n$/, '')}
                          </SyntaxHighlighter>
                        ) : (
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
    </div>
  );
}

export default ConversationDisplay;

