import { apiRequest } from "./apiClient";

export function getDataset(modelId) {
  return apiRequest(`/models/${modelId}/dataset/`);
}

export function uploadDataset(modelId, file, expandExisting = false) {
  const body = new FormData();
  body.append("file", file);
  body.append("expand_existing", expandExisting ? "true" : "false");
  return apiRequest(`/models/${modelId}/dataset/`, {
    method: "POST",
    body,
  });
}

export function selectTargetColumn(modelId, targetColumn, taskType = "auto") {
  return apiRequest(`/models/${modelId}/dataset/target/`, {
    method: "POST",
    body: { target_column: targetColumn, task_type: taskType },
  });
}
