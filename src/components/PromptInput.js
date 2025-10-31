import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Sparkles } from 'lucide-react';

const PromptInput = ({ onSendMessage, isLoading, placeholder = 'Type your message...', exampleQuestions = [] }) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !isLoading) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleExampleClick = (question) => {
    if (!isLoading) {
      onSendMessage(question);
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  return (
    <div className="space-y-3">
      {/* Example Questions */}
      {exampleQuestions.length > 0 && !isLoading && (
        <div className="flex flex-wrap gap-2">
          <div className="flex items-center space-x-1 text-xs text-gray-500 mr-2">
            <Sparkles className="h-3 w-3" />
            <span>Try:</span>
          </div>
          {exampleQuestions.map((question, index) => (
            <button
              key={index}
              type="button"
              onClick={() => handleExampleClick(question)}
              className="px-3 py-1.5 text-sm bg-blue-50 text-blue-700 rounded-full hover:bg-blue-100 hover:text-blue-800 transition-colors border border-blue-200 hover:border-blue-300"
            >
              {question}
            </button>
          ))}
        </div>
      )}
      
      {/* Input Form */}
      <form onSubmit={handleSubmit} className="flex items-end space-x-3">
        <div className="flex-1">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed"
            rows={1}
            style={{ minHeight: '48px', maxHeight: '200px' }}
          />
        </div>
        <button
          type="submit"
          disabled={!message.trim() || isLoading}
          className="flex items-center justify-center w-12 h-12 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Send className="h-5 w-5" />
          )}
        </button>
      </form>
    </div>
  );
};

export default PromptInput;

