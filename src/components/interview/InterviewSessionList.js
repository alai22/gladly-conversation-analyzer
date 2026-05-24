import React, { useEffect, useState } from 'react';
import { RefreshCw, Copy, ExternalLink, StopCircle, Eye, UserPlus, Loader2 } from 'lucide-react';
import {
  listProjectSessions,
  createParticipantSession,
  endInterviewSession,
  fullJoinUrl,
} from '../../utils/interviewApi';

const statusColors = {
  pending: 'bg-gray-100 text-gray-700',
  active: 'bg-halo-blue-light text-halo-blue-dark',
  complete: 'bg-halo-yellow-light text-halo-black',
  handoff: 'bg-amber-100 text-amber-800',
  declined: 'bg-gray-100 text-gray-600',
};

export default function InterviewSessionList({
  projectId,
  onSelectSession,
  refreshKey,
  onSessionCreated,
}) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [inviteLabel, setInviteLabel] = useState('');
  const [inviting, setInviting] = useState(false);
  const [newLink, setNewLink] = useState(null);

  const fetchSessions = async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await listProjectSessions(projectId);
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
  }, [projectId, refreshKey]);

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

  const handleInvite = async (e) => {
    e.preventDefault();
    setInviting(true);
    setError(null);
    setNewLink(null);
    try {
      const data = await createParticipantSession(projectId, {
        participant_label: inviteLabel.trim(),
      });
      if (data.success) {
        const link = fullJoinUrl(data.join_url);
        setNewLink(link);
        setInviteLabel('');
        fetchSessions();
        onSessionCreated?.(data);
      } else {
        setError(data.error || 'Failed to create invite');
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setInviting(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-gray-500">Loading participants…</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Participant interviews</h3>
        <button
          type="button"
          onClick={fetchSessions}
          className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900"
        >
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      <form onSubmit={handleInvite} className="flex flex-col sm:flex-row gap-2 p-4 bg-halo-yellow-light border border-halo-yellow/40 rounded-lg">
        <div className="flex-1">
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Participant label (optional, for your records)
          </label>
          <input
            type="text"
            value={inviteLabel}
            onChange={(e) => setInviteLabel(e.target.value)}
            placeholder="e.g. Participant A, beta tester #3"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={inviting}
          className="self-end sm:self-auto inline-flex items-center gap-2 px-4 py-2 bg-halo-yellow text-halo-black rounded-lg hover:bg-halo-yellow-dark disabled:opacity-50 text-sm"
        >
          {inviting ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
          Invite participant
        </button>
      </form>

      {newLink && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm font-medium text-green-900 mb-2">Participant link ready — share this unique URL</p>
          <code className="text-xs break-all text-green-800 block mb-2">{newLink}</code>
          <button
            type="button"
            onClick={() => navigator.clipboard.writeText(newLink)}
            className="text-sm text-green-700 underline hover:text-green-900"
          >
            Copy link
          </button>
          <p className="text-xs text-green-700 mt-2">
            The participant can return to this same link to resume their interview.
          </p>
        </div>
      )}

      {error && (
        <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
      )}

      {sessions.length === 0 ? (
        <p className="text-sm text-gray-500">No participants yet. Invite someone to start collecting responses.</p>
      ) : (
        <div className="overflow-x-auto border border-gray-200 rounded-lg">
          <table className="min-w-full text-sm">
            <thead className="bg-halo-yellow-light text-left text-halo-black">
              <tr>
                <th className="px-4 py-3 font-medium">Participant</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Messages</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sessions.map((s) => (
                <tr key={s.session_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">
                      {s.participant_label || 'Unlabeled participant'}
                    </div>
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
                        className="p-1.5 text-gray-500 hover:text-halo-blue hover:bg-halo-yellow-light rounded"
                      >
                        <Copy className="h-4 w-4" />
                      </button>
                      <a
                        href={fullJoinUrl(s.join_url)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1.5 text-gray-500 hover:text-halo-blue hover:bg-halo-yellow-light rounded"
                        title="Open participant view"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                      <button
                        type="button"
                        onClick={() => onSelectSession?.(s.session_id)}
                        className="p-1.5 text-gray-500 hover:text-halo-blue hover:bg-halo-yellow-light rounded"
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
