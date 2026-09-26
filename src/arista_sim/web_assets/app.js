const state = {
  sessionId: null,
  prompt: "switch>",
  history: [],
  historyIndex: 0,
  draft: "",
  labs: [],
  sections: [],
  curriculum: null,
  progress: {skills: [], recent_mistakes: []},
  selectedCurriculumSection: null,
  selectedTopic: null,
  labId: null,
  reference: null,
  exerciseChoices: [],
  exercise: null,
  hintsUsed: 0,
  exam: null,
  examIndex: 0,
  examAnswers: [],
  busy: false,
};

const output = document.querySelector("#terminal-output");
const form = document.querySelector("#terminal-form");
const input = document.querySelector("#command-input");
const promptLabel = document.querySelector("#prompt");
const connection = document.querySelector(".connection");
const connectionLabel = document.querySelector("#connection-label");
const labSelect = document.querySelector("#lab-select");
const referenceDialog = document.querySelector("#command-reference");
const referenceSearch = document.querySelector("#reference-search");
const referenceGroups = document.querySelector("#reference-groups");

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.headers.get("content-type")?.includes("application/json")) throw new Error("Your sign-in may have expired. Refresh this page to sign in again; saved configurations will remain.");
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Simulator request failed");
  return payload;
}

function setConnection(kind, label) {
  connection.classList.remove("ready", "error");
  if (kind) connection.classList.add(kind);
  connectionLabel.textContent = label;
}

function appendLine(text, className = "") {
  const line = document.createElement("div");
  line.className = className;
  line.textContent = text;
  output.append(line);
  while (output.children.length > 500) output.firstChild.remove();
  output.scrollTop = output.scrollHeight;
}

function appendCommand(prompt, command) {
  const line = document.createElement("div");
  line.className = "command-line";
  const promptSpan = document.createElement("span");
  promptSpan.className = "old-prompt";
  promptSpan.textContent = `${prompt} `;
  line.append(promptSpan, document.createTextNode(command));
  output.append(line);
  output.scrollTop = output.scrollHeight;
}

function renderLab(lab) {
  document.querySelector("#lab-title").textContent = lab.title;
  document.querySelector("#lab-difficulty").textContent = lab.difficulty;
  document.querySelector("#lab-time").textContent = `${lab.estimated_minutes} min`;
  document.querySelector("#lab-brief").textContent = lab.brief;

  const objectives = document.querySelector("#objectives");
  objectives.replaceChildren(...lab.objectives.map((objective) => {
    const item = document.createElement("li");
    item.textContent = objective;
    return item;
  }));

  const hints = document.querySelector("#hints-list");
  hints.replaceChildren(...lab.hints.map((hint) => {
    const item = document.createElement("li");
    item.textContent = hint;
    return item;
  }));
}

function resetBrowserState() {
  state.history = [];
  state.historyIndex = 0;
  state.draft = "";
  output.replaceChildren();
  document.querySelector("#grade-panel").hidden = true;
  document.querySelector("#progress-label").textContent = "Not checked";
}

async function startSession(labId) {
  state.busy = true;
  labSelect.disabled = true;
  try {
    input.disabled = true;
    resetBrowserState();
    const session = await api("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ lab_id: labId, resume: true }),
    });
    state.sessionId = session.session_id;
    state.labId = session.lab.id;
    state.prompt = session.prompt;
    labSelect.value = state.labId;
    promptLabel.textContent = state.prompt;
    renderLab(session.lab);
    renderCampus(session.campus, session.active);
    state.history = session.history || [];
    state.historyIndex = state.history.length;
    try { localStorage.setItem("arista-last-lab", state.labId); } catch {}
    document.querySelector("#save-status").textContent = session.durable ? "Configurations autosave on the server. Each lab resumes where you left off, including from another device. Reset starts over." : "Progress lasts until this local server stops. Enable a data path for durable saves.";
    appendLine("Arista Network Foundations Simulator — Browser Lab", "welcome");
    appendLine("Lab loaded. Use show commands to inspect the current configuration.", "welcome");
    appendLine("Type ? for contextual help. Complete the objectives, then check your work.", "welcome");
    appendLine("");
    setConnection("ready", "Simulator ready");
    input.disabled = session.closed;
    if (session.closed) appendLine("Session closed. Reset the lab to continue.", "welcome");
    input.focus();
  } catch (error) {
    setConnection("error", "Simulator unavailable");
    appendLine(error.message, "error-line");
    input.disabled = true;
  } finally {
    state.busy = false;
    labSelect.disabled = false;
  }
}

