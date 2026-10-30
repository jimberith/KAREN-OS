const messagesElement = document.getElementById("messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const typing = document.getElementById("typing-indicator");
const authOverlay = document.getElementById("auth-overlay");
const authForm = document.getElementById("auth-form");
const accessInput = document.getElementById("access-code");
const authError = document.getElementById("auth-error");
const authSubmit = document.getElementById("auth-submit");
const statusText = document.getElementById("system-status");
const statusPill = document.querySelector(".status-pill");
const clearButton = document.getElementById("clear-chat");
const toast = document.getElementById("toast");
const micButton = document.getElementById("voice-input");
const speakButton = document.getElementById("voice-output");

let conversation = [];
let accessCode = sessionStorage.getItem("karenAccessCode") || "";
let waiting = false;
let speakReplies = false;
let recognition = null;
let listening = false;

function setStatus(text, mode = "") {
  statusText.textContent = text;
  statusPill.className = "status-pill" + (mode ? " " + mode : "");
}

function notify(text) {
  toast.textContent = text;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2500);
}

function appendMessage(role, content) {
  const article = document.createElement("article");
  article.className = "message " + (role === "user" ? "user-message" : "assistant-message");

  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.textContent = role === "user" ? "Y" : "K";

  const wrapper = document.createElement("div");
  wrapper.className = "message-content";

  const author = document.createElement("div");
  author.className = "message-author";
  const label = document.createElement("span");
  label.textContent = role === "user" ? "YOU" : "KAREN";
  const time = document.createElement("span");
  time.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  author.append(label, time);

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = content;

  wrapper.append(author, bubble);
  article.append(avatar, wrapper);
  messagesElement.append(article);
  messagesElement.scrollTop = messagesElement.scrollHeight;
}

function showAuth(message = "") {
  authError.textContent = message;
  authOverlay.hidden = false;
  accessInput.value = "";
  window.setTimeout(() => accessInput.focus(), 50);
}

async function verifyAccess(code) {
  const response = await fetch("/api/auth/check", {
    method: "POST",
    headers: { "X-Karen-Access-Code": code }
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || "Could not verify access.");
  return true;
}

async function initialize() {
  try {
    const response = await fetch("/api/status");
    const payload = await response.json();
    if (!response.ok) throw new Error("The KAREN OS server is unavailable.");
    setStatus(
      payload.ai_ready ? "AI SYSTEM READY" : "AI SETUP REQUIRED",
      payload.ai_ready ? "ready" : "error"
    );

    // Codespaces uses GitHub's private forwarded-port access control; no second app login.
    if (!payload.access_protected) {
      authOverlay.hidden = true;
      accessCode = "";
      sessionStorage.removeItem("karenAccessCode");
      return;
    }

    if (accessCode) {
      try {
        await verifyAccess(accessCode);
        authOverlay.hidden = true;
        return;
      } catch {
        sessionStorage.removeItem("karenAccessCode");
        accessCode = "";
      }
    }
    showAuth();
  } catch (error) {
    setStatus("SERVER UNAVAILABLE", "error");
    showAuth(error.message);
  }
}

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const code = accessInput.value.trim();
  if (!code) return;
  authSubmit.disabled = true;
  authSubmit.textContent = "VERIFYING...";
  authError.textContent = "";
  try {
    await verifyAccess(code);
    accessCode = code;
    sessionStorage.setItem("karenAccessCode", code);
    authOverlay.hidden = true;
    notify("Secure session connected.");
    input.focus();
  } catch (error) {
    authError.textContent = error.message;
  } finally {
    authSubmit.disabled = false;
    authSubmit.innerHTML = 'ACCESS KAREN OS <span>↗</span>';
  }
});

function setWaiting(value) {
  waiting = value;
  typing.hidden = !value;
  sendButton.disabled = value;
  input.disabled = value;
  if (!value) input.focus();
}

function speak(text) {
  if (!speakReplies || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.02;
  utterance.pitch = 1.0;
  window.speechSynthesis.speak(utterance);
}

async function sendMessage(text) {
  if (waiting) return;
  const userMessage = { role: "user", content: text };
  const nextConversation = [...conversation, userMessage].slice(-20);
  appendMessage("user", text);
  conversation = nextConversation;
  setWaiting(true);

  const headers = { "Content-Type": "application/json" };
  if (accessCode) headers["X-Karen-Access-Code"] = accessCode;

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers,
      body: JSON.stringify({ messages: conversation })
    });
    const payload = await response.json().catch(() => ({}));
    if (response.status === 401) {
      sessionStorage.removeItem("karenAccessCode");
      accessCode = "";
      showAuth("Your access code was rejected. Enter it again.");
      return;
    }
    if (!response.ok) throw new Error(payload.detail || "The request failed.");
    const reply = String(payload.reply || "I didn't receive a response.");
    conversation = [...conversation, { role: "assistant", content: reply }].slice(-20);
    appendMessage("assistant", reply);
    speak(reply);
  } catch (error) {
    appendMessage("assistant", "KAREN connection error: " + error.message);
  } finally {
    setWaiting(false);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text || waiting) return;
  input.value = "";
  input.style.height = "auto";
  await sendMessage(text);
});

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 130) + "px";
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

clearButton.addEventListener("click", () => {
  conversation = [];
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  messagesElement.replaceChildren();
  appendMessage("assistant", "New session started. What would you like to work on?");
  notify("Conversation cleared.");
});

speakButton.addEventListener("click", () => {
  if (!("speechSynthesis" in window)) {
    notify("Speech output is not supported in this browser.");
    return;
  }
  speakReplies = !speakReplies;
  speakButton.classList.toggle("active", speakReplies);
  speakButton.setAttribute("aria-pressed", String(speakReplies));
  speakButton.title = speakReplies ? "Turn voice replies off" : "Read KAREN replies aloud";
  if (!speakReplies) window.speechSynthesis.cancel();
  notify(speakReplies ? "Voice replies enabled." : "Voice replies disabled.");
});

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = navigator.language || "en-US";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  recognition.onstart = () => {
    listening = true;
    micButton.classList.add("active");
    micButton.setAttribute("aria-pressed", "true");
    notify("Listening. Speak now.");
  };
  recognition.onend = () => {
    listening = false;
    micButton.classList.remove("active");
    micButton.setAttribute("aria-pressed", "false");
  };
  recognition.onerror = (event) => {
    notify(event.error === "not-allowed" ? "Microphone permission was denied." : "Voice input failed: " + event.error);
  };
  recognition.onresult = (event) => {
    const spoken = event.results[0][0].transcript.trim();
    if (spoken) {
      input.value = spoken;
      form.requestSubmit();
    }
  };
  micButton.addEventListener("click", () => {
    if (listening) recognition.stop();
    else {
      try { recognition.start(); }
      catch { notify("Voice input is already starting."); }
    }
  });
} else {
  micButton.addEventListener("click", () => {
    notify("Voice input is not supported here. Try an updated Chrome browser.");
  });
  micButton.title = "Voice input unsupported in this browser";
}

initialize();
