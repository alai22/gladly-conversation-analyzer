import React, { useCallback, useEffect, useMemo, useState } from 'react';
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
import { AlertCircle, Clock, Dog, FolderOpen, Play, RefreshCw, Users } from 'lucide-react';
import axios from 'axios';

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

const LabelingDataDashboard = () => {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState(null);
  const [processReport, setProcessReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [cached, setCached] = useState(false);
  const [expandedUser, setExpandedUser] = useState(null);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await axios.get('/api/labeling/status');
      if (response.data.success) {
        setStatus(response.data.data);
        if (response.data.data?.process?.last_report) {
          setProcessReport(response.data.data.process.last_report);
        }
      }
    } catch (err) {
      // Non-fatal; summary can still load
      console.error('Failed to load labeling status', err);
    }
  }, []);

  const fetchSummary = useCallback(async ({ refresh = false } = {}) => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get('/api/labeling/summary', {
        params: refresh ? { refresh: 1 } : undefined,
      });
      if (response.data.success) {
        setData(response.data.data);
        setCached(Boolean(response.data.cached));
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
    setProcessing(true);
    setError(null);
    try {
      const response = await axios.post('/api/labeling/process', {
        dry_run: false,
        clear_output: true,
        async: false,
      });
      if (!response.data.success) {
        throw new Error(response.data.error || 'Process failed');
      }
      setProcessReport(response.data.data);
      await fetchStatus();
      await fetchSummary({ refresh: true });
    } catch (err) {
      const errorMsg =
        err.response?.data?.error ||
        err.response?.data?.message ||
        err.message ||
        'Failed to process staging';
      setError(errorMsg);
    } finally {
      setProcessing(false);
    }
  }, [fetchStatus, fetchSummary]);

  useEffect(() => {
    fetchStatus();
    fetchSummary();
  }, [fetchStatus, fetchSummary]);

  const totals = data?.totals || {};
  const activities = data?.activities || [];
  const users = data?.users || [];

  const chartData = useMemo(
    () =>
      activities.map((a) => ({
        name: a.name,
        label: a.label,
        seconds: a.seconds,
      })),
    [activities]
  );

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
      <div className="flex items-center justify-between mb-6 flex-shrink-0">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Labeling Data</h2>
          <p className="text-sm text-gray-600 mt-1">
            Processed data from{' '}
            <span className="font-mono text-xs">
              s3://{data?.bucket}/{data?.prefix}
            </span>
            {cached ? <span className="ml-2 text-xs text-gray-400">(cached)</span> : null}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={processStaging}
            disabled={processing || loading}
            className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700 disabled:opacity-50"
            title="Copy staging/extracted → extracted-txt/<email>/<collar-sn>/ then refresh summary"
          >
            <Play className={`h-4 w-4 ${processing ? 'animate-pulse' : ''}`} />
            {processing ? 'Processing…' : 'Process staging'}
          </button>
          <button
            type="button"
            onClick={() => {
              fetchStatus();
              fetchSummary({ refresh: true });
            }}
            disabled={loading || processing}
            className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {status ? (
        <div className="mb-4 p-4 bg-white border border-gray-200 rounded-lg text-sm text-gray-700">
          <div className="font-medium text-gray-900 mb-1">Pipeline</div>
          <div>
            Staging: <span className="font-mono">{status.staging_extracted_files ?? 0}</span> extracted
            files in <span className="font-mono">{status.staging_batches ?? 0}</span> Gmail batches
            {status.staging_by_email
              ? ` (${Object.entries(status.staging_by_email)
                  .map(([email, n]) => `${email}: ${n}`)
                  .join(' · ')})`
              : ''}
          </div>
          <div>
            Output: <span className="font-mono">{status.output_files ?? 0}</span> files under{' '}
            <span className="font-mono">{status.output_prefix}</span>
            {(status.output_emails || []).length
              ? ` (${status.output_emails.join(', ')})`
              : ' (empty — click Process staging)'}
          </div>
          {processReport ? (
            <div className="mt-2 text-xs text-gray-500">
              Last process: copied {processReport.copied}, sessions {processReport.sessions},
              unknown SN {processReport.unknown_sn_sessions}, errors{' '}
              {(processReport.errors || []).length}
            </div>
          ) : null}
        </div>
      ) : null}

      {error ? (
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <SummaryCard icon={Users} label="Users" value={totals.users ?? 0} />
        <SummaryCard icon={FolderOpen} label="Sessions" value={totals.sessions ?? 0} />
        <SummaryCard icon={Dog} label="Files" value={totals.files ?? 0} />
        <SummaryCard
          icon={Clock}
          label="Total labeled duration"
          value={totals.duration_human || formatSecondsShort(totals.duration_seconds)}
        />
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
        <h3 className="text-lg font-semibold text-gray-900 mb-1">By user</h3>
        <p className="text-sm text-gray-500 mb-4">
          File counts and summed activity durations per email folder
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
    </div>
  );
};

function SummaryCard({ icon: Icon, label, value }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center gap-2 text-gray-500 text-xs uppercase tracking-wide mb-2">
        <Icon className="h-4 w-4" />
        {label}
      </div>
      <div className="text-2xl font-semibold text-gray-900">{value}</div>
    </div>
  );
}

export default LabelingDataDashboard;