async function initialize() {
  try {
    const [catalog, reference, exercise, exercises, progress, exam, curriculum] = await Promise.all([api("/api/labs"), api("/api/reference"), api("/api/study-now"), api("/api/exercises"), api("/api/progress"), api("/api/exam"), api("/api/curriculum")]);
    state.labs = catalog.labs;
    state.sections = catalog.sections || [];
    initializeSections();
    state.reference = reference;
    state.exerciseChoices = exercises.exercises;
    state.curriculum = curriculum;
    state.progress = progress;
    document.querySelector("#practice-choice").replaceChildren(...state.exerciseChoices.map(choice => new Option(`${choice.title} · ${choice.mode}`, choice.id)));
    renderProgress(progress);
    renderExercise(exercise);
    renderDashboard();
    renderCurriculumWorkspace();
    if (exam.active) renderExam(exam.active);
    labSelect.replaceChildren(...state.labs.map((lab) => {
      const option = document.createElement("option");
      option.value = lab.id;
      option.textContent = lab.title;
      return option;
    }));
    renderReference("");
    let lastLab;
    try { lastLab = localStorage.getItem("arista-last-lab"); } catch {}
    await startSession(state.labs.find(l => l.id === lastLab)?.id || state.labs[0].id);
  } catch (error) {
    setConnection("error", "Simulator unavailable");
    appendLine(error.message, "error-line");
    input.disabled = true;
  }
}

const MODE_LABELS = {learn: "Concept knowledge", recall: "Recall", analyze: "Analysis", configure: "Configuration", verify: "Verification", troubleshoot: "Troubleshooting"};
const PRIORITY_SCORE = {very_high: 4, high: 3, medium: 2, low: 1};

function average(values) { return values.length ? Math.round(values.reduce((sum, value) => sum + value, 0) / values.length) : null; }

function topicMap() {
  const map = new Map();
  for (const section of state.curriculum?.sections || []) for (const domain of section.domains) for (const topic of domain.topics) map.set(topic.id, {...topic, section});
  return map;
}

function showView(view) {
  const dashboard = document.querySelector("#dashboard-view");
  const curriculum = document.querySelector("#curriculum-view");
  const workspace = document.querySelector("#lab-workspace");
  const toWorkspace = !["dashboard", "curriculum"].includes(view);
  dashboard.hidden = view !== "dashboard";
  curriculum.hidden = view !== "curriculum";
  workspace.hidden = !toWorkspace;
  document.querySelectorAll(".nav-link").forEach(item => item.classList.toggle("is-active", item.dataset.view === view));
  if (!toWorkspace) window.scrollTo({top: 0, behavior: "smooth"});
  if (view === "practice") document.querySelector(".study-session")?.setAttribute("open", "");
  if (view === "exam") { document.querySelector(".study-session")?.setAttribute("open", ""); document.querySelector("#exam-start")?.focus(); }
  if (view === "progress") document.querySelector("#mastery-summary")?.scrollIntoView({behavior: "smooth", block: "center"});
}

function renderCurriculumWorkspace() {
  if (!state.curriculum) return;
  const sections = state.curriculum.sections;
  if (!state.selectedCurriculumSection || !sections.some(section => section.id === state.selectedCurriculumSection)) state.selectedCurriculumSection = sections.at(-1)?.id || sections[0]?.id;
  const section = sections.find(item => item.id === state.selectedCurriculumSection);
  const topics = section.domains.flatMap(domain => domain.topics);
  if (!state.selectedTopic || !topics.some(topic => topic.id === state.selectedTopic)) state.selectedTopic = topics[0]?.id;
  const selected = topics.find(topic => topic.id === state.selectedTopic);
  const skills = state.progress.skills || [];
  const sectionValues = skills.filter(skill => topics.some(topic => topic.id === skill.topic_id)).map(skill => Number(skill.mastery));
  const sectionList = document.querySelector("#curriculum-section-list");
  sectionList.replaceChildren(...sections.map((item, index) => { const button = document.createElement("button"); button.type = "button"; button.className = `curriculum-section-button ${item.id === section.id ? "is-selected" : ""}`; const number = document.createElement("b"); number.textContent = index + 1; const title = document.createElement("span"); title.textContent = item.title.replace(/^L1 · /, ""); button.append(number, title); button.addEventListener("click", () => { state.selectedCurriculumSection = item.id; state.selectedTopic = null; renderCurriculumWorkspace(); }); return button; }));
  const summary = document.querySelector("#curriculum-section-summary"); summary.replaceChildren(); const eyebrow = document.createElement("p"); eyebrow.className = "eyebrow"; eyebrow.textContent = "Selected section"; const title = document.createElement("h2"); title.textContent = section.title.replace(/^L1 · /, ""); const description = document.createElement("p"); description.textContent = section.description; const status = document.createElement("span"); status.className = "section-status"; const value = average(sectionValues); status.textContent = value === null ? "No skills assessed in this section yet" : `${value}% assessed mastery across ${sectionValues.length} skill signals`; summary.append(eyebrow, title, description, status);
  const domainList = document.querySelector("#curriculum-domain-list"); domainList.replaceChildren(...section.domains.map(domain => { const card = document.createElement("article"); card.className = "domain-card"; const heading = document.createElement("h3"); heading.textContent = domain.title; card.append(heading); for (const topic of domain.topics) { const button = document.createElement("button"); button.type = "button"; button.textContent = topic.title; button.addEventListener("click", () => { state.selectedTopic = topic.id; renderCurriculumWorkspace(); document.querySelector("#topic-detail").scrollIntoView({behavior:"smooth",block:"nearest"}); }); card.append(button); } return card; }));
  const detail = document.querySelector("#topic-detail"); detail.replaceChildren(); const topicEyebrow = document.createElement("p"); topicEyebrow.className = "eyebrow"; topicEyebrow.textContent = "Topic readiness by mode"; const topicTitle = document.createElement("h2"); topicTitle.textContent = selected.title; const topicDescription = document.createElement("p"); topicDescription.textContent = selected.description; const modeGrid = document.createElement("div"); modeGrid.className = "mode-grid"; for (const mode of Object.keys(MODE_LABELS)) { const card = document.createElement("article"); card.className = "mode-card"; const label = document.createElement("strong"); label.textContent = MODE_LABELS[mode]; const skill = skills.find(item => item.topic_id === selected.id && item.mode === mode); const result = document.createElement("span"); result.textContent = skill ? `${Math.round(skill.mastery)}% mastery · ${skill.attempts} attempts` : "Not yet assessed"; card.append(label, result); const choice = state.exerciseChoices.find(item => item.topic_id === selected.id && item.mode === mode); if (choice) { const button = document.createElement("button"); button.type = "button"; button.textContent = "Practice →"; button.addEventListener("click", async () => { renderExercise(await api(`/api/study-now?topic_id=${encodeURIComponent(selected.id)}&mode=${encodeURIComponent(mode)}`)); showView("practice"); document.querySelector(".study-session")?.scrollIntoView({behavior:"smooth",block:"start"}); }); card.append(button); } else { const planned = document.createElement("small"); planned.className = "planned"; planned.textContent = "Practice content not yet available"; card.append(planned); } modeGrid.append(card); } detail.append(topicEyebrow, topicTitle, topicDescription, modeGrid);
}

