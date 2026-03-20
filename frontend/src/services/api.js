import axios from 'axios';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
});

// Upload CSV file
export async function uploadDataset(file) {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      const pct = Math.round((progressEvent.loaded * 100) / progressEvent.total);
      window.dispatchEvent(new CustomEvent('upload-progress', { detail: pct }));
    },
  });
  return response.data;
}

// Get dashboard config
export async function getDashboard(datasetId) {
  const response = await api.get(`/dashboard/${datasetId}`);
  return response.data;
}

// Get dataset preview
export async function getDatasetPreview(datasetId) {
  const response = await api.get(`/dataset/${datasetId}/preview`);
  return response.data;
}

// Send chat message
export async function sendChatMessage(datasetId, message, history = []) {
  const response = await api.post('/chat', {
    dataset_id: datasetId,
    message,
    conversation_history: history,
  });
  return response.data;
}

// Get LLM-generated suggestions for a dataset
export async function fetchSuggestions(datasetId) {
  const response = await api.get(`/suggestions/${datasetId}`);
  return response.data.suggestions || [];
}

// Explain a chart
export async function explainChart(datasetId, chartConfig) {
  const response = await api.post(`/dashboard/${datasetId}/explain-chart`, chartConfig);
  return response.data;
}

// Export PDF
export function getExportPdfUrl(datasetId) {
  return `${API_BASE}/export/${datasetId}/pdf`;
}

// Export PPTX
export function getExportPptxUrl(datasetId) {
  return `${API_BASE}/export/${datasetId}/pptx`;
}

// Export chart image
export function getChartImageUrl(datasetId, chartId) {
  return `${API_BASE}/export/${datasetId}/chart/${chartId}`;
}

export default api;
