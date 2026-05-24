import React, { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import {
  createInterviewProject,
  updateInterviewProject,
} from '../../utils/interviewApi';

const defaultConfig = {
  topic: '',
  audience: '',
  time_limit_minutes: 15,
  max_questions: 12,
  banned_topics: [],
  compliance_notes: '',
  hypothesis: '',
  confidence_bar: 3,
  allow_follow_up_recruitment: false,
};

function configFromProject(project) {
  if (!project?.config) return { ...defaultConfig };
  return { ...defaultConfig, ...project.config };
}

export default function InterviewSetupForm({
  mode = 'create',
  project = null,
  onSaved,
  onProjectCreated,
}) {
  const isEdit = mode === 'edit';
  const [name, setName] = useState(project?.name || '');
  const [config, setConfig] = useState(() => configFromProject(project));
  const [bannedInput, setBannedInput] = useState(
    () => (project?.config?.banned_topics || []).join(', ')
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (project) {
      setName(project.name || '');
      setConfig(configFromProject(project));
      setBannedInput((project.config?.banned_topics || []).join(', '));
    }
  }, [project?.project_id]);

  const handleChange = (field, value) => {
    setConfig((prev) => ({ ...prev, [field]: value }));
    setSaved(false);
  };

  const buildPayload = () => ({
    name: name.trim() || config.topic,
    ...config,
    time_limit_minutes: Number(config.time_limit_minutes),
    max_questions: Number(config.max_questions),
    confidence_bar: Number(config.confidence_bar),
    banned_topics: bannedInput
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean),
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    setSaved(false);
    try {
      const payload = buildPayload();
      if (isEdit && project?.project_id) {
        const data = await updateInterviewProject(project.project_id, payload);
        if (data.success) {
          setSaved(true);
          onSaved?.(data.project);
        } else {
          setError(data.error || 'Failed to save project');
        }
      } else {
        const data = await createInterviewProject(payload);
        if (data.success) {
          onProjectCreated?.(data.project);
        } else {
          setError(data.error || 'Failed to create project');
        }
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Request failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5 max-w-2xl">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Project name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              setSaved(false);
            }}
            placeholder="e.g. GPS accuracy — Q2 discovery"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-halo-yellow focus:border-halo-yellow"
          />
        </div>
        <div className="sm:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Topic / decision to inform *
          </label>
          <input
            type="text"
            required
            value={config.topic}
            onChange={(e) => handleChange('topic', e.target.value)}
            placeholder="e.g. Shape Up pitch — GPS accuracy improvements"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-halo-yellow focus:border-halo-yellow"
          />
        </div>
        <div className="sm:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Target audience
          </label>
          <input
            type="text"
            value={config.audience}
            onChange={(e) => handleChange('audience', e.target.value)}
            placeholder="e.g. Halo 4 owners who use GPS daily"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-halo-yellow focus:border-halo-yellow"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Time limit (minutes)
          </label>
          <input
            type="number"
            min={5}
            max={60}
            value={config.time_limit_minutes}
            onChange={(e) => handleChange('time_limit_minutes', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Max questions
          </label>
          <input
            type="number"
            min={3}
            max={30}
            value={config.max_questions}
            onChange={(e) => handleChange('max_questions', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          />
        </div>
        <div className="sm:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Do-not-ask topics (comma-separated)
          </label>
          <input
            type="text"
            value={bannedInput}
            onChange={(e) => {
              setBannedInput(e.target.value);
              setSaved(false);
            }}
            placeholder="pricing, competitors, legal disputes"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          />
        </div>
        <div className="sm:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Hypothesis to test (optional)
          </label>
          <input
            type="text"
            value={config.hypothesis}
            onChange={(e) => handleChange('hypothesis', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          />
        </div>
        <div className="sm:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Compliance notes (optional)
          </label>
          <textarea
            value={config.compliance_notes}
            onChange={(e) => handleChange('compliance_notes', e.target.value)}
            rows={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          />
        </div>
        <div className="sm:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Confidence bar — depth vs speed ({config.confidence_bar})
          </label>
          <input
            type="range"
            min={1}
            max={5}
            value={config.confidence_bar}
            onChange={(e) => handleChange('confidence_bar', e.target.value)}
            className="w-full"
          />
          <p className="text-xs text-gray-500 mt-1">1 = quick signal, 5 = deeper exploration</p>
        </div>
        <div className="sm:col-span-2">
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={config.allow_follow_up_recruitment}
              onChange={(e) => handleChange('allow_follow_up_recruitment', e.target.checked)}
            />
            Allow agent to ask permission for follow-up / future research
          </label>
        </div>
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
      )}

      {saved && isEdit && (
        <p className="text-sm text-green-700 bg-green-50 px-3 py-2 rounded-lg">
          Project saved. New invites will use this setup.
        </p>
      )}

      <button
        type="submit"
        disabled={loading}
        className="inline-flex items-center gap-2 px-4 py-2.5 bg-halo-yellow text-halo-black rounded-lg hover:bg-halo-yellow-dark disabled:opacity-50"
      >
        {loading && <Loader2 className="h-4 w-4 animate-spin" />}
        {isEdit ? 'Save project' : 'Create project'}
      </button>
    </form>
  );
}
