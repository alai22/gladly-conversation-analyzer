import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, Send, Eye, BarChart2, Rocket, Archive } from 'lucide-react';
import {
  designerChat,
  getSurvey,
  publishSurvey,
  archiveSurvey,
  updateSurvey,
} from '../../utils/haloSurveyApi';
import SurveyPreview from './SurveyPreview';
import BrazeUrlPanel from './BrazeUrlPanel';
import SurveyResultsPanel from './SurveyResultsPanel';

export default function SurveyBuilder({ surveyId }) {
  const navigate = useNavigate();
  const [survey, setSurvey] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('builder');
  const [chatInput, setChatInput] = useState('');
  const [chatSending, setChatSending] = useState(false);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const chatBottomRef = useRef(null);

  const loadSurvey = async () => {
    try {
      const data = await getSurvey(surveyId);
      if (data.success) setSurvey(data.survey);
      else setError(data.error || 'Survey not found');
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSurvey();
  }, [surveyId]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [survey?.design_chat, chatSending]);

  const handleDesignerSend = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || chatSending) return;
    setChatSending(true);
    setError(null);
    const msg = chatInput.trim();
    setChatInput('');
    try {
      const data = await designerChat(surveyId, msg);
      if (data.success) {
        setSurvey(data.survey);
      } else {
        setError(data.error || data.assistant_message);
        if (data.survey) setSurvey(data.survey);
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setChatSending(false);
    }
  };

  const handlePublish = async () => {
    if (!window.confirm('Publish this survey? The slug will be locked and the public link will go live.')) return;
    try {
      const data = await publishSurvey(surveyId);
      if (data.success) setSurvey(data.survey);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    }
  };

  const handleArchive = async () => {
    if (!window.confirm('Archive this survey? Public link will stop working.')) return;
    try {
      const data = await archiveSurvey(surveyId);
      if (data.success) setSurvey(data.survey);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    }
  };

  const handleSlugSave = async (newSlug) => {
    setSaving(true);
    try {
      const data = await updateSurvey(surveyId, { slug: newSlug });
      if (data.success) setSurvey(data.survey);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleBrazeTemplateChange = async (template) => {
    setSurvey((s) => ({ ...s, braze_url_template: template }));
  };

  const saveBrazeTemplate = async () => {
    setSaving(true);
    try {
      const data = await updateSurvey(surveyId, {
        braze_url_template: survey.braze_url_template,
      });
      if (data.success) setSurvey(data.survey);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-halo-yellow" />
      </div>
    );
  }

  if (!survey) {
    return (
      <div className="p-6 text-center text-red-600">{error || 'Survey not found'}</div>
    );
  }

  const statusBadge = {
    draft: 'bg-gray-100 text-gray-700',
    active: 'bg-green-100 text-green-800',
    archived: 'bg-red-100 text-red-800',
  };

  return (
    <div className="h-full flex flex-col bg-white">
      <div className="px-4 sm:px-6 py-4 border-b border-gray-200">
        <button
          type="button"
          onClick={() => navigate('/surveys')}
          className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-halo-black mb-2"
        >
          <ArrowLeft className="h-4 w-4" /> All surveys
        </button>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold text-halo-black">{survey.title}</h2>
            <div className="flex items-center gap-2 mt-1">
              <span className={`text-xs px-2 py-0.5 rounded font-medium ${statusBadge[survey.status] || statusBadge.draft}`}>
                {survey.status}
              </span>
              {!survey.slug_locked && (
                <input
                  type="text"
                  defaultValue={survey.slug}
                  onBlur={(e) => {
                    if (e.target.value !== survey.slug) handleSlugSave(e.target.value);
                  }}
                  className="text-xs font-mono px-2 py-0.5 border border-gray-300 rounded"
                  placeholder="survey-slug"
                />
              )}
              {survey.slug_locked && (
                <code className="text-xs text-gray-500">/s/{survey.slug}</code>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            {survey.status === 'draft' && (
              <button
                type="button"
                onClick={handlePublish}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-halo-yellow text-halo-black font-medium rounded-lg hover:bg-halo-yellow-dark"
              >
                <Rocket className="h-4 w-4" /> Publish
              </button>
            )}
            {survey.status === 'active' && (
              <button
                type="button"
                onClick={handleArchive}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                <Archive className="h-4 w-4" /> Archive
              </button>
            )}
          </div>
        </div>

        <div className="flex gap-2 mt-4">
          {[
            { id: 'builder', label: 'Builder', icon: Eye },
            { id: 'results', label: 'Results', icon: BarChart2 },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setActiveTab(id)}
              className={`inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg ${
                activeTab === id
                  ? 'bg-halo-yellow text-halo-black font-medium'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Icon className="h-4 w-4" /> {label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="mx-4 mt-2 p-2 text-sm text-red-600 bg-red-50 rounded-lg">{error}</div>
      )}

      {activeTab === 'builder' && (
        <div className="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden">
          <div className="lg:w-1/2 flex flex-col border-r border-gray-200 min-h-[300px]">
            <div className="px-4 py-2 bg-gray-50 border-b border-gray-100">
              <p className="text-xs font-medium text-gray-600">AI Survey Designer</p>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {(survey.design_chat || []).length === 0 && (
                <div className="text-sm text-gray-500 p-4 bg-halo-yellow-light rounded-lg border border-halo-yellow/30">
                  Paste your survey spec or describe changes. Example: &quot;Add a gating question
                  on pairing — if No, end with a message to pair first.&quot;
                </div>
              )}
              {(survey.design_chat || []).map((msg, i) => (
                <div
                  key={i}
                  className={`p-3 rounded-lg text-sm max-w-[90%] ${
                    msg.role === 'user'
                      ? 'ml-auto bg-halo-yellow text-halo-black'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {msg.text}
                </div>
              ))}
              {chatSending && (
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <Loader2 className="h-4 w-4 animate-spin" /> Designing...
                </div>
              )}
              <div ref={chatBottomRef} />
            </div>
            <form onSubmit={handleDesignerSend} className="p-4 border-t border-gray-200">
              <div className="flex gap-2">
                <textarea
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Describe or paste survey content..."
                  rows={2}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-halo-yellow resize-none"
                />
                <button
                  type="submit"
                  disabled={chatSending || !chatInput.trim()}
                  className="self-end p-2.5 bg-halo-yellow text-halo-black rounded-lg disabled:opacity-50"
                >
                  <Send className="h-5 w-5" />
                </button>
              </div>
            </form>
          </div>

          <div className="lg:w-1/2 flex flex-col min-h-[300px]">
            <div className="px-4 py-2 bg-gray-50 border-b border-gray-100">
              <p className="text-xs font-medium text-gray-600">Live Preview</p>
            </div>
            <div className="flex-1 overflow-hidden">
              <SurveyPreview survey={survey} interactive />
            </div>
          </div>
        </div>
      )}

      {activeTab === 'builder' && (
        <div className="p-4 border-t border-gray-200">
          <BrazeUrlPanel
            survey={survey}
            onTemplateChange={handleBrazeTemplateChange}
          />
          {survey.braze_url_template && (
            <button
              type="button"
              onClick={saveBrazeTemplate}
              disabled={saving}
              className="mt-2 text-xs text-halo-blue hover:underline"
            >
              Save Braze URL template
            </button>
          )}
        </div>
      )}

      {activeTab === 'results' && (
        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          <SurveyResultsPanel surveyId={surveyId} survey={survey} />
        </div>
      )}
    </div>
  );
}
