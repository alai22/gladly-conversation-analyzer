/**
 * Path-based URL mapping for Halo Insight.
 * Memorable paths map to internal mode names; other modes stay query-based (?mode=...).
 */

export const PATH_TO_MODE = {
  '/churn': 'churn-trends',
  '/churn/ask': 'survicate',
  '/survicate': 'survey-manager',
  '/gladly': 'conversation-trends',
  '/tools': 'tools',
  '/jira': 'bug-triage',
  '/interview': 'text-interview',
  '/engineering': 'neck-fit-modeler',
};

export const MODE_TO_PATH = {
  'churn-trends': '/churn',
  'survicate': '/churn/ask',
  'survey-manager': '/survicate',
  'conversation-trends': '/gladly',
  'tools': '/tools',
  'bug-triage': '/jira',
  'text-interview': '/interview',
  'neck-fit-modeler': '/engineering',
};

/** Paths that have a canonical mode (for redirects and path-first logic) */
export const PATH_BASED_PATHS = Object.keys(PATH_TO_MODE);

/** Modes that use path-based URLs */
export const PATH_BASED_MODES = Object.keys(MODE_TO_PATH);

export function isInterviewParticipantPath(pathname) {
  return pathname === '/interview/join' || pathname.startsWith('/interview/join/');
}

export function getModeFromPath(pathname) {
  if (isInterviewParticipantPath(pathname)) {
    return 'interview-participant';
  }
  return PATH_TO_MODE[pathname] ?? null;
}

export function getPathFromMode(mode) {
  return MODE_TO_PATH[mode] ?? null;
}

export function isPathBasedMode(mode) {
  return mode in MODE_TO_PATH;
}

export function isPathBasedPath(pathname) {
  return pathname in PATH_TO_MODE;
}