function startRecommendedPractice() {
  showView("practice");
  document.querySelector(".study-session")?.scrollIntoView({behavior: "smooth", block: "start"});
  document.querySelector("#exercise-answer")?.focus();
}

function renderDashboard() {
  if (!state.curriculum) return;
  const skills = state.progress.skills || [];
  const byKey = new Map(skills.map(skill => [`${skill.topic_id}:${skill.mode}`, skill]));
  const dimensions = Object.keys(MODE_LABELS).map(mode => ({mode, value: average(skills.filter(skill => skill.mode === mode).map(skill => Number(skill.mastery)))}));
  const overall = average(skills.map(skill => Number(skill.mastery)));
  const assessed = skills.length;
  const ring = document.querySelector("#readiness-ring");
  ring.style.setProperty("--readiness", `${overall || 0}%`);
  document.querySelector("#readiness-value").textContent = overall === null ? "—" : `${overall}%`;
  document.querySelector("#readiness-copy").textContent = overall === null ? "No mastery has been assessed yet. Start with a focused practice to establish a real baseline." : `${assessed} assessed skill${assessed === 1 ? "" : "s"}. Review the dimensions below so one score never hides a weakness.`;
  document.querySelector("#dashboard-reason").textContent = state.exercise?.reason || "Your next recommended practice";

  const dimensionList = document.querySelector("#dimension-list");
  dimensionList.replaceChildren(...dimensions.map(item => {
    const row = document.createElement("div"); row.className = "dimension-row";
    const label = document.createElement("span"); label.textContent = MODE_LABELS[item.mode];
    const meter = document.createElement("div"); meter.className = "meter"; const fill = document.createElement("span"); fill.style.width = `${item.value || 0}%`; meter.append(fill);
    const value = document.createElement("em"); value.textContent = item.value === null ? "—" : `${item.value}%`;
    row.append(label, meter, value); return row;
  }));

  const topics = topicMap();
  const attention = state.exerciseChoices.map(choice => {
    const skill = byKey.get(`${choice.topic_id}:${choice.mode}`); const topic = topics.get(choice.topic_id);
    const mastery = skill ? Number(skill.mastery) : 0; const errors = skill ? Number(skill.recent_error_rate) : 0;
    return {...choice, topic, mastery, errors, score: (100 - mastery) * PRIORITY_SCORE[choice.priority] * (1 + errors)};
  }).sort((a, b) => b.score - a.score).slice(0, 5);
  const attentionList = document.querySelector("#attention-list");
  attentionList.replaceChildren(...attention.map(item => {
    const row = document.createElement("div"); row.className = `attention-item ${item.mastery < 50 ? "low" : ""}`;
    const title = document.createElement("strong"); title.textContent = item.title;
    const meta = document.createElement("span"); meta.textContent = `${MODE_LABELS[item.mode]} · ${item.mastery ? `${item.mastery}% mastery` : "not yet assessed"} · ${item.priority.replace("_", " ")} priority`;
    const button = document.createElement("button"); button.type = "button"; button.textContent = "Practice"; button.addEventListener("click", async () => { renderExercise(await api(`/api/study-now?topic_id=${encodeURIComponent(item.topic_id)}&mode=${encodeURIComponent(item.mode)}`)); startRecommendedPractice(); });
    row.append(title, meta, button); return row;
  }));

  const activities = [...(state.progress.recent_mistakes || [])].slice(0, 5);
  const activityList = document.querySelector("#activity-list");
  if (!activities.length) activityList.replaceChildren(Object.assign(document.createElement("p"), {className: "empty-state", textContent: "Your completed practice and lab history will appear here. Start Study Now to create your first activity."}));
  else activityList.replaceChildren(...activities.map(item => { const row = document.createElement("div"); row.className = "activity-item"; const title = document.createElement("strong"); title.textContent = topics.get(item.topic_id)?.title || item.topic_id; const detail = document.createElement("span"); detail.textContent = `${MODE_LABELS[item.mode]} · review needed · ${item.practiced_at}`; row.append(title, detail); return row; }));

  const cards = document.querySelector("#curriculum-cards");
  cards.replaceChildren(...state.curriculum.sections.map((section, index) => {
    const topicIds = section.domains.flatMap(domain => domain.topics.map(topic => topic.id));
    const values = skills.filter(skill => topicIds.includes(skill.topic_id)).map(skill => Number(skill.mastery)); const value = average(values);
    const card = document.createElement("article"); card.className = "curriculum-card";
    const number = document.createElement("b"); number.textContent = String(index + 1); const title = document.createElement("h3"); title.textContent = section.title.replace(/^L1 · /, ""); const description = document.createElement("p"); description.textContent = section.domains.map(domain => domain.title).slice(0, 3).join(" · "); const status = document.createElement("span"); status.textContent = value === null ? "Not yet assessed" : `${value}% assessed mastery`; const button = document.createElement("button"); button.type = "button"; button.textContent = "Continue →"; button.addEventListener("click", () => { state.selectedCurriculumSection = section.id; state.selectedTopic = null; renderCurriculumWorkspace(); showView("curriculum"); }); card.append(number, title, description, status, button); return card;
  }));
}

