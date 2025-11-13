import React, { useState } from 'react';
import { Lock } from 'lucide-react';

function Login({ onLogin }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Simple password check - you can change this password
    const correctPassword = process.env.REACT_APP_PASSWORD || 'gladly2024';
    
    if (password === correctPassword) {
      onLogin();
      setError('');
    } else {
      setError('Incorrect password');
      setPassword('');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl p-8 w-full max-w-md">
        <div className="flex items-center justify-center mb-6">
          <Lock className="h-12 w-12 text-blue-600" />
        </div>
        <h1 className="text-2xl font-bold text-center text-gray-900 mb-2">
          Halo Insights
        </h1>
        <p className="text-center text-gray-600 mb-6">
          Enter password to access
        </p>
        
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
          </div>
          
          {error && (
            <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-lg text-sm">
              {error}
            </div>
          )}
          
          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
          >
            Login
          </button>
        </form>
        
        <p className="text-xs text-gray-500 text-center mt-6">
          Secured with password authentication
        </p>
      </div>
    </div>
  );
}

export default Login;

