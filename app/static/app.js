const messages = document.querySelector("#messages");
const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const sessionLabel = document.querySelector("#session-label");
const healthStatus = document.querySelector("#health-status");
const knowledgeCount = document.querySelector("#knowledge-count");
const topicCount = document.querySelector("#topic-count");
const topicList = document.querySelector("#topic-list");
const connectionCopy = document.querySelector("#connection-copy");
const clearButton = document.querySelector("#clear-chat");
const activeRoleLabel = document.querySelector("#active-role-label");
const roleButtons = document.querySelectorAll(".role-button");
const refreshOverview = document.querySelector("#refresh-overview");
const ticketForm = document.querySelector("#ticket-form");
const ticketMessage = document.querySelector("#ticket-message");
const ticketPriority = document.querySelector("#ticket-priority");
const ticketOutput = document.querySelector("#ticket-output");
const documentForm = document.querySelector("#document-form");
const documentTitle = document.querySelector("#document-title");
const documentContent = document.querySelector("#document-content");
const documentOutput = document.querySelector("#document-output");

const roleLabels = {
  general: "Genel",
  employee: "Çalışan",
  it: "IT",
  hr: "İK",
  support: "Destek",
};

let sessionId = localStorage.getItem("kayra_session_id") || crypto.randomUUID();
let selectedRole = localStorage.getItem("kayra_role") || "general";

localStorage.setItem("kayra_session_id", sessionId);
sessionLabel.textContent = sessionId.slice(0, 8);
setActiveRole(selectedRole);

function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function addMessage(text, role = "assistant") {
  const element = createElement("article", `message ${role}`, text);
  messages.appendChild(element);
  scrollToLatest();
}

function addInsight(data) {
  const row = createElement("div", "insight-row");
  [
    ["Alan", data.domain || "Genel"],
    ["Güven", `%${Math.round((data.confidence || 0) * 100)}`],
    ["Risk", data.risk_level || "düşük"],
    ["Süre", `${data.response_time_ms || 0} ms`],
  ].forEach(([label, value]) => row.appendChild(createElement("span", "insight-pill", `${label}: ${value}`)));

  if (data.handoff_recommended) {
    row.appendChild(createElement("span", "insight-pill warning", "Eskalasyon önerilir"));
  }
  messages.appendChild(row);
  scrollToLatest();
}

function addSources(sources) {
  if (!sources?.length) return;
  const wrapper = createElement("section", "sources");
  wrapper.appendChild(createElement("h3", null, "Kaynaklar"));

  sources.forEach((source) => {
    const item = createElement("div", "source");
    item.appendChild(createElement("strong", null, source.title));
    item.appendChild(createElement("small", null, `${source.path} · skor ${source.score}`));
    item.appendChild(createElement("p", null, source.excerpt));
    wrapper.appendChild(item);
  });
  messages.appendChild(wrapper);
  scrollToLatest();
}

function addActions(actions, fallbackSuggestions = []) {
  const normalized = actions?.length ? actions : fallbackSuggestions.map((prompt) => ({ label: prompt, prompt }));
  if (!normalized.length) return;
  const row = createElement("div", "action-row");
  normalized.slice(0, 4).forEach((action) => {
    const button = createElement("button", "action-chip", action.label);
    button.type = "button";
    button.addEventListener("click", () => submitMessage(action.prompt));
    row.appendChild(button);
  });
  messages.appendChild(row);
  scrollToLatest();
}

function addFeedback(message) {
  const row = createElement("div", "feedback-row");
  row.appendChild(createElement("span", null, "Kalite"));
  [
    { text: "İyi", rating: 5 },
    { text: "Zayıf", rating: 2 },
  ].forEach((item) => {
    const button = createElement("button", null, item.text);
    button.type = "button";
    button.addEventListener("click", async () => {
      await sendFeedback(message, item.rating);
      row.replaceChildren(document.createTextNode("Geri bildirim alındı"));
      loadOverview();
      loadAudit();
    });
    row.appendChild(button);
  });
  messages.appendChild(row);
  scrollToLatest();
}

async function sendFeedback(message, rating) {
  await fetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message, rating }),
  });
}

async function submitMessage(message) {
  const text = message.trim();
  if (!text) return;

  addMessage(text, "user");
  input.value = "";
  input.style.height = "auto";
  sendButton.disabled = true;
  sendButton.textContent = "Analiz";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: sessionId, user_role: selectedRole }),
    });
    if (!response.ok) throw new Error("Yanıt alınamadı");

    const data = await response.json();
    sessionId = data.session_id;
    localStorage.setItem("kayra_session_id", sessionId);
    sessionLabel.textContent = sessionId.slice(0, 8);

    addMessage(data.answer, "assistant");
    addInsight(data);
    addSources(data.sources || []);
    addActions(data.next_actions || [], data.follow_up_suggestions || []);
    addFeedback(text);
    loadOverview();
    loadAudit();
  } catch (error) {
    addMessage("Teknik bir sorun oluştu. Biraz sonra tekrar deneyebilirsiniz.", "assistant");
  } finally {
    sendButton.disabled = false;
    sendButton.textContent = "Gönder";
    input.focus();
  }
}

function setActiveRole(role) {
  selectedRole = role;
  localStorage.setItem("kayra_role", selectedRole);
  activeRoleLabel.textContent = roleLabels[selectedRole] || "Genel";
  roleButtons.forEach((button) => button.classList.toggle("active", button.dataset.role === selectedRole));
}

