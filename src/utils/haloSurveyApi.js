/**
 * Halo Survey API client
 */
import axios from 'axios';

const authHeaders = () => {
  const token = localStorage.getItem('authToken');
  return token ? { 'X-Auth-Token': token } : {};
};

// --- Admin ---

export async function listSurveys() {
  const res = await axios.get('/api/surveys', { headers: authHeaders() });
  return res.data;
}

export async function createSurvey(payload) {
  const res = await axios.post('/api/surveys', payload, { headers: authHeaders() });
  return res.data;
}

export async function getSurvey(surveyId) {
  const res = await axios.get(`/api/surveys/${surveyId}`, { headers: authHeaders() });
  return res.data;
}

export async function updateSurvey(surveyId, payload) {
  const res = await axios.patch(`/api/surveys/${surveyId}`, payload, { headers: authHeaders() });
  return res.data;
}

export async function deleteSurvey(surveyId) {
  const res = await axios.delete(`/api/surveys/${surveyId}`, { headers: authHeaders() });
  return res.data;
}

export async function publishSurvey(surveyId) {
  const res = await axios.post(`/api/surveys/${surveyId}/publish`, {}, { headers: authHeaders() });
  return res.data;
}

export async function archiveSurvey(surveyId) {
  const res = await axios.post(`/api/surveys/${surveyId}/archive`, {}, { headers: authHeaders() });
  return res.data;
}

export async function designerChat(surveyId, message) {
  const res = await axios.post(
    `/api/surveys/${surveyId}/designer/chat`,
    { message },
    { headers: authHeaders() }
  );
  return res.data;
}

export async function listSurveyResponses(surveyId) {
  const res = await axios.get(`/api/surveys/${surveyId}/responses`, { headers: authHeaders() });
  return res.data;
}

export async function getSurveyStats(surveyId) {
  const res = await axios.get(`/api/surveys/${surveyId}/stats`, { headers: authHeaders() });
  return res.data;
}

export async function analyzeSurvey(surveyId, payload = {}) {
  const res = await axios.post(`/api/surveys/${surveyId}/analyze`, payload, {
    headers: authHeaders(),
  });
  return res.data;
}

export async function exportSurveyResponses(surveyId) {
  const res = await axios.get(`/api/surveys/${surveyId}/responses/export`, {
    headers: authHeaders(),
    responseType: 'blob',
  });
  return res.data;
}

export function surveyPublicUrl(slug) {
  return `${window.location.origin}/s/${slug}`;
}

// --- Public respondent ---

export async function fetchPublicSurvey(slug) {
  const res = await axios.get(`/api/s/${slug}`);
  return res.data;
}

export async function startSurveyResponse(slug, metadata = {}) {
  const res = await axios.post(`/api/s/${slug}/responses`, {
    action: 'start',
    metadata,
  });
  return res.data;
}

export async function saveSurveyAnswers(slug, responseId, answers, submit = false) {
  const res = await axios.post(`/api/s/${slug}/responses`, {
    response_id: responseId,
    answers,
    submit,
  });
  return res.data;
}

export async function patchSurveyResponse(slug, responseId, answers, submit = false) {
  const res = await axios.patch(`/api/s/${slug}/responses/${responseId}`, {
    answers,
    submit,
  });
  return res.data;
}

export function captureBrazeMetadata(searchParams) {
  const meta = {};
  searchParams.forEach((value, key) => {
    meta[key] = value;
  });
  return meta;
}
