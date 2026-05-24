import React, { useEffect, useState } from 'react';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { getInterviewProject } from '../../utils/interviewApi';
import InterviewSetupForm from './InterviewSetupForm';
import InterviewSessionList from './InterviewSessionList';

export default function InterviewProjectDetail({
  projectId,
  onBack,
  onSelectSession,
  refreshKey,
  onProjectUpdated,
}) {
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sessionRefreshKey, setSessionRefreshKey] = useState(0);

  const loadProject = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getInterviewProject(projectId);
      if (data.success) {
        setProject(data.project);
      } else {
        setError(data.error || 'Project not found');
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProject();
  }, [projectId, refreshKey]);

  const handleProjectSaved = (updated) => {
    setProject((prev) => ({ ...prev, ...updated }));
    onProjectUpdated?.();
  };

  const handleSessionCreated = () => {
    setSessionRefreshKey((k) => k + 1);
    loadProject();
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading project…
      </div>
    );
  }

  if (error || !project) {
    return (
      <div>
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Back to projects
        </button>
        <p className="text-sm text-red-600">{error || 'Project not found'}</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900"
      >
        <ArrowLeft className="h-4 w-4" /> Back to projects
      </button>

      <div>
        <h3 className="text-lg font-semibold text-gray-900">{project.name}</h3>
        <p className="text-sm text-gray-500 mt-0.5">
          Edits apply to new participant invites only — existing sessions keep their original setup.
        </p>
      </div>

      <section>
        <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
          Project setup
        </h4>
        <InterviewSetupForm
          mode="edit"
          project={project}
          onSaved={handleProjectSaved}
        />
      </section>

      <section>
        <InterviewSessionList
          projectId={projectId}
          refreshKey={sessionRefreshKey}
          onSelectSession={onSelectSession}
          onSessionCreated={handleSessionCreated}
        />
      </section>
    </div>
  );
}
