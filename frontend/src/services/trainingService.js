import { apiRequest } from "./apiClient";

export function getTraining(modelId) {
  return apiRequest(`/models/${modelId}/training/`);
}

export function startTraining(modelId) {
  return apiRequest(`/models/${modelId}/training/`, { method: "POST" });
}

export function getMetrics(modelId) {
  return apiRequest(`/models/${modelId}/metrics/`);
}
