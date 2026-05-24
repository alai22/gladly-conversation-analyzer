import React, { useState } from 'react';
import { ChevronDown, ChevronUp, BookOpen } from 'lucide-react';
import InterviewSetupForm from './InterviewSetupForm';
import InterviewSessionList from './InterviewSessionList';
import InterviewResultsPanel from './InterviewResultsPanel';

const GUIDELINES_SUMMARY = [
  'Friendly, neutral tone — no product pitching or leading questions.',
  'Explicit consent before exploration; participant can decline anytime.',
  'No collection of personal identifiers (email, address, account numbers).',
  'One question at a time; adapts depth based on time and signal.',
  'Support/safety issues trigger empathetic handoff to Halo support.',
  'AI disclosure if participant asks whether the interviewer is human.',
];

export default function TextInterviewHub() {
  const [tab, setTab] = useState('configure');
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [guidelinesOpen, setGuidelinesOpen] = useState(false);

  const tabs = [
    { id: 'configure', label: 'Configure' },
    { id: 'sessions', label: 'Sessions' },
    { id: 'results', label: 'Results' },
  ];

  const handleSessionCreated = () => {
    setRefreshKey((k) => k + 1);
    setTab('sessions');
  };

  const handleSelectSession = (sessionId) => {
    setSelectedSessionId(sessionId);
    setTab('results');
  };

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">AI Text Interviews</h2>
        <p className="text-sm text-gray-600 mt-1">
          Conduct adaptive 1:1 research interviews and generate structured insights.
        </p>
      </div>

      <div className="mb-6 border border-indigo-100 rounded-lg bg-indigo-50/50">
        <button
          type="button"
          onClick={() => setGuidelinesOpen(!guidelinesOpen)}
          className="w-full flex items-center justify-between px-4 py-3 text-left"
        >
          <span className="inline-flex items-center gap-2 text-sm font-medium text-indigo-900">
            <BookOpen className="h-4 w-4" /> Participant guidelines (share with marketing/legal)
          </span>
          {guidelinesOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
        {guidelinesOpen && (
          <ul className="px-4 pb-4 text-sm text-indigo-900/90 list-disc list-inside space-y-1">
            {GUIDELINES_SUMMARY.map((line) => (
              <li key={line}>{line}</li>
            ))}
            <li className="list-none mt-2 text-xs text-indigo-700">
              Full doc: docs/interview-participant-guidelines.md
            </li>
          </ul>
        )}
      </div>

      <div className="flex gap-2 mb-6 border-b border-gray-200">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === t.id
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'configure' && (
        <InterviewSetupForm onSessionCreated={handleSessionCreated} />
      )}

      {tab === 'sessions' && (
        <InterviewSessionList
          refreshKey={refreshKey}
          onSelectSession={handleSelectSession}
        />
      )}

      {tab === 'results' && (
        selectedSessionId ? (
          <InterviewResultsPanel
            sessionId={selectedSessionId}
            onBack={() => {
              setSelectedSessionId(null);
              setTab('sessions');
            }}
          />
        ) : (
          <p className="text-sm text-gray-500">
            Select a session from the Sessions tab to view insights.
          </p>
        )
      )}
    </div>
  );
}