function renderReference(query) {
  const normalized = query.trim().toLowerCase();
  const groups = state.reference.categories.map((category) => ({
    ...category,
    commands: category.commands.filter((item) =>
      `${category.title} ${item.command} ${item.description}`.toLowerCase().includes(normalized)
    ),
  })).filter((category) => category.commands.length);

  referenceGroups.replaceChildren(...groups.map((category) => {
    const section = document.createElement("section");
    section.className = "reference-group";
    const heading = document.createElement("h3");
    heading.textContent = category.title;
    const list = document.createElement("div");
    list.className = "reference-list";
    list.replaceChildren(...category.commands.map((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "command-chip";
      button.dataset.command = item.command;
      const command = document.createElement("code");
      command.textContent = item.command;
      const description = document.createElement("span");
      description.textContent = item.description;
      button.append(command, description);
      return button;
    }));
    section.append(heading, list);
    return section;
  }));
  document.querySelector("#reference-empty").hidden = groups.length !== 0;
}

document.querySelector("#reference-open").addEventListener("click", () => {
  referenceSearch.value = "";
  renderReference("");
  referenceDialog.showModal();
  referenceSearch.focus();
});

document.querySelector("#reference-close").addEventListener("click", () => referenceDialog.close());
referenceSearch.addEventListener("input", () => renderReference(referenceSearch.value));
referenceGroups.addEventListener("click", (event) => {
  const button = event.target.closest("[data-command]");
  if (!button) return;
  input.value = button.dataset.command;
  referenceDialog.close();
  input.disabled = false;
  input.focus();
  const placeholder = input.value.match(/<[^>]+>/);
  if (placeholder) input.setSelectionRange(placeholder.index, placeholder.index + placeholder[0].length);
});

labSelect.addEventListener("change", async () => {
  const requestedLab = labSelect.value;
  if (state.busy) {
    labSelect.value = state.labId;
    return;
  }
  await startSession(requestedLab);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.busy || !state.sessionId || input.disabled) return;
  state.busy = true;
  labSelect.disabled = true;
  const command = input.value;
  input.value = "";
  state.history.push(command);
  state.historyIndex = state.history.length;
  state.draft = "";
  appendCommand(state.prompt, command);
  input.disabled = true;

  try {
    const result = await api(`/api/sessions/${state.sessionId}/commands`, {
      method: "POST",
      body: JSON.stringify({ command }),
    });
    if (result.output) appendLine(result.output, result.output.startsWith("%") ? "error-line" : "");
    state.prompt = result.prompt;
    promptLabel.textContent = state.prompt;
    renderCampus(result.campus, result.active);
    if (result.closed) {
      appendLine("Session closed. Reset the lab to continue.", "welcome");
    } else {
      input.disabled = false;
      input.focus();
    }
  } catch (error) {
    appendLine(error.message, "error-line");
    input.disabled = false;
    input.focus();
  } finally {
    state.busy = false;
    labSelect.disabled = false;
  }
});

