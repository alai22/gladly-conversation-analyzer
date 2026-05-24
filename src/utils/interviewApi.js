/**
 * Interview API client
 */
import axios from 'axios';

const authHeaders = () => {
  const token = localStorage.getItem('authToken');
  return token ? { 'X-Auth-Token': token } : {};
};

export async function createInterviewSession(config) {
  const res = await axios.post('/api/interviews/sessions', config, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function listInterviewSessions() {
  const res = await axios.get('/api/interviews/sessions', {
    headers: authHeaders(),
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
