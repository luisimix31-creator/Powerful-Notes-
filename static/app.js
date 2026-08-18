let OPTIONS = null;
let CLIENTS = [];
let currentNoteType = "session";
let editingClientId = null;
let quickMode = false;

const PARTICIPANT_ROLES = [
  { id: "bcba", label: "BCBA" },
  { id: "bcaba", label: "BCaBA" },
  { id: "rbt", label: "RBT" },
  { id: "caregiver", label: "Caregiver" },
];
const PARTICIPANT_ROLE_LABELS = Object.fromEntries(PARTICIPANT_ROLES.map((r) => [r.id, r.label]));

let participants = [];
let programScenarios = {};
let behaviorInterventions = {};
let behaviorAntecedents = {};
let behaviorTopographies = {};
let newClientBehaviorTopographies = {};

const selections = {
  replacement_programs: new Set(),
  maladaptive_behaviors: new Set(),
  data_collection_methods: new Set(),
  environmental_changes: new Set(),
  medical_concerns: new Set(),
  intervention_effectiveness: null,
  protocol_modifications: new Set(),
  client_engagement: null,
  observation_method: null,
  session_rating: null,
  protocol_fidelity: null,
  rbt_strengths: new Set(),
  rbt_feedback_areas: new Set(),
  training_topics: new Set(),
  teaching_methods: new Set(),
  caregiver_competency: null,
  caregiver_response: new Set(),
  training_barriers: new Set(),
  referral_reason: null,
  assessment_methods: new Set(),
  treatment_intensity: null,
  recommended_services: new Set(),
  progress_rating: null,
  reassessment_recommendations: new Set(),
};

const targetEditSelections = {
  replacement_programs: new Set(),
  maladaptive_behaviors: new Set(),
  antecedents: new Set(),
  intervention_strategies: new Set(),
  training_topics: new Set(),
};

const newClientSelections = {
  replacement_programs: new Set(),
  maladaptive_behaviors: new Set(),
  antecedents: new Set(),
  intervention_strategies: new Set(),
  training_topics: new Set(),
};

const el = (id) => document.getElementById(id);

const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]').content;
const BCBA_NAME = document.querySelector('meta[name="bcba-name"]').content.trim();

function apiFetch(url, options = {}) {
  const headers = { ...(options.headers || {}) };
  const method = (options.method || "GET").toUpperCase();
  if (method !== "GET") {
    headers["X-CSRFToken"] = CSRF_TOKEN;
  }
  return fetch(url, { ...options, headers });
}

async function init() {
  OPTIONS = await fetch("/api/options").then((r) => r.json());
  await refreshClients();

  fillPlaceOfService();
  el("sessionDate").value = new Date().toISOString().slice(0, 10);
  applyProviderDefaults(null);
  renderChipGroup("environmentalChanges", OPTIONS.environmental_changes, "environmental_changes", false, selections, null, null, "environmental_changes");
  renderChipGroup("medicalConcerns", OPTIONS.medical_concerns, "medical_concerns", false, selections, null, null, "medical_concerns");
  renderChipGroup("dataCollectionMethods", OPTIONS.data_collection_methods, "data_collection_methods", false, selections, null, null, "data_collection_methods");
  renderChipGroup("interventionEffectiveness", OPTIONS.intervention_effectiveness, "intervention_effectiveness", true, selections, null, null, "intervention_effectiveness");
  renderChipGroup("protocolModifications", OPTIONS.protocol_modifications, "protocol_modifications", false, selections, null, null, "protocol_modifications");
  renderChipGroup("clientEngagement", OPTIONS.client_engagement, "client_engagement", true, selections, null, null, "client_engagement");
  renderChipGroup("observationMethod", OPTIONS.observation_methods, "observation_method", true, selections, null, null, "observation_methods");
  renderChipGroup("sessionRating", OPTIONS.session_ratings, "session_rating", true, selections, null, null, "session_ratings");
  renderChipGroup("protocolFidelity", OPTIONS.protocol_fidelity, "protocol_fidelity", true, selections, null, null, "protocol_fidelity");
  renderChipGroup("rbtStrengths", OPTIONS.rbt_strengths, "rbt_strengths", false, selections, null, null, "rbt_strengths");
  renderChipGroup("rbtFeedbackAreas", OPTIONS.rbt_feedback_areas, "rbt_feedback_areas", false, selections, null, null, "rbt_feedback_areas");

  renderChipGroup("trainingTopics", OPTIONS.caregiver_training_topics, "training_topics", false, selections, null, null, "caregiver_training_topics");
  renderChipGroup("teachingMethods", OPTIONS.teaching_methods, "teaching_methods", false, selections, null, null, "teaching_methods");
  renderChipGroup("caregiverCompetency", OPTIONS.caregiver_competency, "caregiver_competency", true, selections, null, null, "caregiver_competency");
  renderChipGroup("caregiverResponse", OPTIONS.caregiver_response, "caregiver_response", false, selections, null, null, "caregiver_response");
  renderChipGroup("trainingBarriers", OPTIONS.training_barriers, "training_barriers", false, selections, null, null, "training_barriers");

  renderChipGroup("referralReason", OPTIONS.referral_reasons, "referral_reason", true, selections, null, null, "referral_reasons");
  renderChipGroup("assessmentMethodsInitial", OPTIONS.assessment_methods, "assessment_methods", false, selections, null, null, "assessment_methods");
  renderChipGroup("treatmentIntensity", OPTIONS.treatment_intensity, "treatment_intensity", true, selections, null, null, "treatment_intensity");
  renderChipGroup("recommendedServices", OPTIONS.recommended_services, "recommended_services", false, selections, null, null, "recommended_services");
  renderChipGroup("assessmentMethodsReassessment", OPTIONS.assessment_methods, "assessment_methods", false, selections, null, null, "assessment_methods");
  renderChipGroup("progressRating", OPTIONS.progress_ratings, "progress_rating", true, selections, null, null, "progress_ratings");
  renderChipGroup("reassessmentDataMethods", OPTIONS.data_collection_methods, "data_collection_methods", false, selections, null, null, "data_collection_methods");
  renderChipGroup("reassessmentRecommendations", OPTIONS.reassessment_recommendations, "reassessment_recommendations", false, selections, null, null, "reassessment_recommendations");

  renderChipGroup("ncReplacementPrograms", OPTIONS.replacement_programs, "replacement_programs", false, newClientSelections, null, null, "replacement_programs", true);
  renderChipGroup("ncMaladaptiveBehaviors", OPTIONS.maladaptive_behaviors, "maladaptive_behaviors", false, newClientSelections, null, null, "maladaptive_behaviors", true);
  renderChipGroup("ncAntecedents", OPTIONS.antecedents, "antecedents", false, newClientSelections, null, null, "antecedents", true);
  renderChipGroup("ncInterventionStrategies", OPTIONS.intervention_strategies, "intervention_strategies", false, newClientSelections, null, null, "intervention_strategies", true);
  renderChipGroup("ncTrainingTopics", OPTIONS.caregiver_training_topics, "training_topics", false, newClientSelections, null, null, "caregiver_training_topics", true);

  bindStaticEvents();
  setupDropZone("dropInitialAssessment", "fileInitialAssessment", "initial_assessment");
  setupDropZone("dropReassessment", "fileReassessment", "reassessment");
}

