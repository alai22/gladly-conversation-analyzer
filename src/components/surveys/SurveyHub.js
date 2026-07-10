import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, ClipboardList, Loader2, ExternalLink } from 'lucide-react';
import { createSurvey, listSurveys, surveyPublicUrl } from '../../utils/haloSurveyApi';

export default function SurveyHub() {
  const navigate = useNavigate();
  const [surveys, setSurveys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const data = await listSurveys();
      if (data.success) setSurveys(data.surveys || []);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async () => {
    setCreating(true);
    try {
      const data = await createSurvey({ title: 'Untitled Survey' });
      if (data.success) {
        navigate(`/surveys/${data.survey.survey_id}`);
      }
    } catch {
      /* ignore */
    } finally {
      setCreating(false);
    }
  };

  const statusColors = {
    draft: 'bg-gray-100 text-gray-700',
    active: 'bg-green-100 text-green-800',
    archived: 'bg-red-100 text-red-800',
  };

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto bg-white min-h-full">
      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <h2 className="text-2xl font-bold text-halo-black">Halo Surveys</h2>
          <p className="text-sm text-gray-600 mt-1">
            Design surveys with AI, publish branded links for Braze campaigns, and analyze responses.
          </p>
        </div>
        <button
          type="button"
          onClick={handleCreate}
          disabled={creating}
          className="inline-flex items-center gap-2 px-4 py-2 bg-halo-yellow text-halo-black font-medium rounded-lg hover:bg-halo-yellow-dark disabled:opacity-50"
        >
          {creating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Plus className="h-4 w-4" />
          )}
          New survey
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
        </div>
      ) : surveys.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-gray-300 rounded-lg">
          <ClipboardList className="h-10 w-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No surveys yet. Create one or wait for seed data to load.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {surveys.map((s) => (
            <div
              key={s.survey_id}
              className="flex flex-wrap items-center justify-between gap-3 p-4 border border-gray-200 rounded-lg hover:border-halo-yellow transition-colors cursor-pointer"
              onClick={() => navigate(`/surveys/${s.survey_id}`)}
            >
              <div>
                <h3 className="font-semibold text-halo-black">{s.title}</h3>
                <div className="flex items-center gap-2 mt-1">
                  <span
                    className={`text-xs px-2 py-0.5 rounded font-medium ${
                      statusColors[s.status] || statusColors.draft
                    }`}
                  >
                    {s.status}
                  </span>
                  <code className="text-xs text-gray-500">/s/{s.slug}</code>
                  {s.response_count > 0 && (
                    <span className="text-xs text-gray-400">
                      {s.response_count} response{s.response_count !== 1 ? 's' : ''}
                    </span>
                  )}
                </div>
                {s.audience && (
                  <p className="text-xs text-gray-400 mt-1">Audience: {s.audience}</p>
                )}
              </div>
              {s.status === 'active' && (
                <a
                  href={surveyPublicUrl(s.slug)}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="inline-flex items-center gap-1 text-xs text-halo-blue hover:underline"
                >
                  Open <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
