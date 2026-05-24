/**
 * Interview API client
 */
import axios from 'axios';

const authHeaders = () => {
  const token = localStorage.getItem('authToken');
  return token ? { 'X-Auth-Token': token } : {};
};

// --- Research projects ---

export async function createInterviewProject(payload) {
  const res = await axios.post('/api/interviews/projects', payload, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function listInterviewProjects() {
  const res = await axios.get('/api/interviews/projects', {
    headers: authHeaders(),
  });
  return res.data;
}

export async function getInterviewProject(projectId) {
  const res = await axios.get(`/api/interviews/projects/${projectId}`, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function updateInterviewProject(projectId, payload) {
  const res = await axios.patch(`/api/interviews/projects/${projectId}`, payload, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function createParticipantSession(projectId, payload = {}) {
  const res = await axios.post(
    `/api/interviews/projects/${projectId}/sessions`,
    payload,
    { headers: authHeaders() }
  );
  return res.data;
}

export async function listProjectSessions(projectId) {
  const res = await axios.get(`/api/interviews/projects/${projectId}/sessions`, {
    headers: authHeaders(),
  });
  return res.data;
}

// --- Sessions (legacy + shared) ---

export async function createInterviewSession(config) {
  const res = await axios.post('/api/interviews/sessions', config, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function listInterviewSessions(projectId) {
  const params = projectId ? { project_id: projectId } : {};
  const res = await axios.get('/api/interviews/sessions', {
    headers: authHeaders(),
    params,
  });
  return res.data;
}

export async function getInterviewSession(sessionId) {
  const res = await axios.get(`/api/interviews/sessions/${sessionId}`, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function endInterviewSession(sessionId) {
  const res = await axios.post(
    `/api/interviews/sessions/${sessionId}/end`,
    {},
    { headers: authHeaders() }
  );
  return res.data;
}

export async function getInterviewInsights(sessionId) {
  const res = await axios.get(`/api/interviews/sessions/${sessionId}/insights`, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function exportInterviewInsights(sessionId) {
  const res = await axios.get(`/api/interviews/sessions/${sessionId}/export`, {
    headers: authHeaders(),
    responseType: 'blob',
  });
  return res.data;
}

// --- Public participant ---

export async function joinInterview(token) {
  const res = await axios.get(`/api/interviews/join/${token}`);
  return res.data;
}

export async function sendParticipantMessage(token, message) {
  const res = await axios.post(`/api/interviews/join/${token}/message`, { message });
  return res.data;
}

export async function endParticipantInterview(token) {
  const res = await axios.post(`/api/interviews/join/${token}/end`, {});
  return res.data;
}

export function fullJoinUrl(path) {
  if (!path) return '';
  if (path.startsWith('http')) return path;
  return `${window.location.origin}${path}`;
}
