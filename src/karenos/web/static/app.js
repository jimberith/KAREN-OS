const messagesElement = document.getElementById("messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const typing = document.getElementById("typing-indicator");
const toast = document.getElementById("toast");
const statusText = document.getElementById("system-status");
const providerText = document.getElementById("provider-name");
const aiState = document.getElementById("ai-state");
const deviceState = document.getElementById("device-state");
const deviceLed = document.getElementById("device-led");
const sessionId = getSessionId();

let accessCode = sessionStorage.getItem("karenAccessCode") || "";
let agentUrl = localStorage.getItem("karenAgentUrl") || "http://127.0.0.1:8765";
let agentToken = localStorage.getItem("karenAgentToken") || "";
let agentConnected = false;
let busy = false;
let speakReplies = false;
let recognition = null;
let listening = false;
let cameraStream = null;

function getSessionId() {
  let id = localStorage.getItem("karenSessionId");
  if (!id) {
    id = window.crypto?.randomUUID
      ? window.crypto.randomUUID()
      : "karen-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2);
    localStorage.setItem("karenSessionId", id);
  }
  return id;
}

function notify(message, duration = 3000) {
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(notify.timer);
  notify.timer = window.setTimeout(() => toast.classList.remove("show"), duration);
}

function setBusy(value) {
  busy = value;
  typing.hidden = !value;
  sendButton.disabled = value;
  input.disabled = value;
}

function setProviderStatus(payload) {
  const name = String(payload.provider_name || "AI PROVIDER").toUpperCase();
  providerText.textContent = name;
  aiState.textContent = payload.ai_ready ? "READY" : "NOT CONFIGURED";
  statusText.textContent = payload.ai_ready ? "SYSTEM READY" : "SETUP REQUIRED";
  document.querySelector(".system-pulse").classList.toggle("warning", !payload.ai_ready);
}

function showAuth(message = "") {
  document.getElementById("auth-modal").hidden = false;
  document.getElementById("auth-error").textContent = message;
  document.getElementById("access-code").focus();
}

function headers(json = false) {
  const result = {};
  if (json) result["Content-Type"] = "application/json";
  if (accessCode) result["X-Karen-Access-Code"] = accessCode;
  return result;
}

async function api(path, options = {}) {
  const isForm = typeof FormData !== "undefined" && options.body instanceof FormData;
  const response = await fetch(path, {
    ...options,
    headers: { ...headers(!isForm && options.body !== undefined), ...(options.headers || {}) }
  });
  const payload = await response.json().catch(() => ({}));
  if (response.status === 401 && payload.detail === "Access code is incorrect.") {
    sessionStorage.removeItem("karenAccessCode");
    accessCode = "";
    showAuth("The app access code was rejected.");
  }
  if (!response.ok) throw new Error(payload.detail || "Request failed (" + response.status + ").");
  return payload;
}

function scrollMessages() {
  messagesElement.scrollTop = messagesElement.scrollHeight;
}

function makeMessage(role, text, extra = {}) {
  const article = document.createElement("article");
  article.className = "message " + (role === "user" ? "user-message" : "assistant-message");
  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.textContent = role === "user" ? "Y" : "K";
  const wrapper = document.createElement("div");
  wrapper.className = "message-content";
  const author = document.createElement("div");
  author.className = "message-author";
  const name = document.createElement("span");
  name.textContent = role === "user" ? "YOU" : "KAREN";
  const time = document.createElement("span");
  time.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  author.append(name, time);
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = text;
  wrapper.append(author, bubble);

  if (extra.imageUrl) {
    const image = document.createElement("img");
    image.className = "generated-image";
    image.src = extra.imageUrl;
    image.alt = "KAREN generated image";
    image.loading = "lazy";
    wrapper.append(image);
  }

  if (Array.isArray(extra.sources) && extra.sources.length) {
    const sourceBox = document.createElement("div");
    sourceBox.className = "source-list";
    const sourceTitle = document.createElement("div");
    sourceTitle.className = "source-heading";
    sourceTitle.textContent = "SOURCES";
    sourceBox.append(sourceTitle);
    extra.sources.slice(0, 6).forEach(source => {
      if (!source.url || !/^https?:\/\//i.test(source.url)) return;
      const link = document.createElement("a");
      link.href = source.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = source.title || source.url;
      sourceBox.append(link);
    });
    wrapper.append(sourceBox);
  }

  if (extra.action) wrapper.append(makeActionCard(extra.action));
  article.append(avatar, wrapper);
  messagesElement.append(article);
  scrollMessages();
  return article;
}

function makeActionCard(action) {
  const card = document.createElement("div");
  card.className = "action-card";
  const heading = document.createElement("strong");
  heading.textContent = action.label || "Device action";
  const note = document.createElement("p");
  note.textContent = "This command will run on your own computer through the local companion. Nothing is executed until you confirm.";
  const controls = document.createElement("div");
  controls.className = "action-controls";
  const confirm = document.createElement("button");
  confirm.className = "primary-button compact";
  confirm.type = "button";
  confirm.textContent = "CONFIRM ON THIS DEVICE";
  const cancel = document.createElement("button");
  cancel.className = "secondary-button compact";
  cancel.type = "button";
  cancel.textContent = "CANCEL";
  confirm.addEventListener("click", async () => {
    confirm.disabled = true;
    confirm.textContent = "CONNECTING...";
    try {
      const result = await runLocalAction(action);
      note.textContent = result.message || JSON.stringify(result);
      confirm.textContent = "COMPLETED";
      cancel.remove();
    } catch (error) {
      note.textContent = error.message;
      confirm.disabled = false;
      confirm.textContent = "RETRY";
    }
  });
  cancel.addEventListener("click", () => {
    card.replaceChildren();
    const cancelled = document.createElement("p");
    cancelled.textContent = "Action cancelled. Nothing was executed.";
    card.append(cancelled);
  });
  controls.append(confirm, cancel);
  card.append(heading, note, controls);
  return card;
}

async function initialize() {
  try {
    const status = await api("/api/status");
    setProviderStatus(status);
    if (status.access_protected) {
      if (accessCode) {
        try {
          await api("/api/auth/check", { method: "POST" });
          document.getElementById("auth-modal").hidden = true;
        } catch {
          showAuth();
          return;
        }
      } else {
        showAuth();
        return;
      }
    } else {
      document.getElementById("auth-modal").hidden = true;
      sessionStorage.removeItem("karenAccessCode");
      accessCode = "";
    }
    await loadHistory();
    await connectLocalAgent(false);
  } catch (error) {
    statusText.textContent = "SERVER OFFLINE";
    aiState.textContent = "UNAVAILABLE";
    notify(error.message, 5000);
  }
}

async function loadHistory() {
  const result = await api("/api/history/" + encodeURIComponent(sessionId));
  messagesElement.replaceChildren();
  if (!result.messages?.length) {
    makeMessage("assistant", "I'm ready. Ask a question, request a web search, show me an image, or ask me to perform an approved action on your connected device.");
    return;
  }
  result.messages.forEach(message => makeMessage(message.role, message.content));
}

async function sendMessage(text) {
  const prompt = text.trim();
  if (!prompt || busy) return;
  makeMessage("user", prompt);
  input.value = "";
  input.style.height = "auto";
  setBusy(true);
  try {
    const result = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        messages: [{ role: "user", content: prompt }]
      })
    });
    makeMessage("assistant", result.reply || "No response was returned.", {
      sources: result.sources,
      imageUrl: result.image_url,
      action: result.action
    });
    if (speakReplies && result.reply) speak(result.reply);
  } catch (error) {
    makeMessage("assistant", "KAREN could not complete that request: " + error.message);
  } finally {
    setBusy(false);
    scrollMessages();
    input.focus();
  }
}

