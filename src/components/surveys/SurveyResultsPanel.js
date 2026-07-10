import React, { useEffect, useRef, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import ReactMarkdown from 'react-markdown';
import { Download, Loader2, Send, MessageSquare, BarChart3 } from 'lucide-react';
import {
  analyzeSurvey,
  exportSurveyResponses,
  getSurveyStats,
  listSurveyResponses,
} from '../../utils/haloSurveyApi';

const CHART_COLORS = ['#FFDD00', '#0066FF', '#000000', '#E6C700', '#0052CC'];

export default function SurveyResultsPanel({ surveyId, survey }) {
  const [tab, setTab] = useState('overview');
  const [stats, setStats] = useState(null);
  const [responses, setResponses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [analysis, setAnalysis] = useState('');
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [expandedId, setExpandedId] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (!surveyId) return;
    (async () => {
      setLoading(true);
      try {
        const [statsRes, respRes] = await Promise.all([
          getSurveyStats(surveyId),
          listSurveyResponses(surveyId),
        ]);
        if (statsRes.success) setStats(statsRes.stats);
        if (respRes.success) setResponses(respRes.responses || []);
      } catch {
        /* ignore */
      } finally {
        setLoading(false);
      }
    })();
  }, [surveyId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, analysisLoading]);

  const runAnalysis = async (question) => {
    setAnalysisLoading(true);
    try {
      const res = await analyzeSurvey(surveyId, {
        question,
        conversation_history: chatHistory,
      });
      if (res.success) {
        if (res.stats) setStats(res.stats);
        const text = res.analysis || '';
        setAnalysis(text);
        if (question) {
          setChatHistory((h) => [
            ...h,
            { role: 'user', content: question },
            { role: 'assistant', content: text },
          ]);
        }
      }
    } catch {
      setAnalysis('Analysis failed. Please try again.');
    } finally {
      setAnalysisLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const blob = await exportSurveyResponses(surveyId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${survey?.slug || surveyId}-responses.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      /* ignore */
    }
  };

  const handleChatSend = (e) => {
    e.preventDefault();
    if (!chatInput.trim() || analysisLoading) return;
    const q = chatInput.trim();
    setChatInput('');
    runAnalysis(q);
  };

  const handleTabChange = (id) => {
    setTab(id);
    if (id === 'analysis' && !analysis && surveyId && !analysisLoading) {
      runAnalysis();
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  const choiceQuestions = Object.entries(stats?.question_stats || {}).filter(
    ([, s]) => s.counts
  );

  return (
    <div className="space-y-4">
      <div className="flex gap-2 border-b border-gray-200 pb-2">
        {[
          { id: 'overview', label: 'Overview', icon: BarChart3 },
          { id: 'responses', label: 'Responses', icon: MessageSquare },
          { id: 'analysis', label: 'AI Analysis', icon: Send },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => handleTabChange(id)}
            className={`inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg ${
              tab === id ? 'bg-halo-yellow text-halo-black font-medium' : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <Icon className="h-4 w-4" /> {label}
          </button>
        ))}
        <div className="flex-1" />
        <button
          type="button"
          onClick={handleExport}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          <Download className="h-4 w-4" /> Export CSV
        </button>
      </div>

      {tab === 'overview' && stats && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Total', value: stats.total_responses },
              { label: 'Complete', value: stats.complete },
              { label: 'Ineligible', value: stats.ineligible },
              { label: 'Completion rate', value: `${stats.completion_rate}%` },
            ].map(({ label, value }) => (
              <div key={label} className="p-4 rounded-lg border border-gray-200 bg-white">
                <p className="text-xs text-gray-500">{label}</p>
                <p className="text-2xl font-bold text-halo-black">{value}</p>
              </div>
            ))}
          </div>

          {choiceQuestions.slice(0, 6).map(([qid, qstat]) => {
            const chartData = Object.entries(qstat.counts || {}).map(([name, count]) => ({
              name: name.length > 20 ? `${name.slice(0, 18)}…` : name,
              fullName: name,
              count,
            }));
            return (
              <div key={qid} className="p-4 border border-gray-200 rounded-lg bg-white">
                <p className="text-sm font-medium text-halo-black mb-3">{qstat.text}</p>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 8 }}>
                    <XAxis type="number" allowDecimals={false} />
                    <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v, _n, p) => [v, p.payload.fullName]} />
                    <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                      {chartData.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            );
          })}
        </div>
      )}

      {tab === 'responses' && (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-3 font-medium">Status</th>
                <th className="text-left p-3 font-medium">Started</th>
                <th className="text-left p-3 font-medium">Completed</th>
                <th className="text-left p-3 font-medium">External ID</th>
              </tr>
            </thead>
            <tbody>
              {responses.length === 0 ? (
                <tr>
                  <td colSpan={4} className="p-6 text-center text-gray-500">
                    No responses yet
                  </td>
                </tr>
              ) : (
                responses.map((r) => (
                  <React.Fragment key={r.response_id}>
                    <tr
                      className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer"
                      onClick={() =>
                        setExpandedId(expandedId === r.response_id ? null : r.response_id)
                      }
                    >
                      <td className="p-3">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                            r.status === 'complete'
                              ? 'bg-green-100 text-green-800'
                              : r.status === 'ineligible'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="p-3 text-gray-600">{r.started_at?.slice(0, 16)}</td>
                      <td className="p-3 text-gray-600">{r.completed_at?.slice(0, 16) || '—'}</td>
                      <td className="p-3 text-gray-600 font-mono text-xs">
                        {r.metadata?.external_id || '—'}
                      </td>
                    </tr>
                    {expandedId === r.response_id && (
                      <tr className="bg-gray-50">
                        <td colSpan={4} className="p-4">
                          <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                            {JSON.stringify(r.answers, null, 2)}
                          </pre>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'analysis' && (
        <div className="space-y-4">
          <div className="p-4 border border-gray-200 rounded-lg bg-white min-h-[200px] prose prose-sm max-w-none">
            {analysisLoading && !analysis ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-halo-yellow" />
              </div>
            ) : (
              <ReactMarkdown>{analysis || 'Run analysis to see insights.'}</ReactMarkdown>
            )}
          </div>

          {chatHistory.length > 0 && (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {chatHistory.map((msg, i) => (
                <div
                  key={i}
                  className={`p-2 rounded-lg text-sm ${
                    msg.role === 'user' ? 'bg-halo-yellow-light ml-8' : 'bg-gray-100 mr-8'
                  }`}
                >
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              ))}
            </div>
          )}

          <form onSubmit={handleChatSend} className="flex gap-2">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask about the results..."
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-halo-yellow"
            />
            <button
              type="submit"
              disabled={analysisLoading || !chatInput.trim()}
              className="p-2 bg-halo-yellow text-halo-black rounded-lg disabled:opacity-50"
            >
              {analysisLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Send className="h-5 w-5" />
              )}
            </button>
          </form>
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
