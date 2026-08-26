const state = {
  sessionId: null,
  prompt: "switch>",
  history: [],
  historyIndex: 0,
  draft: "",
};

const output = document.querySelector("#terminal-output");
const form = document.querySelector("#terminal-form");
const input = document.querySelector("#command-input");
const promptLabel = document.querySelector("#prompt");
const connection = document.querySelector(".connection");
const connectionLabel = document.querySelector("#connection-label");

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
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

async function startSession() {
  try {
    const labs = await api("/api/labs");
    const session = await api("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ lab_id: labs.labs[0].id }),
    });
    state.sessionId = session.session_id;
    state.prompt = session.prompt;
    promptLabel.textContent = state.prompt;
    renderLab(session.lab);
    appendLine("Arista Network Foundations Simulator — Browser Lab", "welcome");
    appendLine("Type ? for contextual help. Complete the objectives, then check your work.", "welcome");
    appendLine("");
    setConnection("ready", "Simulator ready");
    input.focus();
  } catch (error) {
    setConnection("error", "Simulator unavailable");
    appendLine(error.message, "error-line");
    input.disabled = true;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
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
  }
});

input.addEventListener("keydown", (event) => {
  if (event.key === "ArrowUp" && state.history.length) {
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

document.querySelector("#clear-terminal").addEventListener("click", () => {
  output.replaceChildren();
  input.focus();
});

document.querySelector("#check-work").addEventListener("click", async () => {
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
    document.querySelector("#progress-label").textContent = `${grade.passed_count} / ${grade.total_count}`;
    const results = document.querySelector("#grade-results");
    results.replaceChildren(...grade.results.map((result) => {
      const item = document.createElement("li");
      item.className = result.passed ? "pass" : "";
      item.textContent = `${result.passed ? "✓" : "○"} ${result.label}`;
      return item;
    }));
  } catch (error) {
    appendLine(error.message, "error-line");
  } finally {
    button.disabled = false;
  }
});

document.querySelector("#reset-lab").addEventListener("click", async () => {
  if (!window.confirm("Reset this switch and discard the current lab configuration?")) return;
  try {
    const result = await api(`/api/sessions/${state.sessionId}/reset`, {
      method: "POST",
      body: "{}",
    });
    state.prompt = result.prompt;
    state.history = [];
    state.historyIndex = 0;
    promptLabel.textContent = state.prompt;
    output.replaceChildren();
    appendLine("Lab reset. The switch is back at its starting state.", "welcome");
    document.querySelector("#grade-panel").hidden = true;
    document.querySelector("#progress-label").textContent = "0 / 0";
    input.disabled = false;
    input.focus();
  } catch (error) {
    appendLine(error.message, "error-line");
  }
});

startSession();
