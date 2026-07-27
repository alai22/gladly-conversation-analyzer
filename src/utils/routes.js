/**
 * Path-based URL mapping for Halo Insight.
 * Canonical paths map to internal mode (+ optional adminMode for platform admin tools).
 */

/** @typedef {{ mode: string, adminMode?: string | null, redirect?: string }} RouteConfig */

/** Old paths → canonical paths (SPA redirects) */
export const LEGACY_PATH_REDIRECTS = {
  '/tools': '/platform',
  '/engineering': '/hardware',
};

export const PATH_TO_ROUTE = {
  '/research': { mode: 'churn-trends', adminMode: null },
  '/churn': { mode: 'churn-trends', adminMode: null },
  '/churn/ask': { mode: 'survicate', adminMode: null },
  '/survicate': { mode: 'survey-manager', adminMode: null },
  '/gladly': { mode: 'conversation-trends', adminMode: null },
  '/platform': { mode: 'tools', adminMode: null },
  '/platform/survicate-download': { mode: 'api-data-manager', adminMode: null },
  '/platform/gladly-download': { mode: 'tools', adminMode: 'download' },
  '/platform/zoom': { mode: 'zoom', adminMode: null },
  '/platform/analytics': { mode: 'analytics', adminMode: null },
  '/platform/jira': { mode: 'jira-status', adminMode: null },
  '/platform/claude': { mode: 'tools', adminMode: 'claude' },
  '/jira': { mode: 'bug-triage', adminMode: null },
  '/interview': { mode: 'text-interview', adminMode: null },
  '/surveys': { mode: 'halo-surveys', adminMode: null },
  '/hardware': { mode: 'neck-fit-modeler', adminMode: null },
  '/hardware/neck-fit': { mode: 'neck-fit-modeler', adminMode: null },
};

/** @type {Record<string, string>} */
export const MODE_TO_CANONICAL_PATH = {
  'churn-trends': '/churn',
  'survicate': '/churn/ask',
  'survey-manager': '/survicate',
  'text-interview': '/interview',
  'halo-surveys': '/surveys',
  'conversation-trends': '/gladly',
  'tools': '/platform',
  'api-data-manager': '/platform/survicate-download',
  'zoom': '/platform/zoom',
  'analytics': '/platform/analytics',
  'jira-status': '/platform/jira',
  'bug-triage': '/jira',
  'neck-fit-modeler': '/hardware/neck-fit',
};

/** Modes that belong to the Product Research top-level tab */
export const PRODUCT_RESEARCH_MODES = [
  'churn-trends',
  'survicate',
  'survey-manager',
  'text-interview',
  'halo-surveys',
];

/** Modes that belong to the Platform top-level tab */
export const PLATFORM_MODES = [
  'tools',
  'api-data-manager',
  'zoom',
  'analytics',
  'jira-status',
];

/** Paths that have a canonical route (for redirects and path-first logic) */
export const PATH_BASED_PATHS = Object.keys(PATH_TO_ROUTE);

/** Modes that use path-based URLs instead of ?mode= */
export const PATH_BASED_MODES = Object.keys(MODE_TO_CANONICAL_PATH);

export function isInterviewParticipantPath(pathname) {
  return pathname === '/interview/join' || pathname.startsWith('/interview/join/');
}

export function isSurveyParticipantPath(pathname) {
  return /^\/s\/[a-z0-9]+(?:-[a-z0-9]+)*$/.test(pathname);
}

export function getSurveyBuilderId(pathname) {
  const match = pathname.match(/^\/surveys\/([0-9a-f-]{36})$/i);
  return match ? match[1] : null;
}

export function isSurveyBuilderPath(pathname) {
  return getSurveyBuilderId(pathname) !== null;
}

/**
 * Resolve pathname to route config, including legacy redirects.
 * @param {string} pathname
 * @returns {RouteConfig | null}
 */
export function getRouteFromPath(pathname) {
  if (isInterviewParticipantPath(pathname)) {
    return { mode: 'interview-participant', adminMode: null };
  }
  if (isSurveyParticipantPath(pathname)) {
    return { mode: 'survey-participant', adminMode: null };
  }
  if (getSurveyBuilderId(pathname)) {
    return { mode: 'halo-surveys', adminMode: null };
  }
  if (LEGACY_PATH_REDIRECTS[pathname]) {
    return { redirect: LEGACY_PATH_REDIRECTS[pathname] };
  }
  return PATH_TO_ROUTE[pathname] ?? null;
}

/**
 * @param {string} pathname
 * @returns {string | null}
 */
export function getModeFromPath(pathname) {
  const route = getRouteFromPath(pathname);
  if (!route || route.redirect) return null;
  return route.mode ?? null;
}

/**
 * Canonical path for a mode (+ adminMode when relevant).
 * @param {string} mode
 * @param {string | null} [adminMode]
 * @returns {string | null}
 */
export function getPathFromMode(mode, adminMode = null) {
  if (mode === 'tools') {
    if (adminMode === 'download') return '/platform/gladly-download';
    if (adminMode === 'claude') return '/platform/claude';
    return '/platform';
  }
  return MODE_TO_CANONICAL_PATH[mode] ?? null;
}

/**
 * @param {string} mode
 * @returns {boolean}
 */
export function isPathBasedMode(mode) {
  return mode in MODE_TO_CANONICAL_PATH || PLATFORM_MODES.includes(mode);
}

/**
 * @param {string} pathname
 * @returns {boolean}
 */
export function isPathBasedPath(pathname) {
  return pathname in PATH_TO_ROUTE || pathname in LEGACY_PATH_REDIRECTS;
}

/**
 * @param {string} currentMode
 * @returns {boolean}
 */
export function isProductResearchMode(currentMode) {
  return PRODUCT_RESEARCH_MODES.includes(currentMode);
}

/**
 * @param {string} currentMode
 * @param {string | null} [adminMode]
 * @returns {boolean}
 */
export function isPlatformMode(currentMode, adminMode = null) {
  return (
    PLATFORM_MODES.includes(currentMode) ||
    adminMode === 'download' ||
    adminMode === 'claude'
  );
}

/**
 * @param {string} pathname
 * @param {string} currentMode
 * @param {string | null} adminMode
 * @returns {boolean}
 */
export function pathMatchesMode(pathname, currentMode, adminMode = null) {
  if (currentMode === 'halo-surveys') {
    return pathname === '/surveys' || isSurveyBuilderPath(pathname);
  }
  const expected = getPathFromMode(currentMode, adminMode);
  return expected !== null && pathname === expected;
}
