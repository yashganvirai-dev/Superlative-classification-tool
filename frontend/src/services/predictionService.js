import { apiRequest } from "./apiClient";

export function getPredictionSchema(modelId) {
  return apiRequest(`/models/${modelId}/prediction/schema/`);
}

export function predict(modelId, features) {
  return apiRequest(`/models/${modelId}/prediction/`, {
    method: "POST",
    body: { features },
  });
}
