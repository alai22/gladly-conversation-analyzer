import React, { useState } from 'react';
import { ChevronDown, ChevronUp, BookOpen } from 'lucide-react';
import InterviewProjectList from './InterviewProjectList';
import InterviewProjectDetail from './InterviewProjectDetail';
import InterviewSetupForm from './InterviewSetupForm';
import InterviewResultsPanel from './InterviewResultsPanel';

const GUIDELINES_SUMMARY = [
  'Friendly, neutral tone — no product pitching or leading questions.',
  'Explicit consent before exploration; participant can decline anytime.',
  'One question at a time; adapts depth based on time and signal.',
  'Support/safety issues trigger empathetic handoff to Halo support.',
  'AI disclosure if participant asks whether the interviewer is human.',
];

export default function TextInterviewHub() {
  const [view, setView] = useState('projects');
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [guidelinesOpen, setGuidelinesOpen] = useState(false);

  const handleSelectProject = (projectId) => {
    setSelectedProjectId(projectId);
    setView('project');
  };

  const handleCreateProject = () => {
    setSelectedProjectId(null);
    setView('create');
  };

  const handleProjectCreated = (project) => {
    setRefreshKey((k) => k + 1);
    setSelectedProjectId(project.project_id);
    setView('project');
  };

  const handleSelectSession = (sessionId) => {
    setSelectedSessionId(sessionId);
    setView('results');
  };

  const handleBackToProjects = () => {
    setSelectedProjectId(null);
    setSelectedSessionId(null);
    setView('projects');
    setRefreshKey((k) => k + 1);
  };

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto bg-white min-h-full">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-halo-black">AI Text Interviews</h2>
        <p className="text-sm text-gray-600 mt-1">
          Create research projects, invite participants with unique links, and generate structured insights.
        </p>
      </div>

      <div className="mb-6 border-l-4 border-halo-blue border border-halo-yellow/30 rounded-lg bg-halo-yellow-light">
        <button
          type="button"
          onClick={() => setGuidelinesOpen(!guidelinesOpen)}
          className="w-full flex items-center justify-between px-4 py-3 text-left"
        >
          <span className="inline-flex items-center gap-2 text-sm font-medium text-halo-black">
            <BookOpen className="h-4 w-4" /> Participant guidelines (share with marketing/legal)
          </span>
          {guidelinesOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
        {guidelinesOpen && (
          <ul className="px-4 pb-4 text-sm text-halo-black/90 list-disc list-inside space-y-1">
            {GUIDELINES_SUMMARY.map((line) => (
              <li key={line}>{line}</li>
            ))}
            <li className="list-none mt-2 text-xs text-halo-blue">
              Full doc: docs/interview-participant-guidelines.md
            </li>
          </ul>
        )}
      </div>

      {view === 'projects' && (
        <InterviewProjectList
          refreshKey={refreshKey}
          onSelectProject={handleSelectProject}
          onCreateProject={handleCreateProject}
        />
      )}

      {view === 'create' && (
        <div className="space-y-4">
          <button
            type="button"
            onClick={handleBackToProjects}
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            ← Back to projects
          </button>
          <h3 className="text-lg font-semibold text-gray-900">New research project</h3>
          <InterviewSetupForm mode="create" onProjectCreated={handleProjectCreated} />
        </div>
      )}

      {view === 'project' && selectedProjectId && (
        <InterviewProjectDetail
          projectId={selectedProjectId}
          refreshKey={refreshKey}
          onBack={handleBackToProjects}
          onSelectSession={handleSelectSession}
          onProjectUpdated={() => setRefreshKey((k) => k + 1)}
        />
      )}

      {view === 'results' && selectedSessionId && (
        <InterviewResultsPanel
          sessionId={selectedSessionId}
          onBack={() => {
            setSelectedSessionId(null);
            setView('project');
          }}
        />
      )}
    </div>
  );
}
