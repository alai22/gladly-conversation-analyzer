import React, { useEffect, useState } from 'react';
import { FolderOpen, Plus, RefreshCw } from 'lucide-react';
import { listInterviewProjects } from '../../utils/interviewApi';

const statusColors = {
  draft: 'bg-gray-100 text-gray-700',
  active: 'bg-halo-yellow-light text-halo-black',
  archived: 'bg-halo-blue-light text-halo-blue-dark',
};

export default function InterviewProjectList({ onSelectProject, onCreateProject, refreshKey }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listInterviewProjects();
      if (data.success) {
        setProjects(data.projects || []);
      } else {
        setError(data.error || 'Failed to load projects');
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, [refreshKey]);

  if (loading) {
    return <p className="text-sm text-gray-500">Loading projects…</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Research projects</h3>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={fetchProjects}
            className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900"
          >
            <RefreshCw className="h-4 w-4" /> Refresh
          </button>
          <button
            type="button"
            onClick={onCreateProject}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-halo-yellow text-halo-black rounded-lg hover:bg-halo-yellow-dark"
          >
            <Plus className="h-4 w-4" /> New project
          </button>
        </div>
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
      )}

      {projects.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-gray-300 rounded-lg">
          <FolderOpen className="h-10 w-10 text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500 mb-4">No research projects yet.</p>
          <button
            type="button"
            onClick={onCreateProject}
            className="inline-flex items-center gap-1 px-4 py-2 text-sm bg-halo-yellow text-halo-black rounded-lg hover:bg-halo-yellow-dark"
          >
            <Plus className="h-4 w-4" /> Create your first project
          </button>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {projects.map((p) => (
            <button
              key={p.project_id}
              type="button"
              onClick={() => onSelectProject?.(p.project_id)}
              className="text-left p-4 border border-gray-200 rounded-lg hover:border-halo-yellow hover:bg-halo-yellow-light/80 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-medium text-gray-900 truncate">{p.name}</p>
                  <p className="text-sm text-gray-600 mt-0.5 truncate">{p.config?.topic}</p>
                </div>
                <span
                  className={`shrink-0 inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                    statusColors[p.status] || statusColors.active
                  }`}
                >
                  {p.status}
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                {p.session_count ?? 0} participant{p.session_count === 1 ? '' : 's'}
              </p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