function fillPlaceOfService() {
  const sel = el("placeOfService");
  sel.innerHTML = "";
  OPTIONS.place_of_service.forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p;
    opt.textContent = p;
    sel.appendChild(opt);
  });
  const otherOpt = document.createElement("option");
  otherOpt.value = "__other__";
  otherOpt.textContent = "Other (specify)...";
  sel.appendChild(otherOpt);

  sel.addEventListener("change", () => {
    el("placeOfServiceCustom").hidden = sel.value !== "__other__";
  });
}

function renderChipGroup(containerId, items, key, singleSelect, store, preselected, onChange, customCategory, enablePasteList) {
  const container = el(containerId);
  container.innerHTML = "";
  items.forEach((item) => {
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.textContent = item.label;
    chip.dataset.id = item.id;

    const isPreselected = singleSelect ? preselected === item.id : (preselected && preselected.has(item.id));
    if (isPreselected) {
      chip.classList.add("selected");
      if (singleSelect) store[key] = item.id;
      else store[key].add(item.id);
    }

    chip.addEventListener("click", () => {
      if (singleSelect) {
        store[key] = store[key] === item.id ? null : item.id;
        [...container.children].forEach((c) => c.classList.toggle("selected", c.dataset.id === store[key]));
      } else {
        if (store[key].has(item.id)) {
          store[key].delete(item.id);
          chip.classList.remove("selected");
        } else {
          store[key].add(item.id);
          chip.classList.add("selected");
        }
      }
      if (onChange) onChange();
    });

    if (customCategory && item.id.startsWith("custom_")) {
      chip.title = "Right-click to delete";
      chip.addEventListener("contextmenu", async (e) => {
        e.preventDefault();
        if (!confirm(`Delete "${item.label}"? This removes it from your options permanently.`)) return;

        const res = await apiFetch("/api/options/custom", {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ category: customCategory, id: item.id }),
        });
        if (!res.ok) {
          const err = await res.json();
          alert(err.error || "Failed to delete option.");
          return;
        }

        OPTIONS[customCategory] = OPTIONS[customCategory].filter((i) => i.id !== item.id);
        if (singleSelect) {
          if (store[key] === item.id) store[key] = null;
        } else if (store[key]) {
          store[key].delete(item.id);
        }
        renderChipGroup(containerId, OPTIONS[customCategory], key, singleSelect, store, store[key], onChange, customCategory);
        if (onChange) onChange();
      });
    }

    container.appendChild(chip);
  });

  if (customCategory) {
    ensureCustomAddRow(containerId, customCategory, key, singleSelect, store, onChange);
  }
  if (enablePasteList) {
    ensurePasteListRow(containerId, customCategory, key, singleSelect, store, onChange);
  }
}

// Matches pasted/free-typed text against an existing catalog item: exact label match,
// then match against the label's core text (before any parenthetical or slash), then
// substring match in either direction. Returns the matched item or null.
function matchCatalogItem(text, items) {
  const norm = (s) => s.toLowerCase().trim();
  const target = norm(text);
  if (!target) return null;

  let found = items.find((i) => norm(i.label) === target);
  if (found) return found;

  found = items.find((i) => norm(i.label).split(/[(/]/)[0].trim() === target);
  if (found) return found;

  found = items.find((i) => {
    const label = norm(i.label);
    return label.includes(target) || target.includes(label);
  });
  return found || null;
}

// Auto-injects a "Paste a list" toggle immediately after a chip-grid's custom-add row.
// Splits pasted text by line (stripping bullet/number prefixes), matches each line
// against the existing catalog, selects matches, and creates the rest as new custom
// options — so a BCBA can paste a treatment plan's behavior/program list in one shot
// instead of clicking each chip individually.
function ensurePasteListRow(containerId, category, key, singleSelect, store, onChange) {
  const rowId = `${containerId}PasteRow`;
  if (el(rowId)) return;

  const anchor = el(`${containerId}CustomRow`) || el(containerId);
  const row = document.createElement("div");
  row.id = rowId;
  row.className = "paste-list-row";

  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "btn secondary small";
  toggle.textContent = "Paste a list...";

  const box = document.createElement("div");
  box.className = "paste-list-box";
  box.hidden = true;

  const textarea = document.createElement("textarea");
  textarea.rows = 4;
  textarea.placeholder = "Paste a list, one per line (from a treatment plan, EMR, etc.)...";

  const addBtn = document.createElement("button");
  addBtn.type = "button";
  addBtn.className = "btn secondary small";
  addBtn.textContent = "Add Pasted List";

  const status = document.createElement("div");
  status.className = "hint";

  toggle.addEventListener("click", () => {
    box.hidden = !box.hidden;
    if (!box.hidden) textarea.focus();
  });

  addBtn.addEventListener("click", async () => {
    // Split on newlines AND commas so "tantrum, elopement" on one line adds two
    // separate behaviors instead of one combined entry. Catalog labels that
    // legitimately contain commas (e.g. "Aggression (e.g., hitting, kicking,
    // biting)") don't need to be pasted in full — matchCatalogItem() matches
    // against the label's core text before any parenthetical, so a short
    // "Aggression" still matches correctly even after the comma split.
    const lines = textarea.value
      .split(/\r?\n|,/)
      .map((l) => l.replace(/^[\s\-*••]+|^\d+[.)]\s*/, "").trim())
      .filter(Boolean);
    if (!lines.length) return;

    addBtn.disabled = true;
    status.textContent = "Adding...";

    let matchedCount = 0;
    let createdCount = 0;
    const toCreate = [];
    for (const line of lines) {
      const match = matchCatalogItem(line, OPTIONS[category]);
      if (match) {
        if (singleSelect) store[key] = match.id;
        else store[key].add(match.id);
        matchedCount++;
      } else {
        toCreate.push(line);
      }
    }

    // Sequential, not parallel: each request reads-modifies-writes the same
    // options_json, so concurrent requests could overwrite each other's additions.
    for (const label of toCreate) {
      const res = await apiFetch("/api/options/custom", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category, label }),
      });
      if (!res.ok) continue;
      const item = await res.json();
      OPTIONS[category].push(item);
      if (singleSelect) store[key] = item.id;
      else store[key].add(item.id);
      createdCount++;
    }

    textarea.value = "";
    addBtn.disabled = false;
    status.textContent = `Added ${matchedCount + createdCount} of ${lines.length}: ${matchedCount} matched existing options, ${createdCount} added as new.`;
    renderChipGroup(containerId, OPTIONS[category], key, singleSelect, store, store[key], onChange, category, true);
    if (onChange) onChange();
  });

  box.appendChild(textarea);
  box.appendChild(addBtn);
  box.appendChild(status);
  row.appendChild(toggle);
  row.appendChild(box);
  anchor.insertAdjacentElement("afterend", row);
}

