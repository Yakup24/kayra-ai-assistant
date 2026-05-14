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

const roleLabels = {
  general: "Genel",
  employee: "Çalışan",
  it: "IT",
  hr: "İK",
  support: "Destek",
};

const fallbackTopics = [
  { id: "returns", title: "İade ve Kargo", category: "Müşteri Destek", prompt: "İade süreci nasıl işliyor?" },
  { id: "vpn", title: "VPN ve Erişim", category: "IT Destek", prompt: "VPN bağlantı hatasında ne yapmalıyım?" },
  { id: "leave", title: "Yıllık İzin", category: "İK", prompt: "Yıllık izin prosedürü nedir?" },
  { id: "privacy", title: "KVKK ve Gizlilik", category: "Uyumluluk", prompt: "Kişisel veri paylaşmadan nasıl destek alabilirim?" },
];

let sessionId = localStorage.getItem("kayra_session_id") || crypto.randomUUID();
let selectedRole = localStorage.getItem("kayra_role") || "general";

localStorage.setItem("kayra_session_id", sessionId);
sessionLabel.textContent = sessionId.slice(0, 8);
setActiveRole(selectedRole);

function addMessage(text, role = "assistant") {
  const element = document.createElement("article");
  element.className = `message ${role}`;
  element.textContent = text;
  messages.appendChild(element);
  scrollToLatest();
  return element;
}

function addInsight(data) {
  const insight = document.createElement("div");
  insight.className = "insight-row";

  const confidence = Math.round((data.confidence || 0) * 100);
  const items = [
    ["Alan", data.domain || "Genel"],
    ["Güven", `%${confidence}`],
    ["Risk", data.risk_level || "düşük"],
    ["Süre", `${data.response_time_ms || 0} ms`],
  ];

  items.forEach(([label, value]) => {
    const pill = document.createElement("span");
    pill.className = "insight-pill";
    pill.textContent = `${label}: ${value}`;
    insight.appendChild(pill);
  });

  if (data.handoff_recommended) {
    const handoff = document.createElement("span");
    handoff.className = "insight-pill warning";
    handoff.textContent = "Aktarım önerilir";
    insight.appendChild(handoff);
  }

  messages.appendChild(insight);
  scrollToLatest();
}

function addSources(sources) {
  if (!sources.length) return;

  const wrapper = document.createElement("section");
  wrapper.className = "sources";

  const title = document.createElement("h3");
  title.textContent = "Kaynaklar";
  wrapper.appendChild(title);

  sources.forEach((source) => {
    const item = document.createElement("div");
    item.className = "source";

    const heading = document.createElement("strong");
    heading.textContent = source.title;

    const meta = document.createElement("small");
    meta.textContent = `${source.path} · skor ${source.score}`;

    const excerpt = document.createElement("p");
    excerpt.textContent = source.excerpt;

    item.append(heading, meta, excerpt);
    wrapper.appendChild(item);
  });

  messages.appendChild(wrapper);
  scrollToLatest();
}

function addActions(actions, fallbackSuggestions = []) {
  const normalized = actions?.length
    ? actions
    : fallbackSuggestions.map((prompt) => ({ label: prompt, prompt }));

  if (!normalized.length) return;

  const row = document.createElement("div");
  row.className = "action-row";

  normalized.slice(0, 4).forEach((action) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "action-chip";
    button.textContent = action.label;
    button.addEventListener("click", () => submitMessage(action.prompt));
    row.appendChild(button);
  });

  messages.appendChild(row);
  scrollToLatest();
}

function addFeedback(message) {
  const row = document.createElement("div");
  row.className = "feedback-row";

  const label = document.createElement("span");
  label.textContent = "Yanıt kalitesi";
  row.appendChild(label);

  [
    { text: "İyi", rating: 5 },
    { text: "Zayıf", rating: 2 },
  ].forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = item.text;
    button.addEventListener("click", async () => {
      await sendFeedback(message, item.rating);
      row.replaceChildren(document.createTextNode("Geri bildirim alındı"));
    });
    row.appendChild(button);
  });

  messages.appendChild(row);
  scrollToLatest();
}

async function sendFeedback(message, rating) {
  try {
    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message, rating }),
    });
  } catch (error) {
    console.warn("Feedback gönderilemedi", error);
  }
}

async function submitMessage(message) {
  const text = message.trim();
  if (!text) return;

  addMessage(text, "user");
  input.value = "";
  input.style.height = "auto";
  sendButton.disabled = true;
  sendButton.textContent = "Bekle";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: sessionId, user_role: selectedRole }),
    });

    if (!response.ok) {
      throw new Error("Yanıt alınamadı");
    }

    const data = await response.json();
    sessionId = data.session_id;
    localStorage.setItem("kayra_session_id", sessionId);
    sessionLabel.textContent = sessionId.slice(0, 8);

    addMessage(data.answer, "assistant");
    addInsight(data);
    addSources(data.sources || []);
    addActions(data.next_actions || [], data.follow_up_suggestions || []);
    addFeedback(text);
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
  roleButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.role === selectedRole);
  });
}

function renderTopics(topics) {
  topicList.replaceChildren();
  topicCount.textContent = topics.length.toString();

  topics.forEach((topic) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "topic-button";
    button.innerHTML = `<span>${topic.category}</span><strong>${topic.title}</strong>`;
    button.addEventListener("click", () => submitMessage(topic.prompt));
    topicList.appendChild(button);
  });
}

async function loadTopics() {
  try {
    const response = await fetch("/api/topics");
    const data = await response.json();
    renderTopics(data.topics || fallbackTopics);
  } catch (error) {
    renderTopics(fallbackTopics);
  }
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    healthStatus.textContent = "Çevrimiçi";
    knowledgeCount.textContent = `${data.indexed_chunks} parça`;
    connectionCopy.textContent = "Kaynak modu aktif";
  } catch (error) {
    healthStatus.textContent = "Bağlantı yok";
    knowledgeCount.textContent = "-";
    connectionCopy.textContent = "Sunucu yok";
  }
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
  input.style.height = `${Math.min(input.scrollHeight, 132)}px`;
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

roleButtons.forEach((button) => {
  button.addEventListener("click", () => setActiveRole(button.dataset.role));
});

clearButton.addEventListener("click", () => {
  messages.replaceChildren();
  sessionId = crypto.randomUUID();
  localStorage.setItem("kayra_session_id", sessionId);
  sessionLabel.textContent = sessionId.slice(0, 8);
  addMessage("Yeni oturum açıldı. Kurumsal bilgi tabanında hangi konuyu inceleyelim?", "assistant");
});

checkHealth();
loadTopics();
addMessage("Merhaba, ben Kayra. Kurumsal bilgi tabanından kaynaklı yanıt hazırlayabilirim.", "assistant");
