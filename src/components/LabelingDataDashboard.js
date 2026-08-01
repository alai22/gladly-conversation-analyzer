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
const SUMMARY_STORAGE_KEY = 'halo_labeling_summary_v3';

const COLORS = [
  '#4285F4', '#EA4335', '#FBBC04', '#34A853', '#FF6D01', '#9334E6',
  '#00ACC1', '#64B5F6', '#F28B82', '#81C784', '#FFB74D', '#BA68C8',
];

const GPS_LABEL_DISPLAY = {
  IndoorBlocked: 'Indoor (blocked)',
  IndoorSeeSky: 'Indoor (see sky)',
  Door: 'Door',
  OutdoorCovered: 'Outdoor (covered)',
  OutdoorOpenSky: 'Outdoor (open sky)',
};

function displayLabel(name) {
  return GPS_LABEL_DISPLAY[name] || name;
}

function CollapsibleTable({ label = 'Show data table', children }) {
  return (
    <details className="mt-4 group">
      <summary className="cursor-pointer list-none text-xs text-gray-500 hover:text-gray-700 inline-flex items-center gap-1 select-none">
        <span className="underline decoration-dotted underline-offset-2">{label}</span>
        <span className="text-gray-400 group-open:hidden">▸</span>
        <span className="text-gray-400 hidden group-open:inline">▾</span>
      </summary>
      <div className="mt-3 overflow-x-auto">{children}</div>
    </details>
  );
}

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
  const [promoting, setPromoting] = useState(false);
  const [error, setError] = useState(null);
  const [cached, setCached] = useState(Boolean(stored?.cached));
  const [stale, setStale] = useState(Boolean(stored?.stale));
  const [generatedAt, setGeneratedAt] = useState(stored?.generatedAt || null);
  const [expandedUser, setExpandedUser] = useState(null);
  const wasProcessingRef = useRef(false);
  const autoPromoteAttemptedRef = useRef(false);

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
        setPromoting(running && proc?.job === 'promote-forwards');
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

  const promoteForwards = useCallback(
    async ({ silent = false } = {}) => {
      setError(null);
      if (!silent) setProcessNotice(null);
      try {
        const response = await axios.post('/api/labeling/promote-forwards', {
          async: true,
        });
        if (!response.data.success) {
          throw new Error(response.data.error || 'Promote failed');
        }
        wasProcessingRef.current = true;
        setProcessing(true);
        setPromoting(true);
        setProcessInfo(
          response.data.data || {
            running: true,
            job: 'promote-forwards',
            message: response.data.message,
          }
        );
        setProcessNotice({
          type: 'info',
          text: silent
            ? 'Small forward batch detected — promoting into staging automatically…'
            : 'Promoting forwarded quarantine batches in the background. Safe to leave this tab.',
        });
        await fetchStatus();
      } catch (err) {
        if (err.response?.status === 409) {
          wasProcessingRef.current = true;
          setProcessing(true);
          setProcessInfo(err.response.data?.data || { running: true });
          setProcessNotice({
            type: 'info',
            text: 'A labeling job is already running. Waiting for it to finish…',
          });
          await fetchStatus();
          return;
        }
        const errorMsg =
          err.response?.data?.error ||
          err.response?.data?.message ||
          err.message ||
          'Failed to promote forwards';
        if (!silent) {
          setError(errorMsg);
        } else {
          setProcessNotice({
            type: 'error',
            text: `Auto-promote failed: ${errorMsg}`,
          });
        }
        setProcessing(false);
        setPromoting(false);
      }
    },
    [fetchStatus]
  );

  useEffect(() => {
    fetchStatus();
    // Prefer cached/last results; only full-screen wait when nothing is stored yet
    fetchSummary({ refresh: false });
  }, [fetchStatus, fetchSummary]);

  // Auto-promote tiny quarantine batches on load; larger ones need a click.
  useEffect(() => {
    const pending = status?.pending_forwards;
    if (!pending || autoPromoteAttemptedRef.current) return;
    if (processing || processInfo?.running) return;
    if (!pending.auto_promote || !(pending.pending_count > 0)) return;
    autoPromoteAttemptedRef.current = true;
    promoteForwards({ silent: true });
  }, [status?.pending_forwards, processing, processInfo?.running, promoteForwards]);

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
          setProcessNotice({
            type: 'error',
            text: `${proc?.job === 'promote-forwards' ? 'Promote' : 'Process'} failed: ${proc.last_error}`,
          });
        } else if (proc?.job === 'promote-forwards') {
          setProcessNotice({
            type: 'success',
            text:
              proc?.message ||
              'Forwards promoted into staging. Click Process staging to include them in charts.',
          });
          setPromoting(false);
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
  const pendingForwards = status?.pending_forwards || null;
  const stagingHealth = status?.staging_health || null;
  const stagingHealthWarnings = stagingHealth?.warnings || [];
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

  const byDate = data?.by_date || [];
  const byDateChartData = useMemo(
    () =>
      byDate.map((d) => ({
        date: d.date,
        label: d.date && d.date.length >= 10 ? d.date.slice(5) : d.date, // MM-DD
        seconds: d.duration_seconds || 0,
        sessions: d.sessions || 0,
        files: d.files || 0,
        users: d.users || 0,
        human: d.duration_human || formatSecondsShort(d.duration_seconds),
      })),
    [byDate]
  );

  const gps = data?.gps || null;
  const gpsTotals = gps?.totals || {};
  const gpsActivities = gps?.activities || [];
  const gpsUsers = useMemo(() => {
    const list = gps?.users || [];
    return [...list].sort(
      (a, b) => (b.total_duration_seconds || 0) - (a.total_duration_seconds || 0)
    );
  }, [gps?.users]);
  const gpsChartData = useMemo(
    () =>
      gpsActivities.map((a) => ({
        name: displayLabel(a.name),
        label: displayLabel(a.label),
        seconds: a.seconds,
      })),
    [gpsActivities]
  );
  const gpsUserContributionData = useMemo(
    () =>
      gpsUsers.map((u) => ({
        email: u.email,
        label: (u.email || '').split('@')[0] || u.email,
        seconds: u.total_duration_seconds || 0,
        files: u.files || 0,
        sessions: u.sessions || 0,
        human: u.total_duration_human || formatSecondsShort(u.total_duration_seconds),
      })),
    [gpsUsers]
  );
  const gpsByDateChartData = useMemo(
    () =>
      (gps?.by_date || []).map((d) => ({
        date: d.date,
        label: d.date && d.date.length >= 10 ? d.date.slice(5) : d.date,
        seconds: d.duration_seconds || 0,
        sessions: d.sessions || 0,
        files: d.files || 0,
        users: d.users || 0,
        human: d.duration_human || formatSecondsShort(d.duration_seconds),
      })),
    [gps?.by_date]
  );

  const stagingEmails = Object.keys(status?.staging_by_email || {});
  const outputEmails = status?.output_emails || [];
  const unprocessedEmails = stagingEmails.filter((e) => !outputEmails.includes(e));
  const userChartHeight = Math.max(220, userContributionData.length * 48 + 48);
  const gpsUserChartHeight = Math.max(180, gpsUserContributionData.length * 48 + 48);
  const hasGps = (gpsTotals.files || 0) > 0 || gpsChartData.length > 0;

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

      {stagingHealthWarnings.length > 0 ? (
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-950">
          <div className="font-medium">Staging health</div>
          <div className="mt-1 text-xs text-amber-900/90">
            {stagingHealth.raw_extracted_files} files → ~{stagingHealth.unique_files_after_dedupe}{' '}
            unique after dedupe ({stagingHealth.duplicate_ratio}x)
            {stagingHealth.multi_message_sessions
              ? ` · ${stagingHealth.multi_message_sessions} sessions in multiple emails`
              : ''}
            {stagingHealth.incomplete_sessions
              ? ` · ${stagingHealth.incomplete_sessions} incomplete`
              : ''}
            {stagingHealth.size_mismatch_sessions
              ? ` · ${stagingHealth.size_mismatch_sessions} size mismatches`
              : ''}
          </div>
          <ul className="mt-2 list-disc pl-5 space-y-1">
            {stagingHealthWarnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {pendingForwards?.pending_count > 0 && !pendingForwards.auto_promote && !promoting ? (
        <div className="mb-4 p-3 bg-violet-50 border border-violet-200 rounded-lg text-sm text-violet-950 flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="flex-1 min-w-0">
            <div className="font-medium">Forwarded quarantine ready to promote</div>
            <div className="mt-0.5">
              {pendingForwards.pending_count} batch(es) / {pendingForwards.pending_keys} files
              resolved to{' '}
              {(pendingForwards.pending || [])
                .map((b) => b.labeler_email)
                .filter(Boolean)
                .join(', ') || 'labelers'}
              . This is too large to auto-run on page load — promote into staging, then Process
              staging.
            </div>
          </div>
          <button
            type="button"
            onClick={() => promoteForwards()}
            disabled={processing}
            className="inline-flex items-center justify-center gap-2 px-3 py-2 bg-violet-700 text-white rounded-lg text-sm hover:bg-violet-800 disabled:opacity-50 shrink-0"
          >
            <Play className="h-4 w-4" />
            Promote forwards
          </button>
        </div>
      ) : null}

      {(pendingForwards?.unresolved || []).length > 0 ? (
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-900">
          {(pendingForwards.unresolved || []).length} forward batch(es) have no recoverable
          original From in meta/body — add <span className="font-mono">Email Body</span> in Make or
          promote via CLI with <span className="font-mono">--map</span>.
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
            <div className="font-medium">
              {promoting || processInfo?.job === 'promote-forwards'
                ? 'Promoting forwards'
                : 'Processing in progress'}
            </div>
            <div className="mt-0.5">
              {processInfo?.message ||
                (promoting
                  ? 'Copying quarantine batches into staging/<labeler>/…'
                  : 'Copying staging files into extracted-txt by collar SN…')}
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

      <div className="mb-2">
        <h2 className="text-xl font-semibold text-gray-900">Posture</h2>
        <p className="text-sm text-gray-500">
          From <span className="font-mono text-xs">activity_session_*</span>
        </p>
      </div>

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
        <h3 className="text-lg font-semibold text-gray-900 mb-1">Duration by posture</h3>
        <p className="text-sm text-gray-500 mb-4">
          Posture / activity labels from{' '}
          <span className="font-mono text-xs">activity_session_*_durations.txt</span>
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
          <CollapsibleTable label="Show posture table">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="py-2 pr-4 font-medium">Posture</th>
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
          </CollapsibleTable>
        ) : null}
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-5 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-1">Contribution by labeler</h3>
        <p className="text-sm text-gray-500 mb-4">
          Ranked by total labeled duration from processed{' '}
          <span className="font-mono text-xs">activity_session_*_durations.txt</span>
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
            <CollapsibleTable label="Show labeler table">
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
            </CollapsibleTable>
          </>
        )}
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-5 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-1">Volume by date</h3>
        <p className="text-sm text-gray-500 mb-4">
          Labeled duration per session day (from activity_session timestamps)
        </p>
        {byDateChartData.length === 0 ? (
          <p className="text-sm text-gray-500">No dated sessions found.</p>
        ) : (
          <>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={byDateChartData}
                  margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    tickFormatter={(v) => formatSecondsShort(v)}
                  />
                  <Tooltip
                    formatter={(value, _name, props) => [
                      `${formatSecondsShort(value)} · ${props.payload.sessions} sessions · ${props.payload.users} users`,
                      props.payload.date,
                    ]}
                  />
                  <Bar dataKey="seconds" fill="#4285F4" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <CollapsibleTable label="Show date table">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="py-2 pr-4 font-medium">Date</th>
                    <th className="py-2 pr-4 font-medium">Duration</th>
                    <th className="py-2 pr-4 font-medium">Sessions</th>
                    <th className="py-2 pr-4 font-medium">Users</th>
                    <th className="py-2 font-medium">Files</th>
                  </tr>
                </thead>
                <tbody>
                  {[...byDateChartData].reverse().map((d) => (
                    <tr key={d.date} className="border-b border-gray-100">
                      <td className="py-2 pr-4 text-gray-900 font-mono text-xs">{d.date}</td>
                      <td className="py-2 pr-4 text-gray-700">{d.human}</td>
                      <td className="py-2 pr-4 text-gray-500">{d.sessions}</td>
                      <td className="py-2 pr-4 text-gray-500">{d.users}</td>
                      <td className="py-2 text-gray-500">{d.files}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CollapsibleTable>
          </>
        )}
      </div>

      <div className="mb-2 mt-2">
        <h2 className="text-xl font-semibold text-gray-900">Indoor / Outdoor</h2>
        <p className="text-sm text-gray-500">
          Separate GPS environment model from{' '}
          <span className="font-mono text-xs">gps_session_*</span>
          {!hasGps ? ' — none processed yet (run Process staging)' : null}
        </p>
      </div>

      {hasGps ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <SummaryCard icon={Users} label="GPS labelers" value={gpsTotals.users ?? 0} />
            <SummaryCard icon={FolderOpen} label="GPS sessions" value={gpsTotals.sessions ?? 0} />
            <SummaryCard icon={Dog} label="GPS files" value={gpsTotals.files ?? 0} />
            <SummaryCard
              icon={Clock}
              label="GPS labeled duration"
              value={gpsTotals.duration_human || formatSecondsShort(gpsTotals.duration_seconds)}
            />
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-5 mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-1">Duration by environment</h3>
            <p className="text-sm text-gray-500 mb-4">
              Indoor / outdoor labels from{' '}
              <span className="font-mono text-xs">gps_session_*_durations.txt</span>
            </p>
            {gpsChartData.length === 0 ? (
              <p className="text-sm text-gray-500">No non-zero GPS durations found.</p>
            ) : (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={gpsChartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => formatSecondsShort(v)} />
                    <Tooltip
                      formatter={(value, _name, props) => [
                        `${formatSecondsShort(value)} (${Number(value).toFixed(1)}s)`,
                        props.payload.label,
                      ]}
                    />
                    <Bar dataKey="seconds" radius={[4, 4, 0, 0]}>
                      {gpsChartData.map((entry, index) => (
                        <Cell key={entry.label} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
            {gpsActivities.length > 0 ? (
              <CollapsibleTable label="Show environment table">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 border-b">
                      <th className="py-2 pr-4 font-medium">Environment</th>
                      <th className="py-2 pr-4 font-medium">Duration</th>
                      <th className="py-2 font-medium">Seconds</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gpsActivities.map((a) => (
                      <tr key={a.label} className="border-b border-gray-100">
                        <td className="py-2 pr-4 text-gray-900">{displayLabel(a.label)}</td>
                        <td className="py-2 pr-4 text-gray-700">{a.human}</td>
                        <td className="py-2 text-gray-500">{a.seconds.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CollapsibleTable>
            ) : null}
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-5 mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-1">
              GPS contribution by labeler
            </h3>
            {gpsUserContributionData.length === 0 ? (
              <p className="text-sm text-gray-500">No GPS labelers yet.</p>
            ) : (
              <div style={{ height: gpsUserChartHeight }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={gpsUserContributionData}
                    layout="vertical"
                    margin={{ top: 8, right: 24, left: 8, bottom: 8 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 12 }}
                      tickFormatter={(v) => formatSecondsShort(v)}
                    />
                    <YAxis type="category" dataKey="label" width={120} tick={{ fontSize: 12 }} />
                    <Tooltip
                      formatter={(value, _name, props) => [
                        `${formatSecondsShort(value)} · ${props.payload.sessions} sessions`,
                        props.payload.email,
                      ]}
                    />
                    <Bar dataKey="seconds" radius={[0, 4, 4, 0]}>
                      {gpsUserContributionData.map((entry, index) => (
                        <Cell key={entry.email} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-5 mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-1">GPS volume by date</h3>
            {gpsByDateChartData.length === 0 ? (
              <p className="text-sm text-gray-500">No dated GPS sessions found.</p>
            ) : (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={gpsByDateChartData}
                    margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => formatSecondsShort(v)} />
                    <Tooltip
                      formatter={(value, _name, props) => [
                        `${formatSecondsShort(value)} · ${props.payload.sessions} sessions`,
                        props.payload.date,
                      ]}
                    />
                    <Bar dataKey="seconds" fill="#34A853" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </>
      ) : null}

      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <h3 className="text-lg font-semibold text-gray-900 mb-1">By user (detail)</h3>
        <p className="text-sm text-gray-500 mb-4">
          Posture model — ranked by contribution; expand for per-activity and collar SN breakdown
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
                {status.staging_by_family
                  ? ` · activity ${status.staging_by_family.activity || 0} · gps ${status.staging_by_family.gps || 0}`
                  : ''}
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
                {status.output_by_family
                  ? ` · activity ${status.output_by_family.activity || 0} · gps ${status.output_by_family.gps || 0}`
                  : ''}
                {(status.output_emails || []).length
                  ? ` (${status.output_emails.join(', ')})`
                  : ' (empty — click Process staging)'}
              </div>
              {status.staging_health ? (
                <div>
                  Health: ~{status.staging_health.unique_files_after_dedupe} unique /{' '}
                  {status.staging_health.raw_extracted_files} raw
                  {status.staging_health.duplicate_ratio
                    ? ` (${status.staging_health.duplicate_ratio}x)`
                    : ''}
                  {status.staging_health.incomplete_sessions
                    ? ` · incomplete ${status.staging_health.incomplete_sessions}`
                    : ''}
                </div>
              ) : null}
              {status.pending_forwards ? (
                <div>
                  Forwards: {status.pending_forwards.pending_count || 0} pending
                  {status.pending_forwards.already_promoted?.length
                    ? ` · ${status.pending_forwards.already_promoted.length} already promoted`
                    : ''}
                  {status.pending_forwards.unresolved?.length
                    ? ` · ${status.pending_forwards.unresolved.length} unresolved`
                    : ''}
                  {status.forward_batches
                    ? ` · ${status.forward_batches} quarantine batch(es)`
                    : ''}
                </div>
              ) : null}
              {processReport ? (
                <div className="text-xs text-gray-500">
                  {processReport.promoted ? (
                    <>
                      Last promote: {processReport.promoted.length} batch(es), skipped{' '}
                      {(processReport.skipped || []).length}, errors{' '}
                      {(processReport.errors || []).length}
                    </>
                  ) : (
                    <>
                      Last process: copied {processReport.copied}, sessions {processReport.sessions},
                      unknown SN {processReport.unknown_sn_sessions}, errors{' '}
                      {(processReport.errors || []).length}
                    </>
                  )}
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
