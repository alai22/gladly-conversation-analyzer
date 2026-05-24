import React, { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Send, Loader2, LogOut } from 'lucide-react';
import {
  joinInterview,
  sendParticipantMessage,
  endParticipantInterview,
} from '../../utils/interviewApi';

export default function InterviewParticipantPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('t');
  const [session, setSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [ended, setEnded] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (!token) {
      setError('Invalid interview link. Missing token.');
      setLoading(false);
      return;
    }
    (async () => {
      try {
        const data = await joinInterview(token);
        if (data.success) {
          setSession(data);
          setMessages(data.transcript || []);
          setEnded(['complete', 'declined', 'handoff'].includes(data.status));
        } else {
          setError(data.error || 'Interview not found');
        }
      } catch (err) {
        setError(err.response?.data?.error || err.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || sending || ended) return;
    setSending(true);
    setError(null);
    const text = input.trim();
    setInput('');
    setMessages((prev) => [
      ...prev,
      { role: 'participant', text, ts: new Date().toISOString() },
    ]);
    try {
      const data = await sendParticipantMessage(token, text);
      if (data.success) {
        setMessages(data.transcript || []);
        if (['complete', 'declined', 'handoff'].includes(data.status)) {
          setEnded(true);
        }
      } else {
        setError(data.error);
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setSending(false);
    }
  };

  const handleEnd = async () => {
    if (!window.confirm('End this interview now?')) return;
    setSending(true);
    try {
      const data = await endParticipantInterview(token);
      if (data.success) {
        setEnded(true);
        if (data.reply) {
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', text: data.reply, ts: new Date().toISOString() },
          ]);
        }
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (error && !session) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-6">
        <p className="text-red-600 text-center">{error}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-4 py-4 shadow-sm">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-lg font-semibold text-gray-900">Halo Research Chat</h1>
          {session?.topic && (
            <p className="text-sm text-gray-600 mt-0.5">Topic: {session.topic}</p>
          )}
          {session?.time_limit_minutes && (
            <p className="text-xs text-gray-500">~{session.time_limit_minutes} minutes</p>
          )}
        </div>
      </header>

      <main className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-2xl mx-auto space-y-3">
          {messages.length === 0 && (
            <p className="text-center text-gray-500 text-sm">Waiting for the interview to begin…</p>
          )}
          {messages.map((msg, i) => (
            <div
              key={`${msg.ts}-${i}`}
              className={`flex ${msg.role === 'participant' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] px-4 py-2.5 rounded-2xl text-sm ${
                  msg.role === 'participant'
                    ? 'bg-indigo-600 text-white rounded-br-md'
                    : 'bg-white border border-gray-200 text-gray-800 rounded-bl-md shadow-sm'
                }`}
              >
                {msg.text}
              </div>
            </div>
          ))}
          {sending && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 px-4 py-2 rounded-2xl">
                <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </main>

      {error && (
        <p className="text-center text-sm text-red-600 px-4 pb-2">{error}</p>
      )}

      <footer className="bg-white border-t border-gray-200 px-4 py-4">
        <div className="max-w-2xl mx-auto">
          {ended ? (
            <p className="text-center text-sm text-gray-600 py-2">
              This interview has ended. Thank you for your time.
            </p>
          ) : (
            <>
              <form onSubmit={handleSend} className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Type your response…"
                  disabled={sending}
                  className="flex-1 px-4 py-2.5 border border-gray-300 rounded-full focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
                <button
                  type="submit"
                  disabled={sending || !input.trim()}
                  className="p-2.5 bg-indigo-600 text-white rounded-full hover:bg-indigo-700 disabled:opacity-50"
                >
                  <Send className="h-5 w-5" />
                </button>
              </form>
              <button
                type="button"
                onClick={handleEnd}
                className="mt-3 w-full inline-flex items-center justify-center gap-1 text-sm text-gray-500 hover:text-gray-800"
              >
                <LogOut className="h-4 w-4" /> End interview
              </button>
            </>
          )}
        </div>
      </footer>
    </div>
  );
}
