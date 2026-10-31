import { apiRequest } from "./apiClient";

export function listModels() {
  return apiRequest("/models/");
}

export function createModel(model) {
  return apiRequest("/models/", {
    method: "POST",
    body: model,
  });
}

export function createAutomaticModel({ file, name = "", description = "", algorithm = "AUTO" }) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("name", name);
  formData.append("description", description);
  formData.append("algorithm", algorithm);
  return apiRequest("/models/automatic/", {
    method: "POST",
    body: formData,
  });
}

export function getModel(modelId) {
  return apiRequest(`/models/${modelId}/`);
}

export function deleteModel(modelId) {
  return apiRequest(`/models/${modelId}/`, { method: "DELETE" });
}
