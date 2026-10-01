const messages = document.getElementById("messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("message");
const send = document.getElementById("send");
const health = document.getElementById("health");

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"}[c]));
}

function addUser(text) {
  const el = document.createElement("div");
  el.className = "message user";
  el.innerHTML = `<div class="bubble">${escapeHtml(text)}</div><div class="avatar">You</div>`;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}

function addAssistant(data) {
  const el = document.createElement("div");
  el.className = "message assistant";
  const citations = (data.citations || []).map(c =>
    `<div class="source"><strong>${escapeHtml(c.document_id)} · ${escapeHtml(c.section)}</strong></div>`
  ).join("");
  const snippets = (data.snippets || []).map(s =>
    `<div class="source"><strong>${escapeHtml(s.document_id)} · ${escapeHtml(s.section)}</strong><p>${escapeHtml(s.snippet)}</p></div>`
  ).join("");
  const trace = (data.trace || []).map(t =>
    `<div class="trace-row"><strong>${escapeHtml(t.step || "step")}</strong> · ${escapeHtml(t.status || "")} ${t.tool ? `· <code>${escapeHtml(t.tool)}</code>` : ""}</div>`
  ).join("");
  el.innerHTML = `
    <div class="avatar">X</div>
    <div class="bubble">
      <div class="answer">${escapeHtml(data.answer || data.error || "No answer returned.")}</div>
      ${citations ? `<details class="citations"><summary>Policy citations (${data.citations.length})</summary>${citations}</details>` : ""}
      ${snippets ? `<details class="sources"><summary>Retrieved source snippets</summary>${snippets}</details>` : ""}
      ${trace ? `<details class="trace"><summary>Operational MCP trace</summary>${trace}</details>` : ""}
    </div>`;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}

async function ask(text) {
  addUser(text);
  send.disabled = true;
  send.textContent = "Working…";
  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message: text})
    });
    const data = await response.json();
    addAssistant(data);
    await loadHealth();
  } catch (error) {
    addAssistant({answer: "The application could not reach the chat endpoint. Check /health and try again."});
  } finally {
    send.disabled = false;
    send.textContent = "Ask Xena";
  }
}



form.addEventListener("submit", event => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  ask(text);
});

document.querySelectorAll(".demo").forEach(button => {
  button.addEventListener("click", async () => {
    const response = await fetch("/api/demo-tasks");
    const data = await response.json();
    const task = data.tasks.find(x => x.id === button.dataset.demo);
    if (task) {
      input.value = task.prompt;
      input.focus();
    }
  });
});

async function loadHealth() {
  try {
    const response = await fetch("/health");
    const data = await response.json();

    if (data.mcp?.ok === true) {
      const toolCount = Array.isArray(data.mcp.tools)
        ? data.mcp.tools.length
        : 0;

      health.textContent = `Online · MCP ${toolCount} tools`;
    } else {
      health.textContent = "Online · MCP unavailable";
    }
  } catch {
    health.textContent = "Health check unavailable";
  }
}
loadHealth();