form.addEventListener("submit", event => {
  event.preventDefault();
  sendMessage(input.value);
});

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 150) + "px";
});

input.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

document.querySelectorAll(".quick-chip[data-prompt]").forEach(button => {
  button.addEventListener("click", () => {
    input.value = button.dataset.prompt;
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
  });
});

document.getElementById("quick-vision").addEventListener("click", openCamera);
document.getElementById("quick-device").addEventListener("click", () => openModal("settings-modal"));

document.getElementById("clear-chat").addEventListener("click", async () => {
  if (!window.confirm("Clear this conversation? Saved memory notes will remain.")) return;
  try {
    await api("/api/history/" + encodeURIComponent(sessionId), { method: "DELETE" });
    messagesElement.replaceChildren();
    makeMessage("assistant", "Conversation cleared. Your saved memory notes are still available.");
  } catch (error) { notify(error.message); }
});

function openModal(id) {
  document.getElementById(id).hidden = false;
}
function closeModal(id) {
  document.getElementById(id).hidden = true;
  if (id === "camera-modal") stopCamera();
}
document.querySelectorAll("[data-close]").forEach(button => {
  button.addEventListener("click", () => closeModal(button.dataset.close));
});
document.querySelectorAll(".modal-overlay").forEach(overlay => {
  overlay.addEventListener("click", event => {
    if (event.target === overlay && overlay.id !== "auth-modal") closeModal(overlay.id);
  });
});

