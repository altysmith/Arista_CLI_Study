const state = { studyModules: null, studyProgress: {}, selectedCurriculumSection: null, selectedModule: null, curriculumSearch: "" };

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.headers.get("content-type")?.includes("application/json")) throw new Error("Your sign-in may have expired. Refresh this page to sign in again; saved progress will remain.");
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Curriculum request failed");
  return payload;
}

function setConnection(kind, label) {
  const connection = document.querySelector(".connection");
  connection.classList.remove("ready", "error");
  if (kind) connection.classList.add(kind);
  document.querySelector("#connection-label").textContent = label;
}

async function initialize() {
  try {
    const [studyModules, studyProgress, deployment] = await Promise.all([api("/api/study-modules"), api("/api/study-progress"), api("/health")]);
    state.studyModules = studyModules;
    state.studyProgress = studyProgress;
    document.querySelector("#deployment-metadata").textContent = deployment.commit ? `${deployment.commit.slice(0, 7)} · ${deployment.deployed_at || "deployment time unavailable"}` : "Local development build";
    renderDashboard();
    renderSourceCurriculum();
    setConnection("ready", "Curriculum ready");
  } catch (error) {
    setConnection("error", "Curriculum unavailable");
    document.querySelector("#readiness-copy").textContent = error.message;
    document.querySelector("#topic-detail").replaceChildren(Object.assign(document.createElement("p"), { className: "empty-state", textContent: error.message }));
  }
}