// Auto-injects a "Not listed? Add one manually..." row immediately after a chip-grid
// container the first time it's rendered with a customCategory, then leaves it in place
// (and its listeners intact) across re-renders of that same chip-grid.
function ensureCustomAddRow(containerId, category, key, singleSelect, store, onChange) {
  const rowId = `${containerId}CustomRow`;
  if (el(rowId)) return;

  const container = el(containerId);
  const row = document.createElement("div");
  row.id = rowId;
  row.className = "custom-add-row";

  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = "Not listed? Add one manually...";

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "btn secondary small";
  btn.textContent = "Add";

  const submit = async () => {
    // Typing several items at once (comma-separated) adds each as its own chip
    // instead of one chip with the whole string as its label.
    const labels = input.value.split(",").map((l) => l.trim()).filter(Boolean);
    if (!labels.length) return;

    // Sequential, not parallel: each request reads-modifies-writes the same
    // options_json, so concurrent requests could overwrite each other's additions.
    for (const label of labels) {
      const res = await apiFetch("/api/options/custom", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category, label }),
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.error || `Failed to add "${label}".`);
        continue;
      }
      const item = await res.json();
      OPTIONS[category].push(item);
      if (singleSelect) {
        store[key] = item.id;
      } else {
        if (!store[key]) store[key] = new Set();
        store[key].add(item.id);
      }
    }

    input.value = "";
    renderChipGroup(containerId, OPTIONS[category], key, singleSelect, store, store[key], onChange, category);
    if (onChange) onChange();
  };

  btn.addEventListener("click", submit);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      submit();
    }
  });

  row.appendChild(input);
  row.appendChild(btn);
  container.insertAdjacentElement("afterend", row);
}

async function refreshClients() {
  CLIENTS = await fetch("/api/clients").then((r) => r.json());
  const sel = el("clientSelect");
  const current = sel.value;
  sel.innerHTML = '<option value="">-- Select client --</option>';
  CLIENTS.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = c.name;
    sel.appendChild(opt);
  });
  if (current) sel.value = current;
}

function currentClient() {
  return CLIENTS.find((c) => c.id === el("clientSelect").value);
}

function clientProgramItems(client) {
  const ids = client.replacement_programs || [];
  if (!ids.length) return OPTIONS.replacement_programs;
  return OPTIONS.replacement_programs.filter((p) => ids.includes(p.id));
}

function clientBehaviorItems(client) {
  const ids = client.maladaptive_behaviors || [];
  if (!ids.length) return OPTIONS.maladaptive_behaviors;
  return OPTIONS.maladaptive_behaviors.filter((b) => ids.includes(b.id));
}

function clientAntecedentItems(client) {
  const ids = client.antecedents || [];
  if (!ids.length) return OPTIONS.antecedents;
  return OPTIONS.antecedents.filter((a) => ids.includes(a.id));
}

function clientInterventionItems(client) {
  const ids = client.intervention_strategies || [];
  if (!ids.length) return OPTIONS.intervention_strategies;
  return OPTIONS.intervention_strategies.filter((s) => ids.includes(s.id));
}

function clientTrainingTopicItems(client) {
  const ids = client.training_topics || [];
  if (!ids.length) return OPTIONS.caregiver_training_topics;
  return OPTIONS.caregiver_training_topics.filter((t) => ids.includes(t.id));
}

function resetNewClientChips() {
  newClientSelections.replacement_programs = new Set();
  newClientSelections.maladaptive_behaviors = new Set();
  newClientSelections.antecedents = new Set();
  newClientSelections.intervention_strategies = new Set();
  newClientSelections.training_topics = new Set();
  renderChipGroup("ncReplacementPrograms", OPTIONS.replacement_programs, "replacement_programs", false, newClientSelections, null, null, "replacement_programs", true);
  renderChipGroup("ncMaladaptiveBehaviors", OPTIONS.maladaptive_behaviors, "maladaptive_behaviors", false, newClientSelections, null, null, "maladaptive_behaviors", true);
  renderChipGroup("ncAntecedents", OPTIONS.antecedents, "antecedents", false, newClientSelections, null, null, "antecedents", true);
  renderChipGroup("ncInterventionStrategies", OPTIONS.intervention_strategies, "intervention_strategies", false, newClientSelections, null, null, "intervention_strategies", true);
  renderChipGroup("ncTrainingTopics", OPTIONS.caregiver_training_topics, "training_topics", false, newClientSelections, null, null, "caregiver_training_topics", true);
}

function resetDocExtractUI() {
  newClientBehaviorTopographies = {};
  const statusEl = el("docExtractStatus");
  statusEl.hidden = true;
  statusEl.textContent = "";
  statusEl.className = "doc-extract-status";
  ["dropInitialAssessment", "dropReassessment"].forEach((id) => el(id).classList.remove("has-file"));
}

function applyExtractedData(data) {
  if (data.name && !el("ncName").value.trim()) el("ncName").value = data.name;
  if (data.dob && !el("ncDob").value) el("ncDob").value = data.dob;
  if (data.guardian_name && !el("ncGuardianName").value.trim()) el("ncGuardianName").value = data.guardian_name;

  if (data.maladaptive_behaviors && data.maladaptive_behaviors.length) {
    data.maladaptive_behaviors.forEach((id) => newClientSelections.maladaptive_behaviors.add(id));
    renderChipGroup(
      "ncMaladaptiveBehaviors", OPTIONS.maladaptive_behaviors, "maladaptive_behaviors", false,
      newClientSelections, new Set(newClientSelections.maladaptive_behaviors), null, "maladaptive_behaviors", true
    );
  }
  if (data.replacement_programs && data.replacement_programs.length) {
    data.replacement_programs.forEach((id) => newClientSelections.replacement_programs.add(id));
    renderChipGroup(
      "ncReplacementPrograms", OPTIONS.replacement_programs, "replacement_programs", false,
      newClientSelections, new Set(newClientSelections.replacement_programs), null, "replacement_programs", true
    );
  }
  if (data.intervention_strategies && data.intervention_strategies.length) {
    data.intervention_strategies.forEach((id) => newClientSelections.intervention_strategies.add(id));
    renderChipGroup(
      "ncInterventionStrategies", OPTIONS.intervention_strategies, "intervention_strategies", false,
      newClientSelections, new Set(newClientSelections.intervention_strategies), null, "intervention_strategies", true
    );
  }
  if (data.behavior_topographies) {
    Object.assign(newClientBehaviorTopographies, data.behavior_topographies);
  }
}

async function handleDocumentDrop(dropZoneId, docType, file) {
  const statusEl = el("docExtractStatus");
  const dropZone = el(dropZoneId);
  if (!file) return;

  const ext = file.name.includes(".") ? file.name.split(".").pop().toLowerCase() : "";
  if (!["pdf", "docx"].includes(ext)) {
    statusEl.hidden = false;
    statusEl.className = "doc-extract-status error";
    statusEl.textContent = "Only PDF and Word (.docx) files are supported.";
    return;
  }

  statusEl.hidden = false;
  statusEl.className = "doc-extract-status";
  statusEl.textContent = `Reading ${file.name}...`;

  const formData = new FormData();
  formData.append("file", file);
  formData.append("doc_type", docType);

  let res, data;
  try {
    res = await fetch("/api/extract-client-document", {
      method: "POST",
      headers: { "X-CSRFToken": CSRF_TOKEN },
      body: formData,
    });
    data = await res.json();
  } catch (err) {
    statusEl.className = "doc-extract-status error";
    statusEl.textContent = "Upload failed. Please check your connection and try again.";
    return;
  }

  if (!res.ok) {
    statusEl.className = "doc-extract-status error";
    statusEl.textContent = data.error || "Could not extract information from that file.";
    return;
  }

  dropZone.classList.add("has-file");
  applyExtractedData(data);

  const extras = [];
  if (data.age) extras.push(`age ${data.age}`);
  if (data.bcba_name) extras.push(`authoring BCBA "${data.bcba_name}" (no field for this yet, not auto-filled)`);
  statusEl.className = "doc-extract-status";
  statusEl.textContent =
    `Pulled info from ${file.name} - please review the fields below before saving.` +
    (extras.length ? ` Also found: ${extras.join(", ")}.` : "");
}