input.addEventListener("keydown", async (event) => {
  if ((event.key === "?" || event.key === "Tab") && state.sessionId && !state.busy) {
    event.preventDefault();
    state.busy = true;
    labSelect.disabled = true;
    input.disabled = true;
    try {
      const result = await api(`/api/sessions/${state.sessionId}/help`, {method: "POST", body: JSON.stringify({command: input.value})});
      if (event.key === "Tab" && result.matches.length === 1) input.value = result.completed;
      else appendLine(result.output);
    } catch (error) { appendLine(error.message, "error-line"); }
    finally { state.busy = false; labSelect.disabled = false; input.disabled = false; input.focus(); }
  } else if (event.key === "ArrowUp" && state.history.length) {
    event.preventDefault();
    if (state.historyIndex === state.history.length) state.draft = input.value;
    state.historyIndex = Math.max(0, state.historyIndex - 1);
    input.value = state.history[state.historyIndex];
  } else if (event.key === "ArrowDown" && state.history.length) {
    event.preventDefault();
    state.historyIndex = Math.min(state.history.length, state.historyIndex + 1);
    input.value = state.historyIndex === state.history.length ? state.draft : state.history[state.historyIndex];
  } else if (event.ctrlKey && event.key.toLowerCase() === "l") {
    event.preventDefault();
    output.replaceChildren();
  }
});

document.querySelector("#exercise-hints").addEventListener("toggle", event => {
  if (event.currentTarget.open) state.hintsUsed = Math.max(1, state.hintsUsed);
});

document.querySelector("#exercise-form").addEventListener("submit", async event => {
  event.preventDefault();
  if (!state.exercise) return;
  const button = document.querySelector("#exercise-submit");
  button.disabled = true;
  const result = document.querySelector("#exercise-result");
  try {
    const answer = document.querySelector("#exercise-answer").value;
    const attempt = await api(`/api/exercises/${state.exercise.id}/attempts`, {
      method: "POST",
      body: JSON.stringify({variant_id: state.exercise.variant_id, answer, hints_used: state.hintsUsed}),
    });
    result.className = `exercise-result ${attempt.correct ? "correct" : "incorrect"}`;
    result.textContent = `${attempt.correct ? "Correct." : "Not quite."} ${attempt.explanation} Mastery: ${attempt.progress.mastery}% (${attempt.progress.attempts} attempt${attempt.progress.attempts === 1 ? "" : "s"}).`;
    const next = await api("/api/study-now");
    state.progress = await api("/api/progress");
    renderProgress(state.progress);
    renderDashboard();
    renderCurriculumWorkspace();
    window.setTimeout(() => renderExercise(next), 900);
  } catch (error) {
    result.className = "exercise-result incorrect";
    result.textContent = error.message;
    button.disabled = false;
  }
});

document.querySelector("#practice-picker").addEventListener("submit", async event => {
  event.preventDefault();
  const choice = state.exerciseChoices.find(item => item.id === document.querySelector("#practice-choice").value);
  if (!choice) return;
  try {
    renderExercise(await api(`/api/study-now?topic_id=${encodeURIComponent(choice.topic_id)}&mode=${encodeURIComponent(choice.mode)}`));
  } catch (error) { document.querySelector("#exercise-result").textContent = error.message; }
});

document.querySelector("#supporting-lab").addEventListener("click", async event => {
  const labId = event.currentTarget.dataset.labId;
  if (!labId || state.busy) return;
  await startSession(labId);
  document.querySelector(".lab-card").scrollIntoView({behavior: "smooth", block: "start"});
});

document.querySelector("#clear-terminal").addEventListener("click", () => {
  output.replaceChildren();
  input.focus();
});

document.querySelector("#check-work").addEventListener("click", async () => {
  if (state.busy || !state.sessionId) return;
  state.busy = true;
  labSelect.disabled = true;
  const button = document.querySelector("#check-work");
  button.disabled = true;
  try {
    const grade = await api(`/api/sessions/${state.sessionId}/grade`, {
      method: "POST",
      body: "{}",
    });
    const panel = document.querySelector("#grade-panel");
    panel.hidden = false;
    panel.classList.toggle("complete", grade.passed);
    document.querySelector("#grade-title").textContent = grade.passed ? "Lab complete" : "Keep configuring";
    const summary = document.querySelector("#grade-summary");
    summary.hidden = !grade.passed;
    if (grade.passed) summary.textContent = `Repair verified: ${grade.passed_count}/${grade.total_count} state checks passed${grade.process ? `; ${grade.process_passed_count}/${grade.process_total_count} troubleshooting evidence checks recorded.` : "."}`;
    document.querySelector("#progress-label").textContent = `${grade.passed_count} / ${grade.total_count}`;
    const results = document.querySelector("#grade-results");
    results.replaceChildren(...grade.results.map((result) => {
      const item = document.createElement("li");
      item.className = result.passed ? "pass" : "";
      item.textContent = `${result.passed ? "✓" : "○"} ${result.label}`;
      return item;
    }));
    if (grade.process) appendLine(`Troubleshooting evidence: ${grade.process_passed_count} / ${grade.process_total_count}`, "welcome");
  } catch (error) {
    appendLine(error.message, "error-line");
  } finally {
    button.disabled = false;
    state.busy = false;
    labSelect.disabled = false;
  }
});

