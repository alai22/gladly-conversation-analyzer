import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { AlertCircle, CheckCircle2, Clock, Dog, FolderOpen, Play, RefreshCw, Users } from 'lucide-react';
import axios from 'axios';

const PROCESS_POLL_MS = 4000;
const SUMMARY_STORAGE_KEY = 'halo_labeling_summary_v1';

const COLORS = [
  '#4285F4', '#EA4335', '#FBBC04', '#34A853', '#FF6D01', '#9334E6',
  '#00ACC1', '#64B5F6', '#F28B82', '#81C784', '#FFB74D', '#BA68C8',
];

function formatSecondsShort(seconds) {
  const s = Number(seconds) || 0;
  if (s < 60) return `${s.toFixed(1)}s`;
  const mins = Math.floor(s / 60);
  const rem = s - mins * 60;
  if (mins < 60) return `${mins}m ${rem.toFixed(0)}s`;
  const hours = Math.floor(mins / 60);
  const remMins = mins % 60;
  return `${hours}h ${remMins}m`;
}

function formatUpdatedAt(iso) {
  if (!iso) return null;
  try {
    const d = new Date(iso.endsWith('Z') ? iso : `${iso}Z`);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

function readStoredSummary() {
  try {
    const raw = sessionStorage.getItem(SUMMARY_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed?.data) return null;
    return parsed;
  } catch {
    return null;
  }
}

function writeStoredSummary({ data, generatedAt, cached, stale }) {
  try {
    sessionStorage.setItem(
      SUMMARY_STORAGE_KEY,
      JSON.stringify({
        data,
        generatedAt: generatedAt || null,
        cached: Boolean(cached),
        stale: Boolean(stale),
        savedAt: Date.now(),
      })
    );
  } catch {
    // ignore quota / private mode
  }
}

const LabelingDataDashboard = () => {
  const stored = useMemo(() => readStoredSummary(), []);
  const [data, setData] = useState(stored?.data || null);
  const [status, setStatus] = useState(null);
  const [processReport, setProcessReport] = useState(null);
  const [processInfo, setProcessInfo] = useState(null);
  const [loading, setLoading] = useState(!stored?.data);
  const [processing, setProcessing] = useState(false);
  const [processNotice, setProcessNotice] = useState(null); // success | error banner after job
  const [error, setError] = useState(null);
  const [cached, setCached] = useState(Boolean(stored?.cached));
  const [stale, setStale] = useState(Boolean(stored?.stale));
  const [generatedAt, setGeneratedAt] = useState(stored?.generatedAt || null);
  const [expandedUser, setExpandedUser] = useState(null);
  const wasProcessingRef = useRef(false);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await axios.get('/api/labeling/status');
      if (response.data.success) {
        const next = response.data.data;
        setStatus(next);
        const proc = next?.process || null;
        setProcessInfo(proc);
        if (proc?.last_report) {
          setProcessReport(proc.last_report);
        }
        const running = Boolean(proc?.running);
        setProcessing(running);
        return next;
      }
    } catch (err) {
      // Non-fatal; summary can still load
      console.error('Failed to load labeling status', err);
    }
    return null;
  }, []);

  const fetchSummary = useCallback(async ({ refresh = false } = {}) => {
    // Keep showing last results while refreshing; only block when we have nothing.
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get('/api/labeling/summary', {
        params: refresh ? { refresh: 1 } : undefined,
      });
      if (response.data.success) {
        const nextData = response.data.data;
        const nextGenerated = response.data.generated_at || null;
        const nextCached = Boolean(response.data.cached);
        const nextStale = Boolean(response.data.stale);
        setData(nextData);
        setCached(nextCached);
        setStale(nextStale);
        setGeneratedAt(nextGenerated);
        writeStoredSummary({
          data: nextData,
          generatedAt: nextGenerated,
          cached: nextCached,
          stale: nextStale,
        });
      } else {
        setError(response.data.error || 'Failed to load labeling data');
      }
    } catch (err) {
      const errorMsg =
        err.response?.data?.error ||
        err.response?.data?.message ||
        err.message ||
        'Failed to load labeling data';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  }, []);

  const processStaging = useCallback(async () => {
    setError(null);
    setProcessNotice(null);
    try {
      const response = await axios.post('/api/labeling/process', {
        dry_run: false,
        clear_output: true,
        async: true,
      });
      if (!response.data.success) {
        throw new Error(response.data.error || 'Process failed');
      }
      wasProcessingRef.current = true;
      setProcessing(true);
      setProcessInfo(response.data.data || { running: true, message: response.data.message });
      setProcessNotice({
        type: 'info',
        text: 'Processing started in the background. Safe to leave this tab — it keeps running on the server.',
      });
      await fetchStatus();
    } catch (err) {
      if (err.response?.status === 409) {
        wasProcessingRef.current = true;
        setProcessing(true);
        setProcessInfo(err.response.data?.data || { running: true });
        setProcessNotice({
          type: 'info',
          text: 'A process is already running. Waiting for it to finish…',
        });
        await fetchStatus();
        return;
      }
      const errorMsg =
        err.response?.data?.error ||
        err.response?.data?.message ||
        err.message ||
        'Failed to process staging';
      setError(errorMsg);
      setProcessing(false);
    }
  }, [fetchStatus]);

  useEffect(() => {
    fetchStatus();
    // Prefer cached/last results; only full-screen wait when nothing is stored yet
    fetchSummary({ refresh: false });
  }, [fetchStatus, fetchSummary]);

  // If server returned a stale snapshot, poll briefly so background rescan can land
  useEffect(() => {
    if (!stale) return undefined;
    let cancelled = false;
    let attempts = 0;
    const id = setInterval(async () => {
      attempts += 1;
      if (cancelled || attempts > 6) {
        clearInterval(id);
        return;
      }
      try {
        const response = await axios.get('/api/labeling/summary');
        if (!response.data?.success || cancelled) return;
        if (!response.data.stale) {
          setData(response.data.data);
          setCached(Boolean(response.data.cached));
          setStale(false);
          setGeneratedAt(response.data.generated_at || null);
          writeStoredSummary({
            data: response.data.data,
            generatedAt: response.data.generated_at || null,
            cached: Boolean(response.data.cached),
            stale: false,
          });
          clearInterval(id);
        }
      } catch {
        // keep showing last results
      }
    }, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [stale]);

  // Poll while a background process is running (also resumes after page reload)
  useEffect(() => {
    const running = Boolean(processInfo?.running || processing);
    if (!running) return undefined;

    wasProcessingRef.current = true;
    const id = setInterval(async () => {
      const next = await fetchStatus();
      const stillRunning = Boolean(next?.process?.running);
      if (!stillRunning && wasProcessingRef.current) {
        wasProcessingRef.current = false;
        const proc = next?.process;
        if (proc?.last_error) {
          setProcessNotice({ type: 'error', text: `Process failed: ${proc.last_error}` });
        } else {
          setProcessNotice({
            type: 'success',
            text: proc?.message || 'Processing finished. Refreshing summary…',
          });
          await fetchSummary({ refresh: true });
        }
      }
    }, PROCESS_POLL_MS);

    return () => clearInterval(id);
  }, [processInfo?.running, processing, fetchStatus, fetchSummary]);

  const totals = data?.totals || {};
  const activities = data?.activities || [];
  const users = useMemo(() => {
    const list = data?.users || [];
    return [...list].sort(
      (a, b) => (b.total_duration_seconds || 0) - (a.total_duration_seconds || 0)
    );
  }, [data?.users]);

  const chartData = useMemo(
    () =>
      activities.map((a) => ({
        name: a.name,
        label: a.label,
        seconds: a.seconds,
      })),
    [activities]
  );

  const userContributionData = useMemo(
    () =>
      users.map((u) => ({
        email: u.email,
        label: (u.email || '').split('@')[0] || u.email,
        seconds: u.total_duration_seconds || 0,
        files: u.files || 0,
        sessions: u.sessions || 0,
        human: u.total_duration_human || formatSecondsShort(u.total_duration_seconds),
      })),
    [users]
  );

  const stagingEmails = Object.keys(status?.staging_by_email || {});
  const outputEmails = status?.output_emails || [];
  const unprocessedEmails = stagingEmails.filter((e) => !outputEmails.includes(e));
  const userChartHeight = Math.max(220, userContributionData.length * 48 + 48);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading labeling data from S3...</p>
          <p className="text-xs text-gray-400 mt-2">Scanning extracted-txt and summing durations</p>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-center max-w-md">
          <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-4" />
          <p className="text-red-600 mb-2 font-semibold">Error loading labeling data</p>
          <p className="text-gray-600 text-sm mb-4">{error}</p>
          <button
            type="button"
            onClick={() => fetchSummary({ refresh: true })}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col p-6 bg-gray-50" style={{ minHeight: '100vh' }}>
      <div className="flex items-center justify-between mb-6 flex-shrink-0 gap-4">
        <div className="min-w-0">
          <h2 className="text-2xl font-bold text-gray-900">Labeling Data</h2>
          <p className="text-sm text-gray-500 mt-1">
            {generatedAt ? `Updated ${formatUpdatedAt(generatedAt)}` : 'Activity labeling totals'}
            {loading && data ? (
              <span className="ml-2 inline-flex items-center gap-1 text-xs text-blue-600">
                <RefreshCw className="h-3 w-3 animate-spin" />
                Checking…
              </span>
            ) : stale ? (
              <span className="ml-2 text-xs text-gray-400">Refreshing in background…</span>
            ) : null}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={processStaging}
            disabled={processing}
            className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700 disabled:opacity-50"
            title="Starts a background job: staging → extracted-txt/<email>/<collar-sn>/"
          >
            {processing ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {processing ? 'Processing…' : 'Process staging'}
          </button>
          <button
            type="button"
            onClick={() => {
              fetchStatus();
              fetchSummary({ refresh: true });
            }}
            disabled={loading && !data}
            className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && data ? (
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-900">
          Couldn’t refresh summary ({error}). Showing last results.
        </div>
      ) : null}

      {unprocessedEmails.length > 0 ? (
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-900">
          Staging has {unprocessedEmails.length} labeler(s) not in output yet:{' '}
          {unprocessedEmails.join(', ')}. Click <span className="font-medium">Process staging</span> to
          include them in charts.
        </div>
      ) : null}

      {processing ? (
        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-900 flex items-start gap-3">
          <RefreshCw className="h-5 w-5 animate-spin flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-medium">Processing in progress</div>
            <div className="mt-0.5">
              {processInfo?.message || 'Copying staging files into extracted-txt by collar SN…'}
            </div>
            <div className="mt-1 text-xs text-blue-800">
              Safe to close or leave this tab. Started{' '}
              {processInfo?.started_at ? processInfo.started_at.replace('T', ' ').replace('Z', ' UTC') : 'just now'}.
            </div>
          </div>
        </div>
      ) : null}

      {!processing && processNotice ? (
        <div
          className={`mb-4 p-4 rounded-lg text-sm flex items-start gap-3 border ${
            processNotice.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
              : processNotice.type === 'error'
                ? 'bg-red-50 border-red-200 text-red-900'
                : 'bg-blue-50 border-blue-200 text-blue-900'
          }`}
        >
          {processNotice.type === 'success' ? (
            <CheckCircle2 className="h-5 w-5 flex-shrink-0 mt-0.5" />
          ) : processNotice.type === 'error' ? (
            <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
          ) : (
            <RefreshCw className="h-5 w-5 flex-shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <div>{processNotice.text}</div>
            {processReport && processNotice.type === 'success' ? (
              <div className="mt-1 text-xs opacity-80">
                Copied {processReport.copied} files · {processReport.sessions} sessions ·{' '}
                {(processReport.errors || []).length} errors
              </div>
            ) : null}
          </div>
          <button
            type="button"
            onClick={() => setProcessNotice(null)}
            className="text-xs underline opacity-70 hover:opacity-100"
          >
            Dismiss
          </button>
        </div>
      ) : null}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <SummaryCard
          icon={Users}
          label="Processed users"
          value={totals.users ?? 0}
          hint={
            stagingEmails.length > (totals.users ?? 0)
              ? `${stagingEmails.length} in staging`
              : null
          }
        />
        <SummaryCard icon={FolderOpen} label="Sessions" value={totals.sessions ?? 0} />
        <SummaryCard icon={Dog} label="Files" value={totals.files ?? 0} />
        <SummaryCard
          icon={Clock}
          label="Total labeled duration"
          value={totals.duration_human || formatSecondsShort(totals.duration_seconds)}
        />
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-5 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-1">Contribution by user</h3>
        <p className="text-sm text-gray-500 mb-4">
          Ranked by total labeled duration from processed <span className="font-mono text-xs">*_durations.txt</span>
        </p>
        {userContributionData.length === 0 ? (
          <p className="text-sm text-gray-500">
            No processed users yet. Click Process staging to build extracted-txt from staging.
          </p>
        ) : (
          <>
            <div style={{ height: userChartHeight }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={userContributionData}
                  layout="vertical"
                  margin={{ top: 8, right: 24, left: 8, bottom: 8 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis
                    type="number"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(v) => formatSecondsShort(v)}
                  />
                  <YAxis
                    type="category"
                    dataKey="label"
                    width={120}
                    tick={{ fontSize: 12 }}
                  />
                  <Tooltip
                    formatter={(value, _name, props) => [
                      `${formatSecondsShort(value)} · ${props.payload.sessions} sessions · ${props.payload.files} files`,
                      props.payload.email,
                    ]}
                  />
                  <Bar dataKey="seconds" radius={[0, 4, 4, 0]}>
                    {userContributionData.map((entry, index) => (
                      <Cell key={entry.email} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="py-2 pr-4 font-medium">Rank</th>
                    <th className="py-2 pr-4 font-medium">Labeler</th>
                    <th className="py-2 pr-4 font-medium">Duration</th>
                    <th className="py-2 pr-4 font-medium">Sessions</th>
                    <th className="py-2 font-medium">Files</th>
                  </tr>
                </thead>
                <tbody>
                  {userContributionData.map((u, i) => (
                    <tr key={u.email} className="border-b border-gray-100">
                      <td className="py-2 pr-4 text-gray-500">{i + 1}</td>
                      <td className="py-2 pr-4 text-gray-900">{u.email}</td>
                      <td className="py-2 pr-4 text-gray-700">{u.human}</td>
                      <td className="py-2 pr-4 text-gray-500">{u.sessions}</td>
                      <td className="py-2 text-gray-500">{u.files}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-5 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-1">Duration by activity</h3>
        <p className="text-sm text-gray-500 mb-4">
          Summed from <span className="font-mono text-xs">*_durations.txt</span> across all users
        </p>
        {chartData.length === 0 ? (
          <p className="text-sm text-gray-500">No non-zero activity durations found.</p>
        ) : (
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis
                  tick={{ fontSize: 12 }}
                  tickFormatter={(v) => formatSecondsShort(v)}
                />
                <Tooltip
                  formatter={(value, _name, props) => [
                    `${formatSecondsShort(value)} (${Number(value).toFixed(1)}s)`,
                    props.payload.label,
                  ]}
                />
                <Bar dataKey="seconds" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={entry.label} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {activities.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="py-2 pr-4 font-medium">Activity</th>
                  <th className="py-2 pr-4 font-medium">Duration</th>
                  <th className="py-2 font-medium">Seconds</th>
                </tr>
              </thead>
              <tbody>
                {activities.map((a) => (
                  <tr key={a.label} className="border-b border-gray-100">
                    <td className="py-2 pr-4 text-gray-900">{a.label}</td>
                    <td className="py-2 pr-4 text-gray-700">{a.human}</td>
                    <td className="py-2 text-gray-500">{a.seconds.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <h3 className="text-lg font-semibold text-gray-900 mb-1">By user (detail)</h3>
        <p className="text-sm text-gray-500 mb-4">
          Ranked by contribution; expand for per-activity and collar SN breakdown
        </p>

        <div className="space-y-3">
          {users.map((user) => {
            const isOpen = expandedUser === user.email;
            const kinds = user.by_kind || {};
            return (
              <div key={user.email} className="border border-gray-200 rounded-lg overflow-hidden">
                <button
                  type="button"
                  onClick={() => setExpandedUser(isOpen ? null : user.email)}
                  className="w-full flex items-center justify-between gap-4 px-4 py-3 text-left hover:bg-gray-50"
                >
                  <div className="min-w-0">
                    <div className="font-medium text-gray-900 truncate">{user.email}</div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {user.sessions} sessions · {user.files} files · collars {(user.collar_sns || []).length} ·
                      collar_collected {kinds.collar_collected || 0} ·
                      durations {kinds.durations || 0} · user_reported {kinds.user_reported || 0}
                    </div>
                    {(user.collar_sns || []).length > 0 ? (
                      <div className="text-xs text-gray-400 mt-0.5 truncate">
                        SN: {(user.collar_sns || []).join(', ')}
                      </div>
                    ) : null}
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-sm font-semibold text-gray-900">
                      {user.total_duration_human || formatSecondsShort(user.total_duration_seconds)}
                    </div>
                    <div className="text-xs text-gray-400">{isOpen ? 'Hide' : 'Show'} activities</div>
                  </div>
                </button>

                {isOpen ? (
                  <div className="px-4 pb-4 border-t border-gray-100 bg-gray-50">
                    {(user.activities || []).length === 0 ? (
                      <p className="text-sm text-gray-500 pt-3">No non-zero durations for this user.</p>
                    ) : (
                      <div className="pt-3 overflow-x-auto">
                        <table className="min-w-full text-sm">
                          <thead>
                            <tr className="text-left text-gray-500 border-b border-gray-200">
                              <th className="py-2 pr-4 font-medium">Activity</th>
                              <th className="py-2 pr-4 font-medium">Duration</th>
                              <th className="py-2 font-medium">Seconds</th>
                            </tr>
                          </thead>
                          <tbody>
                            {user.activities.map((a) => (
                              <tr key={`${user.email}-${a.label}`} className="border-b border-gray-100">
                                <td className="py-2 pr-4 text-gray-900">{a.label}</td>
                                <td className="py-2 pr-4 text-gray-700">{a.human}</td>
                                <td className="py-2 text-gray-500">{a.seconds.toFixed(1)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {(user.collars || []).length > 0 ? (
                      <div className="mt-4 space-y-2">
                        <div className="text-xs font-medium text-gray-600 uppercase tracking-wide">
                          By collar SN
                        </div>
                        {user.collars.map((collar) => (
                          <div
                            key={`${user.email}-${collar.collar_sn}`}
                            className="bg-white border border-gray-200 rounded-md px-3 py-2"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <div className="font-mono text-sm text-gray-900">{collar.collar_sn}</div>
                              <div className="text-xs text-gray-500">
                                {collar.sessions} sessions · {collar.files} files ·{' '}
                                {collar.total_duration_human}
                              </div>
                            </div>
                            {(collar.activities || []).length > 0 ? (
                              <div className="mt-1 text-xs text-gray-500">
                                {collar.activities
                                  .map((a) => `${a.name} ${a.human}`)
                                  .join(' · ')}
                              </div>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    ) : null}

                    {Object.keys(user.collar_activity_events || {}).length > 0 ? (
                      <div className="mt-3 text-xs text-gray-500">
                        Collar transitions:{' '}
                        {Object.entries(user.collar_activity_events)
                          .map(([label, count]) => `${label.split(' ')[0]} ${count}`)
                          .join(' · ')}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>

      <details className="mt-8 group">
        <summary className="cursor-pointer list-none text-xs text-gray-500 hover:text-gray-700 inline-flex items-center gap-1">
          <span className="underline decoration-dotted underline-offset-2">Pipeline & source details</span>
          <span className="text-gray-400 group-open:hidden">▸</span>
          <span className="text-gray-400 hidden group-open:inline">▾</span>
        </summary>
        <div className="mt-3 p-4 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 space-y-2">
          <div>
            <span className="text-gray-500">Source:</span>{' '}
            <span className="font-mono text-xs">
              s3://{data?.bucket}/{data?.prefix}
            </span>
            {cached ? (
              <span className="ml-2 text-xs text-gray-400">
                {stale ? '(stale cache)' : '(cached)'}
              </span>
            ) : null}
          </div>
          {status ? (
            <>
              <div>
                <span className="text-gray-500">Staging:</span>{' '}
                <span className="font-mono">{status.staging_extracted_files ?? 0}</span> extracted
                files in <span className="font-mono">{status.staging_batches ?? 0}</span> Gmail
                batches
                {status.staging_by_email
                  ? ` (${Object.entries(status.staging_by_email)
                      .map(([email, n]) => `${email}: ${n}`)
                      .join(' · ')})`
                  : ''}
              </div>
              <div>
                <span className="text-gray-500">Output:</span>{' '}
                <span className="font-mono">{status.output_files ?? 0}</span> files under{' '}
                <span className="font-mono text-xs">{status.output_prefix}</span>
                {(status.output_emails || []).length
                  ? ` (${status.output_emails.join(', ')})`
                  : ' (empty — click Process staging)'}
              </div>
              {processReport ? (
                <div className="text-xs text-gray-500">
                  Last process: copied {processReport.copied}, sessions {processReport.sessions},
                  unknown SN {processReport.unknown_sn_sessions}, errors{' '}
                  {(processReport.errors || []).length}
                </div>
              ) : null}
            </>
          ) : (
            <div className="text-xs text-gray-400">Pipeline status not loaded yet.</div>
          )}
        </div>
      </details>
    </div>
  );
};

function SummaryCard({ icon: Icon, label, value, hint }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center gap-2 text-gray-500 text-xs uppercase tracking-wide mb-2">
        <Icon className="h-4 w-4" />
        {label}
      </div>
      <div className="text-2xl font-semibold text-gray-900">{value}</div>
      {hint ? <div className="text-xs text-amber-700 mt-1">{hint}</div> : null}
    </div>
  );
}

export default LabelingDataDashboard;