function setupDropZone(zoneId, inputId, docType) {
  const zone = el(zoneId);
  const input = el(inputId);
  zone.addEventListener("click", () => input.click());
  zone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      input.click();
    }
  });
  input.addEventListener("change", () => {
    if (input.files[0]) handleDocumentDrop(zoneId, docType, input.files[0]);
    input.value = "";
  });
  zone.addEventListener("dragover", (e) => {
    e.preventDefault();
    zone.classList.add("dragover");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file) handleDocumentDrop(zoneId, docType, file);
  });
}

function bindStaticEvents() {
  el("clientSelect").addEventListener("change", onClientChange);

  document.querySelectorAll(".panel-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = el(btn.dataset.toggle);
      target.hidden = !target.hidden;
      btn.textContent = target.hidden ? "Show" : "Hide";
    });
  });

  el("addParticipantBtn").addEventListener("click", () => addParticipantRow("bcba", ""));

  el("quickModeToggle").addEventListener("change", () => {
    quickMode = el("quickModeToggle").checked;
    el("clientSelectWrap").hidden = quickMode;
    el("quickClientNameField").hidden = !quickMode;
    el("saveBtn").hidden = quickMode;

    if (quickMode) {
      el("clientSelect").value = "";
      el("newClientPanel").hidden = true;
      el("clientTargetsPanel").hidden = true;
      el("notesHistoryPanel").hidden = true;
      el("noSelectionMsg").hidden = true;
      el("outputPanel").hidden = true;
      el("noteForm").hidden = false;
      el("quickClientName").value = "";
      selections.replacement_programs = new Set();
      selections.maladaptive_behaviors = new Set();
      renderClientSpecificChips({});
      applyProviderDefaults(null);
      buildSectionNav();
    } else {
      el("notesHistoryPanel").hidden = false;
      onClientChange();
    }
  });

  el("wordTargetSlider").addEventListener("input", () => {
    el("wordTargetValue").textContent = `${el("wordTargetSlider").value} words`;
  });

  el("newClientBtn").addEventListener("click", () => {
    editingClientId = null;
    el("clientFormTitle").textContent = "New Client";
    ["ncName", "ncDob", "ncDiagnosis", "ncGuardianName", "ncGuardianRel", "ncRbtName"].forEach((id) => (el(id).value = ""));
    resetNewClientChips();
    resetDocExtractUI();
    el("ncDocExtractSection").hidden = false;
    el("newClientTargetsSection").hidden = false;
    el("newClientPanel").hidden = false;
    el("newClientPanel").scrollIntoView({ behavior: "smooth" });
  });
  el("editClientBtn").addEventListener("click", () => {
    const client = currentClient();
    if (!client) return;
    el("ncDocExtractSection").hidden = true;
    editingClientId = client.id;
    el("clientFormTitle").textContent = `Edit ${client.name}`;
    el("ncName").value = client.name || "";
    el("ncDob").value = client.dob || "";
    el("ncDiagnosis").value = client.diagnosis || "";
    el("ncGuardianName").value = client.guardian_name || "";
    el("ncGuardianRel").value = client.guardian_relationship || "";
    el("ncRbtName").value = client.rbt_name || "";
    el("newClientTargetsSection").hidden = true;
    el("newClientPanel").hidden = false;
    el("newClientPanel").scrollIntoView({ behavior: "smooth" });
  });
  el("deleteClientBtn").addEventListener("click", async () => {
    const client = currentClient();
    if (!client) return;
    if (!confirm(`Delete ${client.name}? This permanently removes this client and all of their saved notes. This cannot be undone.`)) return;

    const res = await apiFetch(`/api/clients/${client.id}`, { method: "DELETE" });
    if (!res.ok) {
      const err = await res.json();
      alert(err.error || "Failed to delete client.");
      return;
    }
    await refreshClients();
    el("clientSelect").value = "";
    onClientChange();
  });
  el("ncCancel").addEventListener("click", () => {
    el("newClientPanel").hidden = true;
    editingClientId = null;
  });
  el("ncSave").addEventListener("click", saveClientForm);

  el("targetsToggleBtn").addEventListener("click", () => {
    el("targetsEditArea").hidden = !el("targetsEditArea").hidden;
  });
  el("saveTargetsBtn").addEventListener("click", saveClientTargets);

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      currentNoteType = tab.dataset.type;
      const isSessionLike = currentNoteType === "session" || currentNoteType === "bcaba_session" || currentNoteType === "rbt_session";
      const isReviewedSession = currentNoteType === "session" || currentNoteType === "bcaba_session";
      el("sessionFields").hidden = !isSessionLike;
      el("caregiverFields").hidden = currentNoteType !== "caregiver";
      el("initialAssessmentFields").hidden = currentNoteType !== "initial_assessment";
      el("reassessmentFields").hidden = currentNoteType !== "reassessment";
      el("sessionTimingFields").hidden = !isSessionLike;
      el("cptCodeField").hidden = !isSessionLike;
      el("protocolModificationSection").hidden = !isReviewedSession;
      el("bcbaFeedbackSection").hidden = !isReviewedSession;
      el("bcbaFeedbackHeading").textContent =
        currentNoteType === "bcaba_session"
          ? "BCaBA Direct Observation & Feedback (optional)"
          : "BCBA Direct Observation & Feedback (optional)";
      if (isSessionLike) {
        el("cptCode").value = isReviewedSession ? "97155" : "97153";
      }
      el("outputPanel").hidden = true;
      applyProviderDefaults(currentClient());
      renderClientSpecificChips(currentClient());
      buildSectionNav();
    });
  });

  el("noteForm").addEventListener("submit", (e) => {
    e.preventDefault();
    generateNote();
  });
  el("regenerateBtn").addEventListener("click", generateNote);
  el("saveBtn").addEventListener("click", saveNote);
  el("copyBtn").addEventListener("click", async () => {
    await navigator.clipboard.writeText(el("outputText").value);
    const btn = el("copyBtn");
    const original = btn.textContent;
    btn.textContent = "Copied!";
    setTimeout(() => (btn.textContent = original), 1500);
  });
}

async function saveClientForm() {
  const name = el("ncName").value.trim();
  if (!name) {
    alert("Client name is required.");
    return;
  }
  const body = {
    name,
    dob: el("ncDob").value,
    diagnosis: el("ncDiagnosis").value,
    guardian_name: el("ncGuardianName").value,
    guardian_relationship: el("ncGuardianRel").value,
    rbt_name: el("ncRbtName").value,
  };

  const isEditing = !!editingClientId;
  if (!isEditing) {
    body.replacement_programs = [...newClientSelections.replacement_programs];
    body.maladaptive_behaviors = [...newClientSelections.maladaptive_behaviors];
    body.antecedents = [...newClientSelections.antecedents];
    body.intervention_strategies = [...newClientSelections.intervention_strategies];
    body.training_topics = [...newClientSelections.training_topics];
    body.behavior_topographies = { ...newClientBehaviorTopographies };
  }
  const url = isEditing ? `/api/clients/${editingClientId}` : "/api/clients";
  const method = isEditing ? "PATCH" : "POST";

  const res = await apiFetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json();
    alert(err.error || "Failed to save client.");
    return;
  }
  const client = await res.json();
  await refreshClients();
  el("clientSelect").value = client.id;
  el("newClientPanel").hidden = true;
  editingClientId = null;
  onClientChange();
}