document.querySelector("#reset-lab").addEventListener("click", async () => {
  if (state.busy || !state.sessionId || !window.confirm("Reset this entire lab and discard its saved configuration?")) return;
  state.busy = true;
  labSelect.disabled = true;
  try {
    const result = await api(`/api/sessions/${state.sessionId}/reset`, {
      method: "POST",
      body: "{}",
    });
    state.prompt = result.prompt;
    renderCampus(result.campus, result.active);
    state.history = [];
    state.historyIndex = 0;
    promptLabel.textContent = state.prompt;
    output.replaceChildren();
    appendLine("Lab reset. The switch is back at its starting state.", "welcome");
    document.querySelector("#grade-panel").hidden = true;
    document.querySelector("#progress-label").textContent = "Not checked";
    input.disabled = false;
    input.focus();
  } catch (error) {
    appendLine(error.message, "error-line");
  } finally {
    state.busy = false;
    labSelect.disabled = false;
  }
});

function renderCampus(campus, active) {
  document.querySelector("#campus-panel").hidden = !campus;
  document.querySelector("#device-title").textContent = active || "Training switch";
  if (!campus) return;
  document.querySelector("#topology-title").textContent = campus.title || "College access network";
  document.querySelector("#topology-subtitle").textContent = campus.subtitle || "Fictional campus · Layer 2";
  document.querySelector("#topology-limits").textContent = campus.limits || "Same-subnet traffic on this fixed, loop-free topology is simulated. Routing, STP convergence, LACP, MLAG, ACL enforcement, and traffic timing are not modeled. Learning tables clear on configuration changes and server restart. Switch ARP stays empty because no Layer 3 interface participates.";
  document.querySelector("#topology-nodes").replaceChildren(...campus.switches.map(name => {
    const button = document.createElement("button");
    button.className = "node";
    button.type = "button";
    button.dataset.device = name;
    button.setAttribute("aria-pressed", String(name === active));
    button.append(name);
    button.addEventListener("click", () => selectCampusDevice(name));
    return button;
  }));
  document.querySelector("#topology-links").replaceChildren(...campus.links.map(link => {
    const label = document.createElement("span");
    label.textContent = `${link.a} ${link.ap.replace("Ethernet", "Et")} ↔ ${link.b} ${link.bp.replace("Ethernet", "Et")} · ${link.up ? "up" : "down"}`;
    return label;
  }));
  const evidence = document.querySelector("#routing-evidence");
  evidence.hidden = !campus.devices;
  if (campus.devices) {
    document.querySelector("#routing-evidence-cards").replaceChildren(...campus.devices.map(device => {
      const card = document.createElement("article");
      card.className = "routing-evidence-card";
      const heading = document.createElement("h4");
      heading.textContent = device.name;
      const interfaces = document.createElement("p");
      interfaces.textContent = `Interfaces: ${device.interfaces.map(item => `${item.name.replace("Ethernet", "Et")} ${item.addresses.join(", ")} (${item.up ? "up" : "down"})`).join(" · ") || "none"}`;
      const routes = document.createElement("p");
      routes.textContent = `Static routes: ${device.routes.map(route => `${route.prefix} via ${route.next_hop}`).join(" · ") || "none"}`;
      const decisions = document.createElement("p");
      decisions.textContent = `Selected: ${device.decisions.map(route => `${route.destination} → ${route.source} ${route.prefix} (${route.reason})`).join(" · ") || "no remote route"}`;
      card.replaceChildren(heading, interfaces, routes, decisions);
      return card;
    }));
  }
  const hosts = [...campus.hosts].sort((a,b) => a.port.localeCompare(b.port) || a.switch.localeCompare(b.switch));
  document.querySelector("#host-list").replaceChildren(...hosts.map(h => {
    const p = document.createElement("p");
    p.textContent = `${h.id} · ${h.address} · ${h.port}`;
    return p;
  }));
  for (const id of ["ping-source", "ping-destination"]) {
    const select = document.getElementById(id);
    const previous = select.value;
    select.replaceChildren(...campus.hosts.map(h => new Option(h.id, h.id)));
    select.value = campus.hosts.some(h => h.id === previous) ? previous : campus.hosts[id === "ping-source" ? 0 : 1]?.id;
  }
  document.querySelector("#host-arp").textContent = campus.hosts.map(h => `${h.id}: ${Object.entries(h.arp).map(([ip, mac]) => `${ip} → ${mac}`).join(", ") || "No learned entries"}`).join("\n");
}

