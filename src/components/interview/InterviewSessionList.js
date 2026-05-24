import React, { useEffect, useState } from 'react';
import { RefreshCw, Copy, ExternalLink, StopCircle, Eye } from 'lucide-react';
import {
  listInterviewSessions,
  endInterviewSession,
  fullJoinUrl,
} from '../../utils/interviewApi';

const statusColors = {
  pending: 'bg-gray-100 text-gray-700',
  active: 'bg-blue-100 text-blue-800',
  complete: 'bg-green-100 text-green-800',
  handoff: 'bg-amber-100 text-amber-800',
  declined: 'bg-gray-100 text-gray-600',
};

export default function InterviewSessionList({ onSelectSession, refreshKey }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchSessions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listInterviewSessions();
      if (data.success) {
        setSessions(data.sessions || []);
      } else {
        setError(data.error || 'Failed to load sessions');
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, [refreshKey]);

  const copyLink = (path) => {
    navigator.clipboard.writeText(fullJoinUrl(path));
  };

  const handleEnd = async (sessionId) => {
    if (!window.confirm('End this interview and generate insights?')) return;
    try {
      await endInterviewSession(sessionId);
      fetchSessions();
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    }
  };

  if (loading) {
    return <p className="text-sm text-gray-500">Loading sessions…</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Interview sessions</h3>
        <button
          type="button"
          onClick={fetchSessions}
          className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900"
        >
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
      )}

      {sessions.length === 0 ? (
        <p className="text-sm text-gray-500">No sessions yet. Create one in Configure.</p>
      ) : (
        <div className="overflow-x-auto border border-gray-200 rounded-lg">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-left text-gray-600">
              <tr>
                <th className="px-4 py-3 font-medium">Topic</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Messages</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sessions.map((s) => (
                <tr key={s.session_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{s.topic}</div>
                    <div className="text-xs text-gray-500 font-mono">{s.session_id.slice(0, 8)}…</div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                        statusColors[s.status] || statusColors.pending
                      }`}
                    >
                      {s.status}
                      {s.handoff_triggered ? ' · handoff' : ''}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{s.transcript_length}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        title="Copy participant link"
                        onClick={() => copyLink(s.join_url)}
                        className="p-1.5 text-gray-500 hover:text-indigo-600 hover:bg-indigo-50 rounded"
                      >
                        <Copy className="h-4 w-4" />
                      </button>
                      <a
                        href={fullJoinUrl(s.join_url)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1.5 text-gray-500 hover:text-indigo-600 hover:bg-indigo-50 rounded"
                        title="Open participant view"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                      <button
                        type="button"
                        onClick={() => onSelectSession?.(s.session_id)}
                        className="p-1.5 text-gray-500 hover:text-indigo-600 hover:bg-indigo-50 rounded"
                        title="View results"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                      {s.status === 'active' && (
                        <button
                          type="button"
                          onClick={() => handleEnd(s.session_id)}
                          className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded"
                          title="End session"
                        >
                          <StopCircle className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