document.getElementById("settings-button").addEventListener("click", () => {
  document.getElementById("agent-url").value = agentUrl;
  document.getElementById("agent-token").value = agentToken;
  openModal("settings-modal");
});
document.getElementById("memory-button").addEventListener("click", async () => {
  openModal("memory-modal");
  await refreshMemory();
});
document.getElementById("dashboard-button").addEventListener("click", async () => {
  openModal("dashboard-modal");
  await refreshDashboard();
});
document.getElementById("save-agent").addEventListener("click", async () => {
  agentUrl = document.getElementById("agent-url").value.trim().replace(/\/$/, "");
  agentToken = document.getElementById("agent-token").value.trim();
  localStorage.setItem("karenAgentUrl", agentUrl);
  localStorage.setItem("karenAgentToken", agentToken);
  await connectLocalAgent(true);
});

async function connectLocalAgent(showMessage = true) {
  if (!agentToken) {
    updateDeviceState(false);
    return false;
  }
  try {
    const health = await fetch(agentUrl + "/health", { cache: "no-store" });
    if (!health.ok) throw new Error("Local agent is not responding.");
    const response = await fetch(agentUrl + "/api/status", {
      headers: { "X-Karen-Agent-Token": agentToken },
      cache: "no-store"
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail || "Local agent authorization failed.");
    agentConnected = true;
    updateDeviceState(true);
    if (showMessage) notify("KAREN connected to your local device.");
    return true;
  } catch (error) {
    agentConnected = false;
    updateDeviceState(false);
    const status = document.getElementById("agent-connect-status");
    if (status) status.textContent = error.message + " Check browser local-network permission.";
    if (showMessage) notify(error.message + " Check local agent and browser permission.", 5000);
    return false;
  }
}

function updateDeviceState(connected) {
  deviceState.textContent = connected ? "CONNECTED" : "NOT CONNECTED";
  deviceLed.classList.toggle("active", connected);
  document.getElementById("metric-bridge").textContent = connected ? "ONLINE" : "OFFLINE";
  document.getElementById("agent-connect-status").textContent = connected ? "Connected to this computer." : "Not connected.";
}

async function runLocalAction(action) {
  if (!agentToken) throw new Error("Connect the local agent in Settings first.");
  if (!agentConnected && !(await connectLocalAgent(false))) {
    throw new Error("Local agent unavailable. Start karenos-agent on this computer and reconnect.");
  }
  const response = await fetch(agentUrl + "/api/actions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Karen-Agent-Token": agentToken
    },
    body: JSON.stringify({ action: action.name, target: action.target, confirmed: true })
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.detail || "The local action failed.");
  if (action.name === "system_status") renderDashboardMetrics(result);
  return result;
}