function renderExam(exam) {
  state.exam = exam;
  const panel = document.querySelector("#exam-panel");
  panel.hidden = false;
  const question = exam.questions[state.examIndex];
  document.querySelector("#exam-progress").textContent = `${state.examIndex + 1} / ${exam.question_count}`;
  document.querySelector("#exam-prompt").textContent = question.prompt;
  document.querySelector("#exam-answer").value = state.examAnswers[state.examIndex] || "";
  document.querySelector("#exam-timer").textContent = `Started ${exam.started_at}. Hints are unavailable; submit every answer for the final review.`;
  document.querySelector("#exam-result").textContent = "";
  document.querySelector("#exam-next").textContent = state.examIndex + 1 === exam.question_count ? "Submit exam" : "Next question";
  document.querySelector("#exam-answer").focus();
}

document.querySelector("#exam-start").addEventListener("click", async () => {
  try { state.examIndex = 0; state.examAnswers = []; renderExam(await api("/api/exam", {method: "POST", body: "{}"})); }
  catch (error) { document.querySelector("#exercise-result").textContent = error.message; }
});

document.querySelector("#exam-next").addEventListener("click", async () => {
  if (!state.exam) return;
  const answer = document.querySelector("#exam-answer").value.trim();
  if (!answer) { document.querySelector("#exam-result").textContent = "Enter an answer before continuing."; return; }
  state.examAnswers[state.examIndex] = answer;
  if (state.examIndex + 1 < state.exam.question_count) { state.examIndex += 1; renderExam(state.exam); return; }
  try {
    const result = await api(`/api/exams/${state.exam.id}/submit`, {method: "POST", body: JSON.stringify({answers: state.examAnswers})});
    const review = document.querySelector("#exam-result");
    review.className = "exercise-result correct";
    review.replaceChildren(document.createTextNode(`Score: ${result.score}/${result.total}. `));
    if (!result.remediation.length) review.append("All covered topics passed.");
    for (const item of result.remediation) {
      const practice = document.createElement("button");
      practice.type = "button";
      practice.className = "secondary-button exam-review-action";
      practice.textContent = `Practice ${item.topic_id} (${item.missed} missed)`;
      practice.addEventListener("click", async () => renderExercise(await api(`/api/study-now?topic_id=${encodeURIComponent(item.topic_id)}&mode=${encodeURIComponent(item.mode)}`)));
      review.append(practice);
      if (item.lab_id) {
        const lab = document.createElement("button");
        lab.type = "button";
        lab.className = "secondary-button exam-review-action";
        lab.textContent = "Open supporting lab";
        lab.addEventListener("click", () => startSession(item.lab_id));
        review.append(lab);
      }
    }
    document.querySelector("#exam-next").disabled = true;
  } catch (error) { document.querySelector("#exam-result").className = "exercise-result incorrect"; document.querySelector("#exam-result").textContent = error.message; }
});

function renderProgress(progress) {
  const mastery = document.querySelector("#mastery-summary");
  mastery.hidden = !progress.skills.length;
  mastery.replaceChildren(...progress.skills.slice(0, 4).map(skill => {
    const item = document.createElement("p");
    item.textContent = `${skill.topic_id} · ${skill.mode}: ${skill.mastery}% (${skill.attempts} attempts)`;
    return item;
  }));
  const mistakes = document.querySelector("#mistake-review");
  mistakes.hidden = !progress.recent_mistakes.length;
  mistakes.replaceChildren(...progress.recent_mistakes.slice(0, 4).map(mistake => {
    const item = document.createElement("p");
    item.textContent = `${mistake.topic_id} · ${mistake.mode}: ${mistake.error_tags.join(", ")}`;
    return item;
  }));
}

function renderExercise(exercise) {
  state.exercise = exercise;
  state.hintsUsed = 0;
  document.querySelector("#study-reason").textContent = exercise.reason;
  document.querySelector("#exercise-mode").textContent = `${exercise.mode} · ${exercise.topic_id}`;
  document.querySelector("#exercise-prompt").textContent = exercise.prompt;
  const labButton = document.querySelector("#supporting-lab");
  labButton.hidden = !exercise.lab_id;
  labButton.dataset.labId = exercise.lab_id || "";
  document.querySelector("#exercise-answer").value = "";
  document.querySelector("#exercise-submit").disabled = false;
  document.querySelector("#exercise-result").textContent = "";
  const hints = document.querySelector("#exercise-hints");
  hints.open = false;
  document.querySelector("#exercise-hint-list").replaceChildren(...exercise.hints.map(hint => {
    const item = document.createElement("li");
    item.textContent = hint;
    return item;
  }));
}

async function selectCampusDevice(device) {
  if (state.busy) return;
  state.busy = true;
  labSelect.disabled = true;
  input.disabled = true;
  try {
    const result = await api(`/api/sessions/${state.sessionId}/campus`, {method: "POST", body: JSON.stringify({device})});
    state.prompt = result.prompt;
    promptLabel.textContent = result.prompt;
    state.history = result.history;
    state.historyIndex = state.history.length;
    renderCampus(result.campus, result.active);
    appendLine(`Console: ${result.active}`, "welcome");
    input.disabled = result.closed;
    input.focus({ preventScroll: true });
  } catch (error) { appendLine(error.message, "error-line"); input.disabled = false; }
  finally { state.busy = false; labSelect.disabled = false; }
}