// Rebuilds the sticky jump-nav from whichever section.panel elements are
// actually visible in the current note form - the set changes per note type
// (session vs. caregiver vs. assessment fields), so this reads the live DOM
// rather than keeping a separate hardcoded list in sync.
function buildSectionNav() {
  const nav = el("sectionNav");
  nav.innerHTML = "";
  if (el("noteForm").hidden) {
    nav.hidden = true;
    return;
  }

  const sections = [...el("noteForm").querySelectorAll("section.panel")].filter((sec) => {
    if (sec.hidden) return false;
    let node = sec.parentElement;
    while (node && node !== el("noteForm")) {
      if (node.hidden) return false;
      node = node.parentElement;
    }
    return sec.querySelectorAll("input, select, textarea, .chip-grid").length > 0;
  });

  sections.forEach((sec, i) => {
    const h2 = sec.querySelector("h2");
    if (!h2) return;
    if (!sec.id) sec.id = `panelAuto${i}`;
    const link = document.createElement("button");
    link.type = "button";
    link.className = "section-nav-link";
    link.textContent = h2.textContent.replace(/\s*\([^)]*optional[^)]*\)/i, "").trim();
    link.addEventListener("click", () => sec.scrollIntoView({ behavior: "smooth", block: "start" }));
    nav.appendChild(link);
  });

  nav.hidden = sections.length === 0;
}

function onClientChange() {
  const client = currentClient();
  el("noteForm").hidden = !client;
  el("noSelectionMsg").hidden = !!client;
  el("outputPanel").hidden = true;
  el("clientTargetsPanel").hidden = !client;
  el("editClientBtn").hidden = !client;
  el("deleteClientBtn").hidden = !client;

  selections.replacement_programs = new Set();
  selections.maladaptive_behaviors = new Set();

  if (client) {
    loadNotesHistory(client.id);
    renderTargetsPanel(client);
    renderClientSpecificChips(client);
    applyProviderDefaults(client);
  } else {
    el("notesHistory").innerHTML = "Select a client to view saved notes.";
  }
  buildSectionNav();
}

function renderClientSpecificChips(client) {
  if (!client) return;
  const programs = clientProgramItems(client);
  const behaviors = clientBehaviorItems(client);
  const trainingTopics = clientTrainingTopicItems(client);
  renderChipGroup("replacementPrograms", programs, "replacement_programs", false, selections, null, renderProgramScenarioPickers, "replacement_programs");
  renderChipGroup("maladaptiveBehaviors", behaviors, "maladaptive_behaviors", false, selections, null, renderBehaviorPairingPickers, "maladaptive_behaviors");
  renderChipGroup("trainingTopics", trainingTopics, "training_topics", false, selections, null, null, "caregiver_training_topics");
  renderChipGroup("initialSkills", programs, "replacement_programs", false, selections, null, null, "replacement_programs");
  renderChipGroup("initialBehaviors", behaviors, "maladaptive_behaviors", false, selections, null, null, "maladaptive_behaviors");
  renderChipGroup("reassessmentSkills", programs, "replacement_programs", false, selections, null, null, "replacement_programs");
  renderChipGroup("reassessmentBehaviors", behaviors, "maladaptive_behaviors", false, selections, null, null, "maladaptive_behaviors");
  renderProgramScenarioPickers();
  renderBehaviorPairingPickers();
}

// Shared by program scenario pickers and behavior topography pickers: a select of
// a default option / each pre-written variant / "Write my own..." plus a text input
// that only shows for the custom option, backed by `store[itemId]` (undefined = the
// default option's behavior, a number = that variant's index, a string = custom text).
function appendScenarioPicker(row, itemId, blurbs, store, labelText, placeholderText, defaultOptionLabel) {
  const field = document.createElement("div");
  field.className = "scenario-field";

  const label = document.createElement("label");
  label.textContent = labelText;
  field.appendChild(label);

  const select = document.createElement("select");
  const randomOpt = document.createElement("option");
  randomOpt.value = "";
  randomOpt.textContent = defaultOptionLabel || "Random (varies each time)";
  select.appendChild(randomOpt);

  blurbs.forEach((blurb, idx) => {
    const opt = document.createElement("option");
    opt.value = idx;
    // Full text (no truncation) so the option is readable both in the open
    // dropdown list and via the preview paragraph below the closed select,
    // which the closed <select> box itself can't show for longer scenarios.
    opt.textContent = `Option ${idx + 1}: ${blurb}`;
    select.appendChild(opt);
  });

  const customOpt = document.createElement("option");
  customOpt.value = "custom";
  customOpt.textContent = "Write my own...";
  select.appendChild(customOpt);

  const current = store[itemId];
  const isCustom = typeof current === "string";
  select.value = current !== undefined ? (isCustom ? "custom" : String(current)) : "";

  const preview = document.createElement("div");
  preview.className = "scenario-preview";
  const updatePreview = () => {
    const idx = Number(select.value);
    if (select.value !== "" && select.value !== "custom" && !Number.isNaN(idx) && blurbs[idx]) {
      preview.textContent = blurbs[idx];
      preview.hidden = false;
    } else {
      preview.hidden = true;
    }
  };
  updatePreview();

  const customInput = document.createElement("input");
  customInput.type = "text";
  customInput.className = "scenario-custom-input";
  customInput.placeholder = placeholderText;
  customInput.hidden = !isCustom;
  customInput.value = isCustom ? current : "";
  customInput.addEventListener("input", () => {
    if (customInput.value.trim()) {
      store[itemId] = customInput.value.trim();
    } else {
      delete store[itemId];
    }
  });

  select.addEventListener("change", () => {
    if (select.value === "") {
      delete store[itemId];
      customInput.hidden = true;
    } else if (select.value === "custom") {
      customInput.hidden = false;
      customInput.focus();
      if (customInput.value.trim()) {
        store[itemId] = customInput.value.trim();
      } else {
        delete store[itemId];
      }
    } else {
      customInput.hidden = true;
      store[itemId] = Number(select.value);
    }
    updatePreview();
  });

  field.appendChild(select);
  field.appendChild(preview);
  field.appendChild(customInput);
  row.appendChild(field);
}

function renderProgramScenarioPickers() {
  const container = el("programScenarioPickers");
  const selectedIds = [...selections.replacement_programs];
  Object.keys(programScenarios).forEach((id) => {
    if (!selectedIds.includes(id)) delete programScenarios[id];
  });

  const programs = OPTIONS.replacement_programs.filter((p) => selectedIds.includes(p.id) && p.blurbs && p.blurbs.length > 1);
  container.innerHTML = "";
  if (!programs.length) {
    container.hidden = true;
    return;
  }
  container.hidden = false;

  programs.forEach((p) => {
    const row = document.createElement("div");
    row.className = "scenario-picker-row";

    const title = document.createElement("div");
    title.className = "scenario-picker-title";
    title.textContent = p.label;
    row.appendChild(title);

    appendScenarioPicker(
      row, p.id, p.blurbs, programScenarios,
      "Scenario",
      "Describe what the RBT did for this program during this session..."
    );
    container.appendChild(row);
  });
}