function showView(view) {
  document.querySelector("#dashboard-view").hidden = view !== "dashboard";
  document.querySelector("#curriculum-view").hidden = view !== "curriculum";
  document.querySelectorAll(".nav-link").forEach((item) => item.classList.toggle("is-active", item.dataset.view === view));
  document.querySelector(".app-sidebar").classList.remove("is-open");
  document.querySelector("#mobile-menu").setAttribute("aria-expanded", "false");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function emptyModuleProgress(module) {
  return { learn_reviewed: false, flashcards_revealed: [], quiz_answers: module.activities.quiz.map(() => ""), quiz_correct: module.activities.quiz.map(() => false), practical_complete: false, practical_notes: "", mastery_checked: [] };
}

function moduleProgress(module) {
  if (!module.activities) return null;
  const progress = emptyModuleProgress(module);
  const saved = state.studyProgress[module.id] || {};
  for (const key of Object.keys(progress)) if (key in saved) progress[key] = saved[key];
  return progress;
}

function moduleCompletion(module) {
  if (!module.activities) return 0;
  const progress = moduleProgress(module);
  const activities = module.activities;
  const earned = Number(progress.learn_reviewed) + Number(progress.flashcards_revealed.length >= activities.flashcards.length) + Number(progress.quiz_correct.filter(Boolean).length >= activities.quiz.length) + Number(progress.practical_complete) + Number(progress.mastery_checked.length >= activities.mastery.length);
  return earned * 20;
}

function allModules() {
  return state.studyModules?.sections.flatMap((section) => section.modules.map((module) => ({ section, module }))) || [];
}

function openModule(section, module) {
  state.selectedCurriculumSection = section.id;
  state.selectedModule = module.id;
  state.curriculumSearch = "";
  document.querySelector("#global-search").value = "";
  renderSourceCurriculum();
  showView("curriculum");
  document.querySelector("#topic-detail").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderDashboard() {
  const sections = state.studyModules.sections;
  const interactive = allModules().filter(({ module }) => module.activities);
  const completed = interactive.filter(({ module }) => moduleCompletion(module) === 100).length;
  const progress = interactive.length ? Math.round(interactive.reduce((sum, { module }) => sum + moduleCompletion(module), 0) / interactive.length) : 0;
  const next = interactive.find(({ module }) => moduleCompletion(module) < 100) || interactive[0];
  document.querySelector("#readiness-ring").style.setProperty("--readiness", `${progress}%`);
  document.querySelector("#readiness-value").textContent = `${progress}%`;
  document.querySelector("#readiness-copy").textContent = interactive.length ? `${completed} of ${interactive.length} interactive modules complete. The remaining sections stay available as supplied reference material while their activities are built.` : "Your supplied curriculum is ready to browse.";
  document.querySelector("#dashboard-reason").textContent = next ? `Continue ${next.module.number}. ${next.module.title}` : "Browse all five curriculum sections";
  document.querySelector("#dashboard-study").onclick = () => next ? openModule(next.section, next.module) : showView("curriculum");
  document.querySelector("#curriculum-cards").replaceChildren(...sections.map((section, index) => {
    const card = document.createElement("article");
    card.className = "curriculum-card";
    const sectionInteractive = section.modules.filter((module) => module.activities);
    const sectionComplete = section.modules.filter((module) => moduleCompletion(module) === 100).length;
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Open section →";
    button.addEventListener("click", () => openModule(section, section.modules[0]));
    card.append(Object.assign(document.createElement("b"), { textContent: String(index + 1) }), Object.assign(document.createElement("h3"), { textContent: section.title }), Object.assign(document.createElement("p"), { textContent: `${section.modules.length} supplied lessons and labs` }), Object.assign(document.createElement("span"), { textContent: sectionInteractive.length ? `${sectionComplete} of ${sectionInteractive.length} interactive modules complete` : "Reference lessons ready" }), button);
    return card;
  }));
}

function renderSourceCurriculum() {
  if (!state.studyModules) return;
  const sections = state.studyModules.sections;
  if (!state.selectedCurriculumSection || !sections.some((section) => section.id === state.selectedCurriculumSection)) state.selectedCurriculumSection = sections[0].id;
  const section = sections.find((item) => item.id === state.selectedCurriculumSection);
  if (!state.selectedModule || !section.modules.some((module) => module.id === state.selectedModule)) state.selectedModule = section.modules[0].id;
  const selected = section.modules.find((module) => module.id === state.selectedModule);
  document.querySelector("#curriculum-section-list").replaceChildren(...sections.map((item, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `curriculum-section-button ${item.id === section.id ? "is-selected" : ""}`;
    button.append(Object.assign(document.createElement("b"), { textContent: index + 1 }), Object.assign(document.createElement("span"), { textContent: item.title }));
    button.addEventListener("click", () => { state.selectedCurriculumSection = item.id; state.selectedModule = item.modules[0].id; state.curriculumSearch = ""; document.querySelector("#global-search").value = ""; renderSourceCurriculum(); });
    return button;
  }));
  const completed = section.modules.filter((module) => moduleCompletion(module) === 100).length;
  document.querySelector("#curriculum-section-summary").replaceChildren(Object.assign(document.createElement("p"), { className: "eyebrow", textContent: "Authoritative Drive curriculum" }), Object.assign(document.createElement("h2"), { textContent: section.title }), Object.assign(document.createElement("p"), { textContent: `${section.modules.length} lessons and labs · ${completed} complete. Choose any module; numeric order is recommended, not required.` }));
  const card = document.createElement("article");
  card.className = "domain-card module-index";
  card.append(Object.assign(document.createElement("h3"), { textContent: state.curriculumSearch ? "Search results" : "Lessons and labs" }));
  const normalizedSearch = state.curriculumSearch.trim().toLowerCase();
  const visibleModules = normalizedSearch ? allModules().filter(({ module }) => `${module.title} ${module.markdown}`.toLowerCase().includes(normalizedSearch)) : section.modules.map((module) => ({ section, module }));
  if (!visibleModules.length) card.append(Object.assign(document.createElement("p"), { className: "empty-state", textContent: "No curriculum modules match your search." }));
  visibleModules.forEach(({ section: itemSection, module }) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `${module.id === selected.id ? "is-selected " : ""}${moduleCompletion(module) === 100 ? "is-complete" : ""}`;
    button.textContent = `${moduleCompletion(module) === 100 ? "✓ " : ""}${normalizedSearch ? `${itemSection.title} · ` : ""}${module.number}. ${module.title}${module.kind === "lab" ? " · Lab" : ""}`;
    button.addEventListener("click", () => openModule(itemSection, module));
    card.append(button);
  });
  document.querySelector("#curriculum-domain-list").replaceChildren(card);
  const detail = document.querySelector("#topic-detail");
  const meter = document.createElement("div");
  meter.className = "module-progress";
  meter.append(Object.assign(document.createElement("span"), { style: `width:${moduleCompletion(selected)}%` }));
  detail.replaceChildren(Object.assign(document.createElement("p"), { className: "eyebrow", textContent: `${section.title} · ${selected.kind}` }), Object.assign(document.createElement("h2"), { textContent: `${selected.number}. ${selected.title}` }), meter, Object.assign(document.createElement("p"), { className: "module-progress-label", textContent: selected.activities ? `${moduleCompletion(selected)}% complete across Learn, Flashcards, Quiz, Exercise, and Mastery` : "Supplied curriculum reference" }));
  if (selected.activities) detail.append(renderInteractiveModule(selected, section));
  else detail.append(renderMarkdownContent(selected.markdown), Object.assign(document.createElement("p"), { className: "planned", textContent: "This supplied lesson is ready for study. Its interactive activities will be added as this section is completed." }));
}

async function saveModuleProgress(module, progress, rerender = true) {
  state.studyProgress[module.id] = progress;
  if (rerender) { renderSourceCurriculum(); renderDashboard(); }
  try { state.studyProgress[module.id] = await api("/api/study-progress", { method: "POST", body: JSON.stringify({ module_id: module.id, state: progress }) }); }
  catch (error) { window.alert(`Progress was not saved: ${error.message}`); }
}

function renderInteractiveModule(module, section) {
  const activities = module.activities;
  const progress = moduleProgress(module);
  const wrapper = document.createElement("div");
  wrapper.className = "interactive-module";
  const learn = activityPanel("Learn", "Read the supplied lesson before marking it reviewed.");
  learn.append(renderMarkdownContent(activities.learn));
  learn.append(actionButton(progress.learn_reviewed ? "✓ Learn reviewed" : "Mark Learn reviewed", () => { progress.learn_reviewed = !progress.learn_reviewed; saveModuleProgress(module, progress); }));
  const flashcards = activityPanel("Flashcards", "Answers stay hidden until you reveal each card.");
  activities.flashcards.forEach((card, index) => {
    const revealed = progress.flashcards_revealed.includes(index);
    const item = document.createElement("button");
    item.type = "button";
    item.className = `flashcard ${revealed ? "is-revealed" : ""}`;
    item.append(Object.assign(document.createElement("strong"), { textContent: card.question }), Object.assign(document.createElement("span"), { textContent: revealed ? card.answer : "Reveal answer" }));
    item.addEventListener("click", () => { if (!progress.flashcards_revealed.includes(index)) progress.flashcards_revealed.push(index); saveModuleProgress(module, progress); });
    flashcards.append(item);
  });
  const quiz = activityPanel("Knowledge Quiz", "Answer from memory, compare with the lesson, then assess your response.");
  activities.quiz.forEach((question, index) => {
    const item = document.createElement("article");
    item.className = `quiz-item ${progress.quiz_correct[index] ? "is-correct" : ""}`;
    item.append(Object.assign(document.createElement("h4"), { textContent: `${index + 1}. ${question}` }));
    const answer = document.createElement("textarea");
    answer.rows = 3;
    answer.value = progress.quiz_answers[index] || "";
    answer.placeholder = "Write your answer before checking the source…";
    const review = document.createElement("details");
    review.className = "quiz-source-review";
    review.append(Object.assign(document.createElement("summary"), { textContent: "Check against the Learn content" }), renderMarkdownContent(activities.learn));
    const correct = actionButton("My answer is correct", () => { progress.quiz_answers[index] = answer.value; progress.quiz_correct[index] = true; saveModuleProgress(module, progress); });
    correct.disabled = !answer.value.trim();
    answer.addEventListener("input", () => { progress.quiz_answers[index] = answer.value; correct.disabled = !answer.value.trim(); });
    answer.addEventListener("change", () => saveModuleProgress(module, progress, false));
    const controls = document.createElement("div");
    controls.className = "quiz-controls";
    controls.append(correct, actionButton("Retry this question", () => { progress.quiz_correct[index] = false; saveModuleProgress(module, progress); }));
    item.append(answer, review, controls);
    quiz.append(item);
  });
  const practical = activityPanel("Practical Exercise", "Complete the supplied task and keep optional notes as evidence.");
  practical.append(renderMarkdownContent(activities.practical));
  const notes = document.createElement("textarea");
  notes.rows = 4;
  notes.placeholder = "Optional exercise notes…";
  notes.value = progress.practical_notes;
  notes.addEventListener("input", () => { progress.practical_notes = notes.value; });
  notes.addEventListener("change", () => saveModuleProgress(module, progress, false));
  const practicalLabel = document.createElement("label");
  practicalLabel.className = "mastery-item";
  const practicalCheck = document.createElement("input");
  practicalCheck.type = "checkbox";
  practicalCheck.checked = progress.practical_complete;
  practicalCheck.addEventListener("change", () => { progress.practical_notes = notes.value; progress.practical_complete = practicalCheck.checked; saveModuleProgress(module, progress); });
  practicalLabel.append(practicalCheck, document.createTextNode("I completed this practical exercise"));
  practical.append(notes, practicalLabel);
  const mastery = activityPanel("Mastery Check", "Check each outcome only when you can perform it without relying on the lesson.");
  activities.mastery.forEach((text, index) => {
    const label = document.createElement("label");
    label.className = "mastery-item";
    const check = document.createElement("input");
    check.type = "checkbox";
    check.checked = progress.mastery_checked.includes(index);
    check.addEventListener("change", () => { progress.mastery_checked = check.checked ? [...new Set([...progress.mastery_checked, index])] : progress.mastery_checked.filter((item) => item !== index); saveModuleProgress(module, progress); });
    label.append(check, document.createTextNode(text));
    mastery.append(label);
  });
  const navigation = document.createElement("nav");
  navigation.className = "module-navigation";
  const index = section.modules.findIndex((item) => item.id === module.id);
  if (index > 0) navigation.append(actionButton("← Previous module", () => openModule(section, section.modules[index - 1])));
  if (index < section.modules.length - 1) navigation.append(actionButton("Next module →", () => openModule(section, section.modules[index + 1])));
  wrapper.append(learn, flashcards, quiz, practical, mastery, navigation);
  return wrapper;
}

function activityPanel(title, description) {
  const panel = document.createElement("section");
  panel.className = "module-activity";
  panel.append(Object.assign(document.createElement("h3"), { textContent: title }), Object.assign(document.createElement("p"), { className: "activity-guide", textContent: description }));
  return panel;
}

function actionButton(label, handler) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "secondary-button";
  button.textContent = label;
  button.addEventListener("click", handler);
  return button;
}

