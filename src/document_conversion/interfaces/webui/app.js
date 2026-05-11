const state = {
  file: null,
  pollTimer: null,
  selectedPathId: "docx_to_latex",
  styleMapRows: [{ targetKey: "", sourceStyles: "" }],
  profilePayload: null,
};

function byId(id) {
  return document.getElementById(id);
}

function setError(message) {
  const el = byId("form-error");
  if (!message) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.hidden = false;
  el.textContent = message;
}

function setTaskError(message) {
  const el = byId("task-error");
  if (!message) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.hidden = false;
  el.textContent = message;
}

function stopPolling() {
  if (state.pollTimer) {
    window.clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

function currentPathId() {
  return byId("path-select").value;
}

function updateSelectedFile(file) {
  state.file = file;
  byId("selected-file").textContent = file ? `已选择：${file.name}` : "尚未选择文件";
}

function expectedFileSuffix(pathId) {
  return pathId === "latex_to_docx" ? ".zip" : ".docx";
}

function validateSelectedFile(file, pathId) {
  return file && file.name.toLowerCase().endsWith(expectedFileSuffix(pathId));
}

function dropzoneCopy(pathId) {
  if (pathId === "latex_to_docx") {
    return {
      strong: "拖放 LaTeX 工作区 ZIP 到这里",
      hint: "或点击选择 ZIP 文件",
      accept: ".zip,application/zip",
    };
  }
  return {
    strong: "拖放 DOCX 到这里",
    hint: "或点击选择文件",
    accept: ".docx",
  };
}

function fillSelect(selectId, options, selectedId) {
  const select = byId(selectId);
  select.innerHTML = "";
  for (const option of options) {
    const node = document.createElement("option");
    node.value = option.id;
    node.textContent = option.label;
    if (option.id === selectedId) {
      node.selected = true;
    }
    select.appendChild(node);
  }
}

function fillMultiSelect(selectId, options, selectedIds) {
  const select = byId(selectId);
  select.innerHTML = "";
  const chosen = new Set(selectedIds || []);
  for (const option of options) {
    const node = document.createElement("option");
    node.value = option.id;
    node.textContent = option.label;
    node.selected = chosen.has(option.id);
    select.appendChild(node);
  }
}

function selectedValues(selectId) {
  return Array.from(byId(selectId).selectedOptions || []).map((item) => item.value).filter(Boolean);
}

function normalizeSourceStyles(value) {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function setStyleMapRow(index, patch) {
  state.styleMapRows = state.styleMapRows.map((row, rowIndex) =>
    rowIndex === index ? { ...row, ...patch } : row
  );
}

function removeStyleMapRow(index) {
  if (state.styleMapRows.length === 1) {
    state.styleMapRows = [{ targetKey: "", sourceStyles: "" }];
  } else {
    state.styleMapRows = state.styleMapRows.filter((_, rowIndex) => rowIndex !== index);
  }
  renderStyleMapRows();
}

function addStyleMapRow(row = { targetKey: "", sourceStyles: "" }) {
  state.styleMapRows = [...state.styleMapRows, row];
  renderStyleMapRows();
}

function renderStyleMapRows() {
  const container = byId("stylemap-rows");
  container.innerHTML = "";

  state.styleMapRows.forEach((row, index) => {
    const wrapper = document.createElement("div");
    wrapper.className = "stylemap-row";

    const targetField = document.createElement("label");
    targetField.className = "field";
    const targetLabel = document.createElement("span");
    targetLabel.textContent = "目标键";
    const targetInput = document.createElement("input");
    targetInput.type = "text";
    targetInput.value = row.targetKey;
    targetInput.placeholder = "例如 Heading1";
    targetInput.addEventListener("input", (event) => {
      setStyleMapRow(index, { targetKey: event.target.value });
    });
    targetField.append(targetLabel, targetInput);

    const sourceField = document.createElement("label");
    sourceField.className = "field";
    const sourceLabel = document.createElement("span");
    sourceLabel.textContent = "源样式列表";
    const sourceInput = document.createElement("input");
    sourceInput.type = "text";
    sourceInput.value = row.sourceStyles;
    sourceInput.placeholder = "例如 Main Title, Level 1 Heading";
    sourceInput.addEventListener("input", (event) => {
      setStyleMapRow(index, { sourceStyles: event.target.value });
    });
    sourceField.append(sourceLabel, sourceInput);

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "secondary-button stylemap-remove";
    removeButton.textContent = "删除";
    removeButton.addEventListener("click", () => {
      removeStyleMapRow(index);
    });

    wrapper.append(targetField, sourceField, removeButton);
    container.appendChild(wrapper);
  });
}

function serializeStyleMapRows() {
  const payload = {};
  const seenKeys = new Set();

  for (const row of state.styleMapRows) {
    const targetKey = row.targetKey.trim();
    const sources = normalizeSourceStyles(row.sourceStyles);
    const isEmptyRow = !targetKey && sources.length === 0;
    if (isEmptyRow) {
      continue;
    }
    if (!targetKey) {
      throw new Error("StyleMap 的目标键不能为空。");
    }
    if (sources.length === 0) {
      throw new Error(`StyleMap 的目标键 ${targetKey} 至少需要一个源样式。`);
    }
    if (seenKeys.has(targetKey)) {
      throw new Error(`StyleMap 的目标键重复：${targetKey}`);
    }
    seenKeys.add(targetKey);
    payload[targetKey] = sources.length === 1 ? sources[0] : sources;
  }

  return Object.keys(payload).length ? JSON.stringify(payload) : "";
}

function splitTextList(raw) {
  return raw
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function renderTaskState(task) {
  byId("status-card").hidden = false;
  byId("task-id").textContent = task.task_id;
  const stateNode = byId("task-state");
  stateNode.textContent = task.state;
  stateNode.classList.toggle("failed", task.state === "failed");
}

async function pollTask(taskId) {
  try {
    const response = await fetch(`/v2/tasks/${encodeURIComponent(taskId)}`);
    if (!response.ok) {
      throw new Error("任务状态查询失败");
    }
    const task = await response.json();
    renderTaskState(task);
    if (task.state === "done") {
      stopPolling();
      setTaskError("");
      const link = byId("download-link");
      link.href = `/v2/tasks/${encodeURIComponent(taskId)}/result`;
      link.hidden = false;
    } else if (task.state === "failed") {
      stopPolling();
      byId("download-link").hidden = true;
      setTaskError(task.err_msg || "任务执行失败");
    }
  } catch (error) {
    stopPolling();
    setTaskError(error instanceof Error ? error.message : "任务状态查询失败");
  }
}

function applyPathMode() {
  const pathId = currentPathId();
  state.selectedPathId = pathId;
  const copy = dropzoneCopy(pathId);
  byId("dropzone-title").textContent = copy.strong;
  byId("dropzone-hint").textContent = copy.hint;
  byId("file-input").setAttribute("accept", copy.accept);
  byId("docx-controls").hidden = pathId !== "docx_to_latex";
  byId("pandoc-controls").hidden = pathId !== "latex_to_docx";
  updateSelectedFile(null);
  setError("");
}

async function loadPresets() {
  const response = await fetch("/v1/profiles");
  if (!response.ok) {
    throw new Error("无法读取 WebUI 预设配置");
  }
  const payload = await response.json();
  state.profilePayload = payload;

  fillSelect("path-select", [
    { id: "docx_to_latex", label: "DOCX → LaTeX" },
    { id: "latex_to_docx", label: "LaTeX → DOCX" },
  ], payload.defaults.source_format === "latex" ? "latex_to_docx" : "docx_to_latex");

  fillSelect(
    "docx-profile",
    (payload.profiles_by_path.docx_to_latex || []).filter((item) => item.engine_id === "docx2tex"),
    payload.defaults.by_path.docx_to_latex.profile_id
  );
  fillSelect("custom-xsl-preset", payload.path_options.docx_to_latex.custom_xsl, payload.defaults.by_path.docx_to_latex.custom_xsl_preset);
  fillSelect("table-model", payload.path_options.docx_to_latex.table_model, payload.defaults.by_path.docx_to_latex.table_model);
  fillSelect("math-type-source", payload.path_options.docx_to_latex.math_type_source, payload.defaults.by_path.docx_to_latex.math_type_source);

  const pandocDefaults = payload.path_options.latex_to_docx.defaults_by_profile[payload.defaults.by_path.latex_to_docx.profile_id];
  fillSelect(
    "pandoc-profile",
    (payload.profiles_by_path.latex_to_docx || []).filter((item) => item.engine_id === "pandoc"),
    payload.defaults.by_path.latex_to_docx.profile_id
  );
  fillSelect("reference-doc-id", payload.path_options.latex_to_docx.reference_docs, pandocDefaults.reference_doc_id);
  fillSelect("numbering-metadata-id", payload.path_options.latex_to_docx.numbering_metadata, pandocDefaults.numbering_metadata_id);
  fillMultiSelect("lua-filter-ids", payload.path_options.latex_to_docx.lua_filters, pandocDefaults.lua_filter_ids);
  fillMultiSelect("exec-filter-ids", payload.path_options.latex_to_docx.exec_filters, pandocDefaults.exec_filter_ids);
  fillSelect("top-level-division", payload.path_options.latex_to_docx.top_level_division, pandocDefaults.top_level_division);
  fillSelect("csl-id", [{ id: "", label: "Pandoc 默认样式" }, ...payload.path_options.latex_to_docx.csl], pandocDefaults.csl_id);
  byId("citeproc-toggle").checked = Boolean(pandocDefaults.citeproc);
  byId("debug-toggle").checked = Boolean(payload.defaults.by_path.docx_to_latex.debug);

  applyPathMode();
}

function applyPandocProfileDefaults() {
  if (!state.profilePayload) {
    return;
  }
  const profileId = byId("pandoc-profile").value;
  const defaults = state.profilePayload.path_options.latex_to_docx.defaults_by_profile[profileId];
  if (!defaults) {
    return;
  }
  fillSelect("reference-doc-id", state.profilePayload.path_options.latex_to_docx.reference_docs, defaults.reference_doc_id);
  fillSelect("numbering-metadata-id", state.profilePayload.path_options.latex_to_docx.numbering_metadata, defaults.numbering_metadata_id);
  fillMultiSelect("lua-filter-ids", state.profilePayload.path_options.latex_to_docx.lua_filters, defaults.lua_filter_ids);
  fillMultiSelect("exec-filter-ids", state.profilePayload.path_options.latex_to_docx.exec_filters, defaults.exec_filter_ids);
  fillSelect("top-level-division", state.profilePayload.path_options.latex_to_docx.top_level_division, defaults.top_level_division);
  fillSelect("csl-id", [{ id: "", label: "Pandoc 默认样式" }, ...state.profilePayload.path_options.latex_to_docx.csl], defaults.csl_id);
  byId("citeproc-toggle").checked = Boolean(defaults.citeproc);
}

async function submitForm(event) {
  event.preventDefault();
  setError("");
  setTaskError("");
  byId("download-link").hidden = true;

  const pathId = currentPathId();
  if (!validateSelectedFile(state.file, pathId)) {
    setError(`请先选择一个 ${expectedFileSuffix(pathId)} 文件。`);
    return;
  }

  const formData = new FormData();
  formData.append("file", state.file);
  formData.append("debug", String(byId("debug-toggle").checked));

  if (pathId === "docx_to_latex") {
    formData.append("source_format", "docx");
    formData.append("target_format", "latex");
    formData.append("profile_id", byId("docx-profile").value);
    formData.append("custom_xsl_preset", byId("custom-xsl-preset").value);
    formData.append("TableModel", byId("table-model").value);
    formData.append("MathTypeSource", byId("math-type-source").value);
    const styleMap = serializeStyleMapRows();
    if (styleMap) {
      formData.append("StyleMap", styleMap);
    }
  } else {
    formData.append("source_format", "latex");
    formData.append("target_format", "docx");
    formData.append("profile_id", byId("pandoc-profile").value);
    const mainTex = byId("main-tex").value.trim();
    if (mainTex) {
      formData.append("main_tex", mainTex);
    }
    formData.append("reference_doc_id", byId("reference-doc-id").value);
    formData.append("numbering_metadata_id", byId("numbering-metadata-id").value);
    formData.append("lua_filter_ids", JSON.stringify(selectedValues("lua-filter-ids")));
    formData.append("exec_filter_ids", JSON.stringify(selectedValues("exec-filter-ids")));
    formData.append("top_level_division", byId("top-level-division").value);
    formData.append("citeproc", String(byId("citeproc-toggle").checked));
    const cslId = byId("csl-id").value;
    if (cslId) {
      formData.append("csl_id", cslId);
    }
    const bibliographyPaths = splitTextList(byId("bibliography-paths").value);
    if (bibliographyPaths.length) {
      formData.append("bibliography_paths", JSON.stringify(bibliographyPaths));
    }
  }

  const submitButton = byId("submit-button");
  submitButton.disabled = true;

  try {
    const response = await fetch("/v2/tasks", {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      let detail = "提交失败";
      try {
        const payload = await response.json();
        detail = payload.detail || detail;
      } catch (_ignored) {
        // ignore
      }
      throw new Error(detail);
    }
    const payload = await response.json();
    renderTaskState({ task_id: payload.task_id, state: "pending" });
    stopPolling();
    state.pollTimer = window.setInterval(() => {
      void pollTask(payload.task_id);
    }, 2000);
    void pollTask(payload.task_id);
  } catch (error) {
    setError(error instanceof Error ? error.message : "提交失败");
  } finally {
    submitButton.disabled = false;
  }
}

function setupDropzone() {
  const dropzone = byId("dropzone");
  const fileInput = byId("file-input");

  const assignFile = (file) => {
    if (!validateSelectedFile(file, currentPathId())) {
      updateSelectedFile(null);
      setError(`仅支持上传 ${expectedFileSuffix(currentPathId())} 文件。`);
      return;
    }
    setError("");
    updateSelectedFile(file);
  };

  dropzone.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInput.click();
    }
  });
  fileInput.addEventListener("change", () => {
    const [file] = fileInput.files || [];
    assignFile(file || null);
  });
  ["dragenter", "dragover"].forEach((name) => {
    dropzone.addEventListener(name, (event) => {
      event.preventDefault();
      dropzone.classList.add("dragover");
    });
  });
  ["dragleave", "drop"].forEach((name) => {
    dropzone.addEventListener(name, (event) => {
      event.preventDefault();
      dropzone.classList.remove("dragover");
    });
  });
  dropzone.addEventListener("drop", (event) => {
    const [file] = event.dataTransfer?.files || [];
    assignFile(file || null);
  });
}

async function init() {
  renderStyleMapRows();
  setupDropzone();
  byId("add-stylemap-row").addEventListener("click", () => addStyleMapRow());
  byId("path-select").addEventListener("change", applyPathMode);
  byId("pandoc-profile").addEventListener("change", applyPandocProfileDefaults);
  byId("upload-form").addEventListener("submit", (event) => {
    void submitForm(event);
  });
  try {
    await loadPresets();
  } catch (error) {
    setError(error instanceof Error ? error.message : "无法初始化表单");
  }
}

window.addEventListener("DOMContentLoaded", () => {
  void init();
});