function renderBehaviorPairingPickers() {
  const container = el("behaviorInterventionPickers");
  const selectedIds = [...selections.maladaptive_behaviors];
  Object.keys(behaviorInterventions).forEach((id) => {
    if (!selectedIds.includes(id)) delete behaviorInterventions[id];
  });
  Object.keys(behaviorAntecedents).forEach((id) => {
    if (!selectedIds.includes(id)) delete behaviorAntecedents[id];
  });
  Object.keys(behaviorTopographies).forEach((id) => {
    if (!selectedIds.includes(id)) delete behaviorTopographies[id];
  });

  const behaviors = OPTIONS.maladaptive_behaviors.filter((b) => selectedIds.includes(b.id));
  container.innerHTML = "";
  if (!behaviors.length) {
    container.hidden = true;
    return;
  }
  container.hidden = false;

  const interventionCatalog = clientInterventionItems(currentClient() || {});
  const antecedentCatalog = clientAntecedentItems(currentClient() || {});

  behaviors.forEach((b) => {
    const row = document.createElement("div");
    row.className = "scenario-picker-row";

    const title = document.createElement("div");
    title.className = "scenario-picker-title";
    title.textContent = b.label;
    row.appendChild(title);

    if (b.blurbs && b.blurbs.length > 1) {
      appendScenarioPicker(
        row, b.id, b.blurbs, behaviorTopographies,
        "Topography",
        "Describe what this behavior looked like during this session...",
        "Option 1 (default)"
      );
    }

    const antecedentField = document.createElement("div");
    antecedentField.className = "scenario-field";
    const antecedentLabel = document.createElement("label");
    antecedentLabel.textContent = "Antecedents / Triggers";
    antecedentField.appendChild(antecedentLabel);

    const antecedentContainerId = `behaviorAntecedent_${b.id}`;
    const antecedentContainer = document.createElement("div");
    antecedentContainer.id = antecedentContainerId;
    antecedentContainer.className = "chip-grid";
    antecedentField.appendChild(antecedentContainer);
    row.appendChild(antecedentField);

    const interventionField = document.createElement("div");
    interventionField.className = "scenario-field";
    const interventionLabel = document.createElement("label");
    interventionLabel.textContent = "Interventions Used";
    interventionField.appendChild(interventionLabel);

    const chipContainerId = `behaviorIntervention_${b.id}`;
    const chipContainer = document.createElement("div");
    chipContainer.id = chipContainerId;
    chipContainer.className = "chip-grid";
    interventionField.appendChild(chipContainer);
    row.appendChild(interventionField);
    container.appendChild(row);

    if (!behaviorAntecedents[b.id]) behaviorAntecedents[b.id] = new Set();
    renderChipGroup(
      antecedentContainerId,
      antecedentCatalog,
      b.id,
      false,
      behaviorAntecedents,
      behaviorAntecedents[b.id],
      null,
      "antecedents"
    );

    if (!behaviorInterventions[b.id]) behaviorInterventions[b.id] = new Set();
    renderChipGroup(
      chipContainerId,
      interventionCatalog,
      b.id,
      false,
      behaviorInterventions,
      behaviorInterventions[b.id],
      null,
      "intervention_strategies"
    );
  });
}

function renderParticipants() {
  const container = el("participantsList");
  container.innerHTML = "";
  participants.forEach((p, idx) => {
    const row = document.createElement("div");
    row.className = "participant-row";

    const roleSelect = document.createElement("select");
    PARTICIPANT_ROLES.forEach((r) => {
      const opt = document.createElement("option");
      opt.value = r.id;
      opt.textContent = r.label;
      if (r.id === p.role) opt.selected = true;
      roleSelect.appendChild(opt);
    });
    roleSelect.addEventListener("change", () => {
      participants[idx].role = roleSelect.value;
    });

    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.placeholder = "Name";
    nameInput.value = p.name;
    nameInput.addEventListener("input", () => {
      participants[idx].name = nameInput.value;
    });

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "btn secondary small";
    removeBtn.textContent = "Remove";
    removeBtn.addEventListener("click", () => {
      participants.splice(idx, 1);
      renderParticipants();
    });

    row.appendChild(roleSelect);
    row.appendChild(nameInput);
    row.appendChild(removeBtn);
    container.appendChild(row);
  });
}

function addParticipantRow(role, name) {
  participants.push({ role: role || "bcba", name: name || "" });
  renderParticipants();
}

function findParticipant(role) {
  return participants.find((p) => p.role === role && p.name.trim());
}

function participantNames(role) {
  return participants.filter((p) => p.role === role && p.name.trim()).map((p) => p.name.trim());
}

function applyProviderDefaults(client) {
  const bcbaOnlyNoteTypes = ["caregiver", "initial_assessment", "reassessment"];
  const isBcbaOnlyNote = bcbaOnlyNoteTypes.includes(currentNoteType);
  // Session notes name the reviewing clinician's role differently depending on
  // who authored them: a BCBA note reviews under role "bcba", a BCaBA note
  // reviews under role "bcaba". Plain RBT session notes have no reviewing
  // clinician field at all, so they get no default here.
  const reviewingRole =
    currentNoteType === "session" ? "bcba" :
    currentNoteType === "bcaba_session" ? "bcaba" :
    isBcbaOnlyNote ? "bcba" : null;

  if (reviewingRole && BCBA_NAME) {
    const alreadyCorrect = participants.some((p) => p.role === reviewingRole && p.name.trim());
    if (!alreadyCorrect) {
      // A BCaBA session note only credits a participant with role "bcaba"
      // specifically (no bcba/bcaba fallback, unlike the other note types), so
      // retarget a same-name auto-fill left over from switching note-type tabs
      // instead of leaving a stale entry under the wrong role.
      const otherRole = reviewingRole === "bcba" ? "bcaba" : "bcba";
      const staleAutoFill = participants.find((p) => p.role === otherRole && p.name.trim() === BCBA_NAME);
      if (staleAutoFill) {
        staleAutoFill.role = reviewingRole;
      } else {
        const existing = participants.find((p) => p.role === reviewingRole);
        if (existing) {
          existing.name = BCBA_NAME;
        } else {
          participants.push({ role: reviewingRole, name: BCBA_NAME });
        }
      }
    }
  }

  if (isBcbaOnlyNote) {
    if (client && client.guardian_name) {
      const existingCaregiver = participants.find((p) => p.role === "caregiver");
      if (existingCaregiver) {
        existingCaregiver.name = client.guardian_name;
      } else {
        participants.push({ role: "caregiver", name: client.guardian_name });
      }
    }
    if (currentNoteType === "caregiver" && client && client.guardian_name && !el("caregiverName").value.trim()) {
      el("caregiverName").value = client.guardian_name;
    }
  } else if (client && client.rbt_name) {
    const existingRbt = participants.find((p) => p.role === "rbt");
    if (existingRbt) {
      existingRbt.name = client.rbt_name;
    } else {
      participants.push({ role: "rbt", name: client.rbt_name });
    }
  }
  renderParticipants();
}