function appendInlineMarkdown(element, value) {
  const parts = value.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
  for (const part of parts) {
    if (part.startsWith("`") && part.endsWith("`")) element.append(Object.assign(document.createElement("code"), { textContent: part.slice(1, -1) }));
    else if (part.startsWith("**") && part.endsWith("**")) element.append(Object.assign(document.createElement("strong"), { textContent: part.slice(2, -2) }));
    else element.append(document.createTextNode(part));
  }
}

function renderMarkdownContent(markdown) {
  const content = document.createElement("div");
  content.className = "module-markdown";
  const lines = markdown.split("\n");
  let list = null;
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (line.startsWith("```")) {
      const language = line.slice(3);
      const values = [];
      while (++index < lines.length && !lines[index].startsWith("```")) values.push(lines[index]);
      const pre = document.createElement("pre");
      const code = document.createElement("code");
      code.className = language ? `language-${language}` : "";
      code.textContent = values.join("\n");
      pre.append(code);
      content.append(pre);
      list = null;
      continue;
    }
    if (line.startsWith("|") && lines[index + 1]?.match(/^\|[-:| ]+\|$/)) {
      const table = document.createElement("table");
      const header = document.createElement("tr");
      line.split("|").slice(1, -1).forEach((value) => { const cell = document.createElement("th"); appendInlineMarkdown(cell, value.trim()); header.append(cell); });
      const head = document.createElement("thead");
      head.append(header);
      table.append(head);
      index += 1;
      const body = document.createElement("tbody");
      while (lines[index + 1]?.startsWith("|")) {
        index += 1;
        const row = document.createElement("tr");
        lines[index].split("|").slice(1, -1).forEach((value) => { const cell = document.createElement("td"); appendInlineMarkdown(cell, value.trim()); row.append(cell); });
        body.append(row);
      }
      table.append(body);
      content.append(table);
      list = null;
      continue;
    }
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    const item = line.match(/^[-*]\s+(.+)$/);
    const ordered = line.match(/^\d+\.\s+(.+)$/);
    if (heading) {
      list = null;
      const element = document.createElement(`h${Math.min(heading[1].length + 2, 5)}`);
      appendInlineMarkdown(element, heading[2]);
      content.append(element);
    } else if (item || ordered) {
      const tag = ordered ? "OL" : "UL";
      if (!list || list.tagName !== tag) { list = document.createElement(tag.toLowerCase()); content.append(list); }
      const entry = document.createElement("li");
      appendInlineMarkdown(entry, (item || ordered)[1]);
      list.append(entry);
    } else if (line.trim()) {
      list = null;
      const paragraph = document.createElement("p");
      appendInlineMarkdown(paragraph, line.trim());
      content.append(paragraph);
    }
  }
  return content;
}

document.querySelectorAll(".nav-link").forEach((button) => button.addEventListener("click", () => showView(button.dataset.view)));
document.querySelectorAll("[data-action='curriculum']").forEach((button) => button.addEventListener("click", () => showView("curriculum")));
document.querySelector("#curriculum-dashboard").addEventListener("click", () => showView("dashboard"));
document.querySelector("#mobile-menu").addEventListener("click", (event) => { const sidebar = document.querySelector(".app-sidebar"); const open = sidebar.classList.toggle("is-open"); event.currentTarget.setAttribute("aria-expanded", String(open)); });
document.querySelector("#global-search").addEventListener("input", (event) => {
  state.curriculumSearch = event.currentTarget.value.trim();
  if (state.curriculumSearch) { renderSourceCurriculum(); showView("curriculum"); }
  else if (!document.querySelector("#curriculum-view").hidden) renderSourceCurriculum();
});
document.querySelector("#global-search").addEventListener("keydown", (event) => {
  if (event.key !== "Enter" || !state.curriculumSearch) return;
  const match = allModules().find(({ module }) => `${module.title} ${module.markdown}`.toLowerCase().includes(state.curriculumSearch.toLowerCase()));
  if (match) openModule(match.section, match.module);
});

initialize();
