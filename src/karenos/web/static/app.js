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

let conversation = [];
let accessCode = sessionStorage.getItem("karenAccessCode") || "";
let waiting = false;

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
    if (!payload.access_protected) {
      setStatus("SETUP REQUIRED", "error");
      showAuth("The owner must set KAREN_ACCESS_PASSWORD on the server.");
      return;
    }
    setStatus(payload.ai_ready ? "AI SYSTEM READY" : "AI SETUP REQUIRED", payload.ai_ready ? "ready" : "error");
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

async function sendMessage(text) {
  if (waiting || !accessCode) return;
  const userMessage = { role: "user", content: text };
  const nextConversation = [...conversation, userMessage].slice(-20);
  appendMessage("user", text);
  conversation = nextConversation;
  setWaiting(true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Karen-Access-Code": accessCode
      },
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
  } catch (error) {
    appendMessage("assistant", "I couldn't complete that request. " + error.message);
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
  messagesElement.replaceChildren();
  appendMessage("assistant", "New session started. What would you like to work on?");
  notify("Conversation cleared.");
});

initialize();