function renderDashboardMetrics(result) {
  document.getElementById("metric-bridge").textContent = "ONLINE";
  document.getElementById("metric-cpu").textContent = Number(result.cpu_percent).toFixed(0) + "%";
  document.getElementById("metric-memory").textContent = Number(result.memory_percent).toFixed(0) + "%";
  document.getElementById("metric-battery").textContent =
    result.battery_percent == null ? "N/A" : Math.round(result.battery_percent) + "%";
  document.getElementById("dashboard-note").textContent = result.platform || "Local device telemetry received.";
}

async function refreshDashboard() {
  if (!agentToken) {
    document.getElementById("dashboard-note").textContent = "Connect the local companion in Settings to read this computer's CPU, RAM, battery and disk information.";
    return;
  }
  try {
    const response = await fetch(agentUrl + "/api/status", {
      headers: { "X-Karen-Agent-Token": agentToken },
      cache: "no-store"
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Cannot read local device status.");
    agentConnected = true;
    updateDeviceState(true);
    renderDashboardMetrics(result);
  } catch (error) {
    updateDeviceState(false);
    document.getElementById("dashboard-note").textContent = error.message;
  }
}
document.getElementById("refresh-dashboard").addEventListener("click", refreshDashboard);

async function refreshMemory() {
  const list = document.getElementById("memory-list");
  list.replaceChildren();
  try {
    const result = await api("/api/memory?session_id=" + encodeURIComponent(sessionId));
    if (!result.notes?.length) {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.textContent = "No saved notes yet. Use “Remember that…” in the command box.";
      list.append(empty);
      return;
    }
    result.notes.forEach(note => {
      const item = document.createElement("div");
      item.className = "memory-item";
      const body = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = note.title;
      const content = document.createElement("p");
      content.textContent = note.content;
      body.append(title, content);
      const remove = document.createElement("button");
      remove.className = "secondary-button compact";
      remove.type = "button";
      remove.textContent = "DELETE";
      remove.addEventListener("click", async () => {
        try {
          await api("/api/memory/" + note.id + "?session_id=" + encodeURIComponent(sessionId), { method: "DELETE" });
          await refreshMemory();
        } catch (error) { notify(error.message); }
      });
      item.append(body, remove);
      list.append(item);
    });
  } catch (error) { list.textContent = error.message; }
}

document.getElementById("memory-form").addEventListener("submit", async event => {
  event.preventDefault();
  const content = document.getElementById("memory-content-input").value.trim();
  if (!content) return;
  try {
    await api("/api/memory", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        title: document.getElementById("memory-title-input").value.trim(),
        content
      })
    });
    document.getElementById("memory-form").reset();
    await refreshMemory();
    notify("Memory saved.");
  } catch (error) { notify(error.message); }
});

document.getElementById("export-memory").addEventListener("click", async () => {
  try {
    const data = await api("/api/memory/export?session_id=" + encodeURIComponent(sessionId));
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "karen-memory-export.json";
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) { notify(error.message); }
});

async function analyzeImage(blob, filename, question) {
  const formData = new FormData();
  formData.append("image", blob, filename || "karen-image.jpg");
  formData.append("question", question || "Describe this image. Identify important objects and visible text.");
  formData.append("session_id", sessionId);
  makeMessage("user", "Please analyse this image: " + (question || "Describe what you see."));
  setBusy(true);
  try {
    const result = await api("/api/vision/analyze", { method: "POST", body: formData });
    makeMessage("assistant", result.reply);
    if (speakReplies) speak(result.reply);
  } catch (error) {
    makeMessage("assistant", "Visual analysis failed: " + error.message);
  } finally { setBusy(false); }
}

document.getElementById("attach-image").addEventListener("click", () => document.getElementById("image-input").click());
document.getElementById("image-input").addEventListener("change", async event => {
  const file = event.target.files?.[0];
  if (!file) return;
  const question = input.value.trim();
  input.value = "";
  if (file.size > 8 * 1024 * 1024) {
    notify("Choose an image smaller than 8 MB.");
    event.target.value = "";
    return;
  }
  await analyzeImage(file, file.name, question);
  event.target.value = "";
});