function renderTopics(topics) {
  topicList.replaceChildren();
  topicCount.textContent = topics.length.toString();
  topics.forEach((topic) => {
    const button = createElement("button", "topic-button");
    button.type = "button";
    button.appendChild(createElement("span", null, topic.category));
    button.appendChild(createElement("strong", null, topic.title));
    button.addEventListener("click", () => submitMessage(topic.prompt));
    topicList.appendChild(button);
  });
}

async function loadTopics() {
  const response = await fetch("/api/topics");
  const data = await response.json();
  renderTopics(data.topics || []);
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    healthStatus.textContent = "Çevrimiçi";
    knowledgeCount.textContent = `${data.indexed_chunks} parça`;
    connectionCopy.textContent = "Enterprise mod";
  } catch (error) {
    healthStatus.textContent = "Bağlantı yok";
    knowledgeCount.textContent = "-";
    connectionCopy.textContent = "Sunucu yok";
  }
}

async function loadOverview() {
  const response = await fetch("/api/enterprise/overview");
  const data = await response.json();

  document.querySelector("#product-name").textContent = data.product_name;
  document.querySelector("#product-tagline").textContent = data.tagline;
  document.querySelector("#product-maturity").textContent = data.maturity;

  renderMetrics(data.metrics || []);
  renderNamedList("#capability-list", data.capabilities || []);
  renderNamedList("#integration-list", data.integrations || []);
  renderSecurity(data.security_controls || []);
}

function renderMetrics(metrics) {
  const grid = document.querySelector("#metrics-grid");
  grid.replaceChildren();
  metrics.forEach((metric) => {
    const card = createElement("div", "metric-card");
    card.appendChild(createElement("span", null, metric.label));
    card.appendChild(createElement("strong", null, metric.value));
    card.appendChild(createElement("small", null, metric.trend));
    grid.appendChild(card);
  });
}

function renderNamedList(selector, items) {
  const list = document.querySelector(selector);
  list.replaceChildren();
  items.forEach((item) => {
    const row = createElement("div", "stack-item");
    const title = createElement("div", "stack-title");
    title.appendChild(createElement("strong", null, item.title || item.name));
    title.appendChild(createElement("span", null, item.status));
    row.appendChild(title);
    row.appendChild(createElement("p", null, item.description));
    list.appendChild(row);
  });
}

function renderSecurity(items) {
  const list = document.querySelector("#security-list");
  list.replaceChildren();
  items.forEach((item) => {
    const row = createElement("div", "security-item");
    row.appendChild(createElement("strong", null, item.title));
    row.appendChild(createElement("span", null, item.level));
    row.appendChild(createElement("p", null, item.description));
    list.appendChild(row);
  });
}

async function loadAudit() {
  const response = await fetch("/api/admin/audit");
  const data = await response.json();
  const list = document.querySelector("#audit-list");
  list.replaceChildren();

  if (!data.events?.length) {
    list.appendChild(createElement("p", "empty-state", "Henüz audit olayı yok."));
    return;
  }

  data.events.forEach((event) => {
    const row = createElement("div", "audit-item");
    row.appendChild(createElement("strong", null, event.summary));
    row.appendChild(createElement("span", null, `${event.risk_level} · ${event.created_at.slice(0, 16)}`));
    list.appendChild(row);
  });
}

async function createTicketDraft(event) {
  event.preventDefault();
  const message = ticketMessage.value.trim();
  if (!message) return;

  const response = await fetch("/api/tickets/draft", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, priority: ticketPriority.value }),
  });
  const draft = await response.json();
  ticketOutput.replaceChildren();
  ticketOutput.appendChild(createElement("strong", null, draft.title));
  ticketOutput.appendChild(createElement("p", null, `${draft.category} · ${draft.priority}`));
  draft.acceptance_criteria.forEach((item) => ticketOutput.appendChild(createElement("span", "mini-line", item)));
}

async function addKnowledgeDocument(event) {
  event.preventDefault();
  const title = documentTitle.value.trim();
  const content = documentContent.value.trim();
  if (!title || content.length < 20) return;

  const response = await fetch("/api/admin/documents", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, content, category: "Admin" }),
  });
  const result = await response.json();
  documentOutput.textContent = `${result.status}: ${result.indexed_chunks} parça indekslendi`;
  documentTitle.value = "";
  documentContent.value = "";
  checkHealth();
  loadOverview();
  loadAudit();
}

function scrollToLatest() {
  messages.scrollTop = messages.scrollHeight;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  submitMessage(input.value);
});

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 136)}px`;
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

roleButtons.forEach((button) => button.addEventListener("click", () => setActiveRole(button.dataset.role)));
clearButton.addEventListener("click", () => {
  messages.replaceChildren();
  sessionId = crypto.randomUUID();
  localStorage.setItem("kayra_session_id", sessionId);
  sessionLabel.textContent = sessionId.slice(0, 8);
  addMessage("Yeni oturum açıldı. Hangi kurumsal akışı ele alalım?", "assistant");
});
refreshOverview.addEventListener("click", () => {
  loadOverview();
  loadAudit();
});
ticketForm.addEventListener("submit", createTicketDraft);
documentForm.addEventListener("submit", addKnowledgeDocument);

checkHealth();
loadTopics();
loadOverview();
loadAudit();
addMessage("Merhaba, ben Kayra. Kurumsal bilgi tabanından kaynaklı yanıt, risk skoru ve aksiyon planı hazırlayabilirim.", "assistant");
