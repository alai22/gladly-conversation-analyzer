import React, { useEffect, useState } from 'react';
import { Download, ArrowLeft, Loader2 } from 'lucide-react';
import { getInterviewInsights, exportInterviewInsights } from '../../utils/interviewApi';

function Section({ title, children }) {
  return (
    <section className="mb-6">
      <h4 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-2">{title}</h4>
      {children}
    </section>
  );
}

function BulletList({ items }) {
  if (!items?.length) return <p className="text-sm text-gray-500 italic">None captured</p>;
  return (
    <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
      {items.map((item, i) => (
        <li key={i}>{typeof item === 'string' ? item : JSON.stringify(item)}</li>
      ))}
    </ul>
  );
}

export default function InterviewResultsPanel({ sessionId, onBack }) {
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getInterviewInsights(sessionId);
        if (!cancelled && data.success) {
          setInsights(data.insights);
        }
      } catch (err) {
        if (!cancelled) setError(err.response?.data?.error || err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [sessionId]);

  const handleExport = async () => {
    try {
      const blob = await exportInterviewInsights(sessionId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `interview-${sessionId.slice(0, 8)}-insights.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-500 py-8">
        <Loader2 className="h-5 w-5 animate-spin" /> Generating insights…
      </div>
    );
  }

  if (error) {
    return <p className="text-red-600 text-sm">{error}</p>;
  }

  if (!insights) {
    return <p className="text-gray-500 text-sm">No insights available.</p>;
  }

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
        <button
          type="button"
          onClick={handleExport}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
        >
          <Download className="h-4 w-4" /> Export JSON
        </button>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm space-y-2 mb-6">
        <h3 className="text-xl font-semibold text-gray-900">{insights.topic}</h3>
        <p className="text-sm text-gray-600">Audience: {insights.audience}</p>
        <p className="text-sm text-gray-600">
          Duration: {insights.duration_minutes} min · Consent: {insights.consent?.given ? 'yes' : 'no'}
        </p>
        {insights.risk_flags?.length > 0 && (
          <p className="text-sm text-amber-700">Risk flags: {insights.risk_flags.join(', ')}</p>
        )}
      </div>

      <Section title="Key takeaways">
        <BulletList items={insights.key_takeaways} />
      </Section>

      <Section title="Themes">
        {(insights.themes || []).map((t, i) => (
          <div key={i} className="mb-3 p-3 bg-gray-50 rounded-lg">
            <p className="font-medium text-gray-900">{t.theme}</p>
            <p className="text-xs text-gray-500 mb-1">Confidence: {t.confidence}</p>
            <BulletList items={t.evidence_quotes} />
          </div>
        ))}
      </Section>

      <Section title="Pain points">
        <BulletList items={insights.pain_points} />
      </Section>

      <Section title="Current workarounds">
        <BulletList items={insights.current_workarounds} />
      </Section>

      <Section title="Jobs to be done">
        <BulletList items={insights.jobs_to_be_done} />
      </Section>

      <Section title="Moments that matter">
        <BulletList items={insights.moments_that_matter} />
      </Section>

      <Section title="Opportunities">
        {(insights.opportunities || []).length === 0 ? (
          <BulletList items={[]} />
        ) : (
          insights.opportunities.map((o, i) => (
            <div key={i} className="mb-2 text-sm text-gray-700">
              <span className="font-medium">{o.opportunity}</span> — impact: {o.impact}. {o.notes}
            </div>
          ))
        )}
      </Section>

      <Section title="Recommended action">
        <p className="text-sm text-gray-800">{insights.recommended_action || '—'}</p>
      </Section>

      <Section title="Open questions">
        <BulletList items={insights.open_questions} />
      </Section>

      <Section title="Transcript">
        <div className="space-y-2 max-h-96 overflow-y-auto border border-gray-100 rounded-lg p-3 bg-gray-50">
          {(insights.full_transcript || []).map((entry, i) => (
            <div
              key={i}
              className={`text-sm ${entry.role === 'participant' ? 'text-right' : 'text-left'}`}
            >
              <span
                className={`inline-block px-3 py-2 rounded-lg max-w-[85%] ${
                  entry.role === 'participant'
                    ? 'bg-indigo-100 text-indigo-900'
                    : 'bg-white border border-gray-200 text-gray-800'
                }`}
              >
                {entry.text}
              </span>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}