async function openCamera() {
  openModal("camera-modal");
  const status = document.getElementById("camera-status");
  try {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error("Camera access is unavailable in this browser.");
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false
    });
    const video = document.getElementById("camera-video");
    video.srcObject = cameraStream;
    await video.play();
    document.getElementById("capture-camera").disabled = false;
    status.textContent = "Camera active. Capture one frame when ready.";
  } catch (error) { status.textContent = "Camera unavailable: " + error.message; }
}

function stopCamera() {
  if (cameraStream) cameraStream.getTracks().forEach(track => track.stop());
  cameraStream = null;
  document.getElementById("camera-video").srcObject = null;
  document.getElementById("capture-camera").disabled = true;
}
document.getElementById("camera-button").addEventListener("click", openCamera);
document.getElementById("start-camera").addEventListener("click", openCamera);
document.getElementById("capture-camera").addEventListener("click", () => {
  const video = document.getElementById("camera-video");
  const canvas = document.getElementById("camera-canvas");
  if (!video.videoWidth || !video.videoHeight) {
    notify("Camera frame is not ready yet.");
    return;
  }
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0);
  canvas.toBlob(async blob => {
    if (!blob) {
      notify("Could not capture the camera frame.");
      return;
    }
    const question = input.value.trim();
    input.value = "";
    closeModal("camera-modal");
    await analyzeImage(blob, "camera-capture.jpg", question);
  }, "image/jpeg", 0.88);
});

document.getElementById("voice-output").addEventListener("click", () => {
  if (!("speechSynthesis" in window)) {
    notify("Speech output is not supported by this browser.");
    return;
  }
  speakReplies = !speakReplies;
  const button = document.getElementById("voice-output");
  button.classList.toggle("active", speakReplies);
  button.setAttribute("aria-pressed", String(speakReplies));
  if (!speakReplies) window.speechSynthesis.cancel();
  notify(speakReplies ? "Spoken replies enabled." : "Spoken replies disabled.");
});

async function speak(text) {
  if (!speakReplies || !text) return;
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();

  // Prefer natural server-generated Gemini speech; fall back to the browser voice.
  try {
    const result = await api("/api/voice/speak", {
      method: "POST",
      body: JSON.stringify({ text })
    });
    const audio = new Audio(result.audio_url);
    audio.preload = "auto";
    await audio.play();
    return;
  } catch (error) {
    console.info("Gemini TTS unavailable; using browser speech:", error.message);
  }

  if (!("speechSynthesis" in window)) {
    notify("Speech output is unavailable in this browser.");
    return;
  }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.02;
  utterance.pitch = 1.0;
  window.speechSynthesis.speak(utterance);
}

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = navigator.language || "en-US";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  recognition.onstart = () => {
    listening = true;
    document.getElementById("voice-input").classList.add("active");
    notify("Listening. Speak now.");
  };
  recognition.onend = () => {
    listening = false;
    document.getElementById("voice-input").classList.remove("active");
  };
  recognition.onerror = event => notify("Voice input error: " + event.error);
  recognition.onresult = event => {
    const spoken = event.results[0][0].transcript.trim();
    if (spoken) sendMessage(spoken);
  };
  document.getElementById("voice-input").addEventListener("click", () => {
    try {
      if (listening) recognition.stop();
      else recognition.start();
    } catch { notify("Voice recognition is already starting."); }
  });
} else {
  document.getElementById("voice-input").addEventListener("click", () => {
    notify("Voice input is unavailable in this browser. Try an updated Chrome browser.");
  });
}

document.getElementById("auth-form").addEventListener("submit", async event => {
  event.preventDefault();
  const candidate = document.getElementById("access-code").value;
  const status = document.getElementById("auth-error");
  status.textContent = "Checking…";
  try {
    const response = await fetch("/api/auth/check", {
      method: "POST",
      headers: { "X-Karen-Access-Code": candidate }
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail || "Access denied.");
    accessCode = candidate;
    sessionStorage.setItem("karenAccessCode", candidate);
    document.getElementById("auth-modal").hidden = true;
    await loadHistory();
  } catch (error) { status.textContent = error.message; }
});

initialize();