// Condenses a long label list to a short, scannable preview instead of dumping
// every label into one wall of text (a client with no restrictions set shows the
// full catalog per category, which can run 40+ items).
function _summarizeList(items, limit = 3) {
  if (!items.length) return "none";
  const labels = items.map((i) => i.label);
  if (labels.length <= limit) return labels.join(", ");
  const shown = labels.slice(0, limit).join(", ");
  return `${shown}, +${labels.length - limit} more`;
}

function renderTargetsPanel(client, forceOpen) {
  const programIds = client.replacement_programs || [];
  const behaviorIds = client.maladaptive_behaviors || [];
  const antecedentIds = client.antecedents || [];
  const interventionIds = client.intervention_strategies || [];
  const topicIds = client.training_topics || [];

  const summary = el("targetsSummary");
  if (!programIds.length && !behaviorIds.length && !antecedentIds.length && !interventionIds.length && !topicIds.length) {
    summary.textContent = "No client-specific targets set — all standard programs, behaviors, antecedents, interventions, and training topics are available. Click Edit to restrict this client's list.";
  } else {
    const rows = [
      ["Programs", clientProgramItems(client)],
      ["Behaviors", clientBehaviorItems(client)],
      ["Antecedents", clientAntecedentItems(client)],
      ["Interventions", clientInterventionItems(client)],
      ["Training Topics", clientTrainingTopicItems(client)],
    ];
    summary.innerHTML = "";
    rows.forEach(([label, items]) => {
      const row = document.createElement("div");
      row.className = "targets-summary-row";
      const strong = document.createElement("strong");
      strong.textContent = `${label} (${items.length}):`;
      row.appendChild(strong);
      row.appendChild(document.createTextNode(` ${_summarizeList(items)}`));
      summary.appendChild(row);
    });
  }

  el("targetsEditArea").hidden = !forceOpen;
  targetEditSelections.replacement_programs = new Set(programIds);
  targetEditSelections.maladaptive_behaviors = new Set(behaviorIds);
  targetEditSelections.antecedents = new Set(antecedentIds);
  targetEditSelections.intervention_strategies = new Set(interventionIds);
  targetEditSelections.training_topics = new Set(topicIds);
  renderChipGroup("clientReplacementPrograms", OPTIONS.replacement_programs, "replacement_programs", false, targetEditSelections, new Set(programIds), null, "replacement_programs");
  renderChipGroup("clientMaladaptiveBehaviors", OPTIONS.maladaptive_behaviors, "maladaptive_behaviors", false, targetEditSelections, new Set(behaviorIds), null, "maladaptive_behaviors");
  renderChipGroup("clientAntecedents", OPTIONS.antecedents, "antecedents", false, targetEditSelections, new Set(antecedentIds), null, "antecedents");
  renderChipGroup("clientInterventionStrategies", OPTIONS.intervention_strategies, "intervention_strategies", false, targetEditSelections, new Set(interventionIds), null, "intervention_strategies");
  renderChipGroup("clientTrainingTopics", OPTIONS.caregiver_training_topics, "training_topics", false, targetEditSelections, new Set(topicIds), null, "caregiver_training_topics");
  el("targetsSaveStatus").textContent = "";
}

