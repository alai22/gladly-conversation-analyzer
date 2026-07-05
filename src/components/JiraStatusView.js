import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CheckCircle, XCircle, AlertCircle, RefreshCw, ExternalLink, Link2, FolderOpen, User } from 'lucide-react';

function ErrorWithDetails({ error, errorDetails }) {
  if (!error) return null;
  const hasDetails = errorDetails && (errorDetails.status_code != null || errorDetails.response_snippet);
  return (
    <div>
      <p className="text-sm text-red-700">{error}</p>
      {hasDetails && (
        <details className="mt-2">
          <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">Technical details</summary>
          <div className="mt-1 p-2 bg-gray-100 rounded text-xs overflow-auto max-h-48 font-mono whitespace-pre-wrap break-all">
            {errorDetails.status_code != null && <div>HTTP {errorDetails.status_code}</div>}
            {errorDetails.response_snippet && (
              <div className="mt-1 border-t border-gray-200 pt-1">Response: {errorDetails.response_snippet}</div>
            )}
          </div>
        </details>
      )}
    </div>
  );
}

const JiraStatusView = ({ setCurrentMode }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [status, setStatus] = useState({ configured: false, oauth_can_connect: false, oauth_connected: false });
  const [loading, setLoading] = useState(false);
  const [fetchResult, setFetchResult] = useState(null); // { count, issues, error }
  const [fetching, setFetching] = useState(false);
  const [projectsResult, setProjectsResult] = useState(null); // { projects, error } or null
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [myselfResult, setMyselfResult] = useState(null); // { displayName, emailAddress } or { error }
  const [loadingMyself, setLoadingMyself] = useState(false);
  const [oauthMessage, setOauthMessage] = useState(null); // { type: 'success' | 'error', text }

  const fetchStatus = () => {
    setLoading(true);
    fetch('/api/jira/status')
      .then((r) => r.json())
      .then((data) => {
        setStatus({
          configured: data.configured ?? false,
          base_url: data.base_url,
          auth_type: data.auth_type,
          oauth_can_connect: data.oauth_can_connect ?? false,
          oauth_connected: data.oauth_connected ?? false,
        });
      })
      .catch(() => setStatus({ configured: false, oauth_can_connect: false, oauth_connected: false }))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  // Read OAuth callback result from URL
  useEffect(() => {
    const connected = searchParams.get('connected');
    const oauthError = searchParams.get('oauth_error');
    if (connected === '1') {
      setOauthMessage({ type: 'success', text: 'Jira connected successfully. You can fetch issues below.' });
      setSearchParams({ mode: 'jira-status' }, { replace: true });
      fetchStatus();
    } else if (oauthError) {
      const messages = {
        missing_code: 'Authorization was cancelled or no code returned.',
        invalid_state: 'Invalid state; please try connecting again.',
        no_callback: 'APP_BASE_URL not set. Set it in .env for OAuth callback.',
        exchange_failed: 'Could not exchange code for tokens. Check client ID/secret and callback URL.',
      };
      setOauthMessage({ type: 'error', text: messages[oauthError] || oauthError });
      setSearchParams({ mode: 'jira-status' }, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const handleListProjects = () => {
    setLoadingProjects(true);
    setProjectsResult(null);
    fetch('/api/jira/projects')
      .then((res) => res.json().then((data) => ({ status: res.status, data })))
      .then(({ status: code, data }) => {
        if (code !== 200 || data.status !== 'success') {
          setProjectsResult({
            error: data.message || 'Failed to fetch projects',
            error_details: data.error_details || null,
          });
          return;
        }
        const list = Array.isArray(data.data) ? data.data : [];
        setProjectsResult({ projects: list });
      })
      .catch((err) => setProjectsResult({ error: err.message || 'Request failed' }))
      .finally(() => setLoadingProjects(false));
  };

  const handleWhoAmI = () => {
    setLoadingMyself(true);
    setMyselfResult(null);
    fetch('/api/jira/myself')
      .then((res) => res.json().then((data) => ({ status: res.status, data })))
      .then(({ status: code, data }) => {
        if (code !== 200 || data.status !== 'success') {
          setMyselfResult({
            error: data.message || 'Failed to get current user',
            error_details: data.error_details || null,
          });
          return;
        }
        setMyselfResult(data.data || {});
      })
      .catch((err) => setMyselfResult({ error: err.message || 'Request failed' }))
      .finally(() => setLoadingMyself(false));
  };

  const handleFetch = () => {
    setFetching(true);
    setFetchResult(null);
    fetch('/api/jira/issues?project=HALO&max_results=1000')
      .then((res) => res.json().then((data) => ({ status: res.status, data })))
      .then(({ status: code, data }) => {
        if (code !== 200 || data.status !== 'success') {
          setFetchResult({
            error: data.message || 'Failed to fetch issues',
            error_details: data.error_details || null,
          });
          return;
        }
        const list = Array.isArray(data.data) ? data.data : [];
        setFetchResult({
          count: list.length,
          issues: list.slice(0, 20).map((i) => ({
            key: i.key,
            title: i.title,
            components: i.components?.length ? i.components : (i.component ? [i.component] : []),
          })),
        });
      })
      .catch((err) => setFetchResult({ error: err.message || 'Request failed' }))
      .finally(() => setFetching(false));
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Jira connection</h1>
          <p className="text-gray-600 mt-1">Check if Jira issues can be fetched for Bug Triage (HALO)</p>
        </div>
        <button
          type="button"
          onClick={() => setCurrentMode('tools')}
          className="text-sm text-gray-600 hover:text-gray-900"
        >
          Back to Platform
        </button>
      </div>

      {oauthMessage && (
        <div className={`mb-4 p-3 rounded-lg ${oauthMessage.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
          {oauthMessage.type === 'success' ? <CheckCircle className="h-4 w-4 inline mr-2" /> : <XCircle className="h-4 w-4 inline mr-2" />}
          <span className="text-sm">{oauthMessage.text}</span>
        </div>
      )}

      {/* Config status */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-2">Configuration</h2>
        {loading ? (
          <p className="text-sm text-gray-500">Checking…</p>
        ) : status.configured ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-green-700">
              <CheckCircle className="h-5 w-5 shrink-0" />
              <div>
                <p className="text-sm font-medium">Jira is connected {status.auth_type === 'oauth' ? '(OAuth)' : '(Basic auth)'}</p>
                {status.base_url && (
                  <p className="text-xs text-gray-500 mt-0.5">Base URL: {status.base_url}</p>
                )}
              </div>
            </div>
            {status.oauth_connected && (
              <button
                type="button"
                onClick={() => {
                  fetch('/api/jira/oauth/disconnect', { method: 'POST' })
                    .then(() => fetchStatus());
                }}
                className="text-xs text-gray-500 hover:text-red-600"
              >
                Disconnect OAuth
              </button>
            )}
          </div>
        ) : status.oauth_can_connect ? (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">Connect with OAuth (use the client ID and secret from IT).</p>
            <a
              href="/api/jira/oauth/authorize"
              className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
            >
              <Link2 className="h-4 w-4" />
              Connect to Jira
            </a>
          </div>
        ) : (
          <div className="flex items-start gap-2 text-amber-700">
            <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium">Jira is not configured</p>
              <p className="text-xs text-gray-600 mt-1">
                Either set JIRA_CLIENT_ID, JIRA_CLIENT_SECRET, and APP_BASE_URL for OAuth, or set JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN for Basic auth. API token at{' '}
                <a
                  href="https://id.atlassian.com/manage-profile/security/api-tokens"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline inline-flex items-center gap-0.5"
                >
                  id.atlassian.com <ExternalLink className="h-3 w-3" />
                </a>
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Who am I */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
          <User className="h-4 w-4" />
          Current user
        </h2>
        <p className="text-sm text-gray-600 mb-3">
          Verify which Jira user this API is using (same permissions as that user).
        </p>
        <button
          type="button"
          onClick={handleWhoAmI}
          disabled={!status.configured || loadingMyself}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <User className={`h-4 w-4 ${loadingMyself ? 'animate-pulse' : ''}`} />
          {loadingMyself ? 'Checking…' : 'Who am I?'}
        </button>
        {myselfResult && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            {myselfResult.error ? (
              <ErrorWithDetails error={myselfResult.error} errorDetails={myselfResult.error_details} />
            ) : (
              <p className="text-sm text-gray-700">
                <span className="font-medium">{myselfResult.displayName ?? '—'}</span>
                {myselfResult.emailAddress && (
                  <span className="text-gray-500 ml-2">({myselfResult.emailAddress})</span>
                )}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Projects accessible to API */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
          <FolderOpen className="h-4 w-4" />
          Projects accessible to this API
        </h2>
        <p className="text-sm text-gray-600 mb-3">
          List projects the current user can see. Use the <strong>key</strong> (e.g. HALO) when fetching issues.
        </p>
        <button
          type="button"
          onClick={handleListProjects}
          disabled={!status.configured || loadingProjects}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <FolderOpen className={`h-4 w-4 ${loadingProjects ? 'animate-pulse' : ''}`} />
          {loadingProjects ? 'Loading…' : 'List projects'}
        </button>
        {projectsResult && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            {projectsResult.error ? (
              <ErrorWithDetails error={projectsResult.error} errorDetails={projectsResult.error_details} />
            ) : projectsResult.projects && projectsResult.projects.length > 0 ? (
              <div className="text-sm">
                <p className="font-medium text-gray-700 mb-2">
                  {projectsResult.projects.length} project(s): key → name
                </p>
                <ul className="list-disc list-inside space-y-1 text-gray-600">
                  {projectsResult.projects.map((p) => (
                    <li key={p.id || p.key}>
                      <span className="font-mono font-medium text-gray-800">{p.key}</span>
                      {' → '}
                      {p.name}
                    </li>
                  ))}
                </ul>
                <p className="text-xs text-gray-500 mt-2">
                  Bug Triage uses project key <strong>HALO</strong>. If you don’t see HALO here, use one of the keys above in your app config or ask an admin for access.
                </p>
              </div>
            ) : (
              <p className="text-sm text-amber-700">No projects returned (user may have no project access).</p>
            )}
          </div>
        )}
      </div>

      {/* Fetch test */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-2">Test fetch</h2>
        <p className="text-sm text-gray-600 mb-3">
          Fetch up to 500 issues from project HALO to verify the connection.
        </p>
        <button
          type="button"
          onClick={handleFetch}
          disabled={!status.configured || fetching}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`h-4 w-4 ${fetching ? 'animate-spin' : ''}`} />
          {fetching ? 'Fetching…' : 'Fetch issues'}
        </button>

        {fetchResult && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            {fetchResult.error ? (
              <div className="flex items-start gap-2 text-red-700">
                <XCircle className="h-5 w-5 shrink-0 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <ErrorWithDetails error={fetchResult.error} errorDetails={fetchResult.error_details} />
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2 text-green-700 mb-2">
                  <CheckCircle className="h-5 w-5 shrink-0" />
                  <p className="text-sm font-medium">{fetchResult.count} issues fetched</p>
                </div>
                {fetchResult.issues && fetchResult.issues.length > 0 && (
                  <div className="text-xs text-gray-600">
                    <p className="font-medium text-gray-700 mb-1">Sample (first {fetchResult.issues.length}):</p>
                    <ul className="list-disc list-inside space-y-0.5">
                      {fetchResult.issues.map((i) => (
                        <li key={i.key}>
                          <span className="font-mono">{i.key}</span>
                          {(i.components?.length ? i.components : []).length > 0 && (
                            <span className="text-gray-500 ml-1">
                              [{i.components.join(', ')}]
                            </span>
                          )}
                          {i.title && ` — ${i.title.length > 50 ? i.title.slice(0, 50) + '…' : i.title}`}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Auth options */}
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-2">Auth options</h2>
        <p className="text-sm text-gray-600">
          <strong>OAuth 2.0:</strong> Use “Connect to Jira” above (requires JIRA_CLIENT_ID, JIRA_CLIENT_SECRET, APP_BASE_URL, and the callback URL added in Atlassian). One-time browser authorization, then the app uses stored tokens.
          {' '}<strong>Basic auth:</strong> Set JIRA_EMAIL and JIRA_API_TOKEN in .env (create token at id.atlassian.com). No browser step.
        </p>
      </div>
    </div>
  );
};

export default JiraStatusView;