document.querySelector("#ping-form").addEventListener("submit", async event => {
  event.preventDefault();
  if (state.busy) return;
  state.busy = true;
  labSelect.disabled = true;
  try {
    const result = await api(`/api/sessions/${state.sessionId}/campus`, {method: "POST", body: JSON.stringify({source: document.querySelector("#ping-source").value, destination: document.querySelector("#ping-destination").value})});
    document.querySelector("#ping-result").textContent = result.output;
    const timeline = document.querySelector("#ping-route-timeline");
    timeline.hidden = !result.timeline;
    if (result.timeline) timeline.replaceChildren(...result.timeline.flatMap(item => [Object.assign(document.createElement("p"), {textContent: item.direction}), ...item.routes.map(route => Object.assign(document.createElement("p"), {textContent: `↳ ${route.source} ${route.prefix} via ${route.via} · ${route.reason}`})), ...(item.failure ? [Object.assign(document.createElement("p"), {textContent: `↳ first blocker: ${item.failure}`})] : [])]));
    renderCampus(result.campus, result.active);
  } catch (error) { document.querySelector("#ping-result").textContent = error.message; }
  finally { state.busy = false; labSelect.disabled = false; }
});

function initializeSections() {
  const select = document.querySelector("#section-select");
  select.replaceChildren(...state.sections.map(section => new Option(section.title, section.id)));
  let saved;
  try { saved = localStorage.getItem("arista-study-section"); } catch {}
  if (state.sections.some(section => section.id === saved)) select.value = saved;
  select.addEventListener("change", renderSection);
  renderSection();
}

function renderSection() {
  const id = document.querySelector("#section-select").value;
  const section = state.sections.find(section => section.id === id);
  if (!section) return;
  try { localStorage.setItem("arista-study-section", id); } catch {}
  document.querySelector("#study-title").textContent = section.title;
  document.querySelector("#section-description").textContent = section.description;
  document.querySelector("#section-topics").replaceChildren(...section.topics.map((topic, index) => {
    const card = document.createElement("article");
    card.className = "study-topic";
    const title = document.createElement("h3");
    title.textContent = (index + 1) + ". " + topic.title;
    const description = document.createElement("p");
    description.textContent = topic.description;
    card.append(title, description);
    for (const labId of topic.labs) {
      const lab = state.labs.find(lab => lab.id === labId);
      if (!lab) continue;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary-button study-launch";
      button.textContent = lab.title + " · " + lab.estimated_minutes + " min";
      button.addEventListener("click", async () => {
        if (state.busy) return;
        showView("lab");
        await startSession(lab.id);
        document.querySelector(".lab-card").scrollIntoView({behavior: "smooth", block: "start"});
      });
      card.append(button);
    }
    for (const checkpoint of topic.checkpoints || []) {
      const details = document.createElement("details");
      details.className = "study-checkpoint";
      const summary = document.createElement("summary");
      summary.textContent = checkpoint.question;
      const answer = document.createElement("p");
      answer.textContent = checkpoint.answer;
      details.append(summary, answer);
      card.append(details);
    }
    return card;
  }));
  const sources = document.querySelector("#section-sources");
  sources.replaceChildren(document.createTextNode("Reference reading: "));
  for (const source of section.sources || []) {
    const link = document.createElement("a");
    link.textContent = source.title;
    link.href = source.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    sources.append(link, document.createTextNode(" "));
  }
  sources.hidden = !section.sources?.length;
}

document.querySelectorAll(".nav-link").forEach(button => button.addEventListener("click", () => showView(button.dataset.view)));
document.querySelector("#mobile-menu").addEventListener("click", event => { const sidebar = document.querySelector(".app-sidebar"); const open = sidebar.classList.toggle("is-open"); event.currentTarget.setAttribute("aria-expanded", String(open)); });
document.querySelector("#dashboard-study").addEventListener("click", startRecommendedPractice);
document.querySelector("#curriculum-study").addEventListener("click", startRecommendedPractice);
document.querySelectorAll("[data-action]").forEach(button => button.addEventListener("click", () => {
  const action = button.dataset.action;
  if (action === "study" || action === "practice" || action === "weak") startRecommendedPractice();
  else if (action === "lab") showView("lab");
  else if (action === "curriculum") showView("curriculum");
  else if (action === "progress" || action === "recent") showView("progress");
}));
document.querySelector("#global-search").addEventListener("keydown", event => {
  if (event.key !== "Enter") return;
  const query = event.currentTarget.value.trim().toLowerCase();
  if (!query) return;
  if (state.reference?.categories.some(category => category.commands.some(command => `${command.command} ${command.description}`.toLowerCase().includes(query)))) {
    showView("lab"); referenceDialog.showModal(); referenceSearch.value = query; renderReference(query); return;
  }
  showView("curriculum");
});

initialize();