async function saveClientTargets() {
  const client = currentClient();
  const body = {
    replacement_programs: [...targetEditSelections.replacement_programs],
    maladaptive_behaviors: [...targetEditSelections.maladaptive_behaviors],
    antecedents: [...targetEditSelections.antecedents],
    intervention_strategies: [...targetEditSelections.intervention_strategies],
    training_topics: [...targetEditSelections.training_topics],
  };
  const res = await apiFetch(`/api/clients/${client.id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    el("targetsSaveStatus").textContent = "Failed to save targets.";
    return;
  }
  await refreshClients();
  el("clientSelect").value = client.id;
  const updatedClient = currentClient();
  renderTargetsPanel(updatedClient);
  renderClientSpecificChips(updatedClient);
  el("targetsSaveStatus").textContent = "Targets saved.";
}

async function loadNotesHistory(clientId) {
  const notes = await fetch(`/api/notes?client_id=${clientId}`).then((r) => r.json());
  const container = el("notesHistory");
  if (!notes.length) {
    container.innerHTML = "No saved notes yet.";
    return;
  }
  container.innerHTML = "";
  notes.forEach((n) => {
    const row = document.createElement("div");
    row.className = "note-row";
    const label = document.createElement("span");
    const typeLabels = {
      session: "BCBA Session",
      bcaba_session: "BCaBA Session",
      rbt_session: "RBT Session",
      caregiver: "Caregiver",
      initial_assessment: "Initial Assessment",
      reassessment: "Reassessment",
    };
    label.textContent = `${n.session_date} · ${typeLabels[n.note_type] || n.note_type}`;
    const link = document.createElement("a");
    link.href = `/api/notes/download/${n.id}`;
    link.textContent = "download";
    row.appendChild(label);
    row.appendChild(link);
    container.appendChild(row);
  });
}

function buildPayload() {
  const placeOfService =
    el("placeOfService").value === "__other__" ? el("placeOfServiceCustom").value.trim() : el("placeOfService").value;
  const payload = {
    note_type: currentNoteType,
    place_of_service: placeOfService,
    additional_notes: el("additionalNotes").value,
    plan_next_session: el("planNextSession").value,
    target_word_count: el("wordTargetSlider").value,
  };

  if (quickMode) {
    payload.client_name = el("quickClientName").value.trim();
  } else {
    payload.client_id = currentClient().id;
  }

  const rbtParticipant = findParticipant("rbt");
  const bcbaParticipant = findParticipant("bcba") || findParticipant("bcaba");
  const bcabaOnlyParticipant = findParticipant("bcaba");
  const caregiverNames = participantNames("caregiver");

  if (currentNoteType === "session") {
    payload.session_date = el("sessionDate").value;
    payload.start_time = el("startTime").value;
    payload.end_time = el("endTime").value;
    payload.cpt_code = el("cptCode").value;
    payload.provider_name = rbtParticipant ? rbtParticipant.name.trim() : "";
    payload.provider_credential = "RBT";
    payload.reviewing_bcba_name = bcbaParticipant ? bcbaParticipant.name.trim() : "";
    payload.reviewing_bcba_credential = bcbaParticipant ? PARTICIPANT_ROLE_LABELS[bcbaParticipant.role] : "";
    payload.caregiver_participant_names = caregiverNames;
    payload.protocol_modifications = [...selections.protocol_modifications];
    payload.protocol_modification_data = el("protocolModData").value;
    payload.protocol_modification_response = el("protocolModResponse").value;
    payload.replacement_programs = [...selections.replacement_programs];
    payload.program_scenarios = { ...programScenarios };
    payload.maladaptive_behaviors = [...selections.maladaptive_behaviors];
    payload.behavior_interventions = Object.fromEntries(
      Object.entries(behaviorInterventions).map(([behaviorId, ids]) => [behaviorId, [...ids]])
    );
    payload.behavior_antecedents = Object.fromEntries(
      Object.entries(behaviorAntecedents).map(([behaviorId, ids]) => [behaviorId, [...ids]])
    );
    payload.behavior_topographies = { ...behaviorTopographies };
    payload.intervention_effectiveness = selections.intervention_effectiveness;
    payload.data_collection_methods = [...selections.data_collection_methods];
    payload.environmental_changes = [...selections.environmental_changes];
    payload.medical_concerns = [...selections.medical_concerns];
    payload.client_engagement = selections.client_engagement;
    payload.observation_method = selections.observation_method;
    payload.session_rating = selections.session_rating;
    payload.protocol_fidelity = selections.protocol_fidelity;
    payload.rbt_strengths = [...selections.rbt_strengths];
    payload.rbt_feedback_areas = [...selections.rbt_feedback_areas];
    payload.review_additional_notes = el("reviewAdditionalNotes").value;
  } else if (currentNoteType === "bcaba_session") {
    payload.session_date = el("sessionDate").value;
    payload.start_time = el("startTime").value;
    payload.end_time = el("endTime").value;
    payload.cpt_code = el("cptCode").value;
    payload.provider_name = rbtParticipant ? rbtParticipant.name.trim() : "";
    payload.provider_credential = "RBT";
    payload.reviewing_bcba_name = bcabaOnlyParticipant ? bcabaOnlyParticipant.name.trim() : "";
    payload.reviewing_bcba_credential = bcabaOnlyParticipant ? "BCaBA" : "";
    payload.caregiver_participant_names = caregiverNames;
    payload.protocol_modifications = [...selections.protocol_modifications];
    payload.protocol_modification_data = el("protocolModData").value;
    payload.protocol_modification_response = el("protocolModResponse").value;
    payload.replacement_programs = [...selections.replacement_programs];
    payload.program_scenarios = { ...programScenarios };
    payload.maladaptive_behaviors = [...selections.maladaptive_behaviors];
    payload.behavior_interventions = Object.fromEntries(
      Object.entries(behaviorInterventions).map(([behaviorId, ids]) => [behaviorId, [...ids]])
    );
    payload.behavior_antecedents = Object.fromEntries(
      Object.entries(behaviorAntecedents).map(([behaviorId, ids]) => [behaviorId, [...ids]])
    );
    payload.behavior_topographies = { ...behaviorTopographies };
    payload.intervention_effectiveness = selections.intervention_effectiveness;
    payload.data_collection_methods = [...selections.data_collection_methods];
    payload.environmental_changes = [...selections.environmental_changes];
    payload.medical_concerns = [...selections.medical_concerns];
    payload.client_engagement = selections.client_engagement;
    payload.observation_method = selections.observation_method;
    payload.session_rating = selections.session_rating;
    payload.protocol_fidelity = selections.protocol_fidelity;
    payload.rbt_strengths = [...selections.rbt_strengths];
    payload.rbt_feedback_areas = [...selections.rbt_feedback_areas];
    payload.review_additional_notes = el("reviewAdditionalNotes").value;
  } else if (currentNoteType === "rbt_session") {
    payload.session_date = el("sessionDate").value;
    payload.start_time = el("startTime").value;
    payload.end_time = el("endTime").value;
    payload.cpt_code = el("cptCode").value;
    payload.provider_name = rbtParticipant ? rbtParticipant.name.trim() : "";
    payload.provider_credential = "RBT";
    payload.caregiver_participant_names = caregiverNames;
    payload.replacement_programs = [...selections.replacement_programs];
    payload.program_scenarios = { ...programScenarios };
    payload.maladaptive_behaviors = [...selections.maladaptive_behaviors];
    payload.behavior_interventions = Object.fromEntries(
      Object.entries(behaviorInterventions).map(([behaviorId, ids]) => [behaviorId, [...ids]])
    );
    payload.behavior_antecedents = Object.fromEntries(
      Object.entries(behaviorAntecedents).map(([behaviorId, ids]) => [behaviorId, [...ids]])
    );
    payload.behavior_topographies = { ...behaviorTopographies };
    payload.intervention_effectiveness = selections.intervention_effectiveness;
    payload.data_collection_methods = [...selections.data_collection_methods];
    payload.environmental_changes = [...selections.environmental_changes];
    payload.medical_concerns = [...selections.medical_concerns];
    payload.client_engagement = selections.client_engagement;
  } else if (currentNoteType === "caregiver") {
    payload.provider_name = bcbaParticipant ? bcbaParticipant.name.trim() : "";
    payload.provider_credential = bcbaParticipant ? PARTICIPANT_ROLE_LABELS[bcbaParticipant.role] : "";
    payload.caregiver_name = el("caregiverName").value;
    payload.caregiver_relationship = el("caregiverRelationship").value;
    payload.training_topics = [...selections.training_topics];
    payload.teaching_methods = [...selections.teaching_methods];
    payload.caregiver_competency = selections.caregiver_competency;
    payload.caregiver_response = [...selections.caregiver_response];
    payload.training_barriers = [...selections.training_barriers];
  } else if (currentNoteType === "initial_assessment") {
    payload.provider_name = bcbaParticipant ? bcbaParticipant.name.trim() : "";
    payload.provider_credential = bcbaParticipant ? PARTICIPANT_ROLE_LABELS[bcbaParticipant.role] : "";
    payload.referral_reason = selections.referral_reason;
    payload.assessment_methods = [...selections.assessment_methods];
    payload.maladaptive_behaviors = [...selections.maladaptive_behaviors];
    payload.replacement_programs = [...selections.replacement_programs];
    payload.treatment_intensity = selections.treatment_intensity;
    payload.recommended_services = [...selections.recommended_services];
  } else if (currentNoteType === "reassessment") {
    payload.provider_name = bcbaParticipant ? bcbaParticipant.name.trim() : "";
    payload.provider_credential = bcbaParticipant ? PARTICIPANT_ROLE_LABELS[bcbaParticipant.role] : "";
    payload.assessment_methods = [...selections.assessment_methods];
    payload.progress_rating = selections.progress_rating;
    payload.replacement_programs = [...selections.replacement_programs];
    payload.maladaptive_behaviors = [...selections.maladaptive_behaviors];
    payload.data_collection_methods = [...selections.data_collection_methods];
    payload.reassessment_recommendations = [...selections.reassessment_recommendations];
  }
  return payload;
}

async function generateNote() {
  if (quickMode && !el("quickClientName").value.trim()) {
    alert("Enter a client name to generate a quick note.");
    return;
  }
  const payload = buildPayload();
  const res = await apiFetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    alert(err.error || "Failed to generate note.");
    return;
  }
  const result = await res.json();
  el("outputText").value = result.note_text;
  el("wordCount").textContent = `${result.word_count} words`;
  el("similarityBadge").textContent = `${result.max_similarity}% similar to prior notes`;
  el("outputPanel").hidden = false;
  el("saveStatus").textContent = "";
}

async function saveNote() {
  if (quickMode) {
    return;
  }
  const client = currentClient();
  const body = {
    client_id: client.id,
    note_type: currentNoteType,
    note_text: el("outputText").value,
  };
  if (el("sessionDate").value) {
    body.session_date = el("sessionDate").value;
  }
  const res = await apiFetch("/api/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const result = await res.json();
  if (!res.ok) {
    el("saveStatus").textContent = result.error || "Failed to save note.";
    return;
  }
  el("saveStatus").textContent = `Saved as ${result.filename}`;
  loadNotesHistory(client.id);
}

init();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js", { scope: "/" });
  });
}
