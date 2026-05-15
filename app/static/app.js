const authScreen = document.querySelector("#auth-screen");
const appShell = document.querySelector("#app-shell");
const authForm = document.querySelector("#auth-form");
const authTabs = document.querySelectorAll(".auth-tab");
const authSubmit = document.querySelector("#auth-submit");
const authMessage = document.querySelector("#auth-message");
const authUsername = document.querySelector("#auth-username");
const authPassword = document.querySelector("#auth-password");
const logoutButton = document.querySelector("#logout-button");
const accountName = document.querySelector("#account-name");

const messages = document.querySelector("#messages");
const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const onlineToggle = document.querySelector("#online-toggle");
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
const ticketRequester = document.querySelector("#ticket-requester");
const ticketOutput = document.querySelector("#ticket-output");
const ticketList = document.querySelector("#ticket-list");
const ticketPanelTitle = document.querySelector("#ticket-panel-title");
const ticketPanelMode = document.querySelector("#ticket-panel-mode");
const ticketPanelCopy = document.querySelector("#ticket-panel-copy");
const documentForm = document.querySelector("#document-form");
const documentTitle = document.querySelector("#document-title");
const documentContent = document.querySelector("#document-content");
const documentOutput = document.querySelector("#document-output");
const documentList = document.querySelector("#document-list");
const userForm = document.querySelector("#user-form");
const userOutput = document.querySelector("#user-output");
const userList = document.querySelector("#user-list");
const newUserDisplay = document.querySelector("#new-user-display");
const newUserEmail = document.querySelector("#new-user-email");
const newUserUsername = document.querySelector("#new-user-username");
const newUserPassword = document.querySelector("#new-user-password");
const newUserRole = document.querySelector("#new-user-role");
const controlPanel = document.querySelector(".control-panel");

const roleLabels = {
  general: "Genel",
  employee: "Çalışan",
  it: "IT",
  hr: "İK",
  support: "Destek Uzmanı",
  admin: "Admin",
};

const ticketStatusLabels = {
  open: "Açık",
  in_progress: "İşlemde",
  resolved: "Çözüldü",
  closed: "Kapalı",
};

let authMode = "login";
let authToken = localStorage.getItem("kayra_token") || "";
let currentUser = null;
let sessionId = localStorage.getItem("kayra_session_id") || crypto.randomUUID();
let selectedRole = localStorage.getItem("kayra_role") || "general";

localStorage.setItem("kayra_session_id", sessionId);
sessionLabel.textContent = sessionId.slice(0, 8);
setActiveRole(selectedRole);

function authHeaders() {
  return authToken ? { Authorization: `Bearer ${authToken}` } : {};
}

function isAdmin() {
  return currentUser?.role === "admin";
}

function isSupport() {
  return currentUser?.role === "support";
}

function canManageTickets() {
  return isAdmin() || isSupport();
}

function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function setAuthMode(mode) {
  authMode = mode;
  authTabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.authMode === mode));
  authSubmit.textContent = mode === "admin" ? "Admin Girişi" : mode === "support" ? "Destek Uzmanı Girişi" : "Çalışan Girişi";
  authMessage.textContent = "";
  if (mode === "admin") {
    authUsername.value = authUsername.value || "admin";
  } else if (mode === "support") {
    authUsername.value = authUsername.value || "support";
  }
}

async function submitAuth(event) {
  event.preventDefault();
  authMessage.textContent = "";

  const payload = {
    username: authUsername.value.trim(),
    password: authPassword.value,
  };

  try {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Giriş başarısız");

    if (authMode === "admin" && data.user.role !== "admin") {
      throw new Error("Bu giriş alanı yalnızca admin hesapları içindir.");
    }
    if (authMode === "support" && data.user.role !== "support") {
      throw new Error("Bu giriş alanı yalnızca destek uzmanı hesapları içindir.");
    }

    authToken = data.token;
    currentUser = data.user;
    localStorage.setItem("kayra_token", authToken);
    await enterApp();
  } catch (error) {
    authMessage.textContent = error.message;
  }
}

async function restoreSession() {
  if (!authToken) {
    showAuth();
    return;
  }
  try {
    const response = await fetch("/api/auth/me", { headers: authHeaders() });
    if (!response.ok) throw new Error("Oturum yok");
    currentUser = await response.json();
    await enterApp();
  } catch (error) {
    localStorage.removeItem("kayra_token");
    authToken = "";
    showAuth();
  }
}

function showAuth() {
  authScreen.classList.remove("hidden");
  appShell.classList.add("hidden");
  setAuthMode(authMode);
}

async function enterApp() {
  authScreen.classList.add("hidden");
  appShell.classList.remove("hidden");
  const display = currentUser.display_name || currentUser.username;
  accountName.textContent = `${display} · ${roleLabels[currentUser.role] || currentUser.role}`;
  if (isAdmin()) {
    selectedRole = "admin";
  } else if (isSupport()) {
    selectedRole = "support";
  } else if (selectedRole === "admin" || selectedRole === "support") {
    selectedRole = currentUser.role || "employee";
  }
  setActiveRole(selectedRole);
  applyModeVisibility();
  await Promise.all([checkHealth(), loadTopics(), loadTickets()]);
  if (isAdmin()) {
    await Promise.all([loadOverview(), loadAudit(), loadUsers(), loadTickets(), loadDocuments(), loadIntegrations()]);
  }
  await loadConversationHistory();
  if (!messages.children.length) {
    addMessage("Merhaba, ben Kayra. Çalışan destek taleplerini anlayabilir, bilgi tabanından kaynaklı cevap hazırlayabilir ve gerektiğinde ticket açıp süreci takip edebilirim.", "assistant");
  }
}

function applyModeVisibility() {
  const adminMode = isAdmin();
  const supportMode = isSupport();
  controlPanel.classList.remove("hidden");
  appShell.classList.toggle("admin-mode", adminMode);
  appShell.classList.toggle("support-mode", supportMode);
  appShell.classList.toggle("user-mode", !adminMode && !supportMode);
  document.querySelectorAll(".admin-only").forEach((element) => element.classList.toggle("hidden", !adminMode));
  roleButtons.forEach((button) => {
    const role = button.dataset.role;
    const hidden =
      (adminMode && role !== "admin") ||
      (supportMode && role !== "support") ||
      (!adminMode && !supportMode && ["admin", "support"].includes(role));
    button.classList.toggle("hidden", hidden);
    button.disabled = supportMode && role !== "support";
  });
  configureTicketPanel();
}

function configureTicketPanel() {
  if (!currentUser) return;
  ticketRequester.classList.toggle("hidden", !canManageTickets());
  ticketRequester.value = canManageTickets() ? ticketRequester.value : "";
  if (isAdmin()) {
    ticketPanelTitle.textContent = "Tüm Çalışan Talepleri";
    ticketPanelMode.textContent = "Admin görünümü";
    ticketPanelCopy.textContent = "Çalışanların açtığı tüm talepleri, öncelikleri, destek atamalarını ve çözüm notlarını izleyebilirsiniz.";
    ticketMessage.placeholder = "Talep metni veya çalışandan gelen destek notu";
  } else if (isSupport()) {
    ticketPanelTitle.textContent = "Destek Uzmanı Kuyruğu";
    ticketPanelMode.textContent = "Çözüm ekranı";
    ticketPanelCopy.textContent = "Çalışanlardan gelen sorunları alın, işlem durumuna taşıyın ve çözüm notuyla kapatın.";
    ticketMessage.placeholder = "Çalışan adına yeni sorun/talep açmak için metin";
  } else {
    ticketPanelTitle.textContent = "Çalışan Taleplerim";
    ticketPanelMode.textContent = "Çalışan";
    ticketPanelCopy.textContent = "Yaşadığınız sorunu yazıp destek talebi açın; çözüm durumunu ve destek notunu buradan takip edin.";
    ticketMessage.placeholder = "Yaşadığınız sorunu, hata mesajını ve ihtiyacınızı yazın";
  }
}

function logout() {
  localStorage.removeItem("kayra_token");
  authToken = "";
  currentUser = null;
  messages.replaceChildren();
  showAuth();
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
      if (isAdmin()) {
        loadOverview();
        loadAudit();
      }
    });
    row.appendChild(button);
  });
  messages.appendChild(row);
  scrollToLatest();
}

async function sendFeedback(message, rating) {
  await fetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ session_id: sessionId, message, rating }),
  });
}

async function submitMessage(message) {
  const text = message.trim();
  if (!text || !authToken) return;

  addMessage(text, "user");
  input.value = "";
  input.style.height = "auto";
  sendButton.disabled = true;
  sendButton.textContent = onlineToggle.checked ? "Online" : "Analiz";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({
        message: text,
        session_id: sessionId,
        user_role: selectedRole,
        online_enabled: onlineToggle.checked,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Yanıt alınamadı");

    sessionId = data.session_id;
    localStorage.setItem("kayra_session_id", sessionId);
    sessionLabel.textContent = sessionId.slice(0, 8);

    addMessage(data.answer, "assistant");
    addInsight(data);
    addSources(data.sources || []);
    addActions(data.next_actions || [], data.follow_up_suggestions || []);
    addFeedback(text);
    if (isAdmin()) {
      loadOverview();
      loadAudit();
    }
    if (canManageTickets()) {
      loadTickets();
    }
  } catch (error) {
    addMessage(error.message || "Teknik bir sorun oluştu. Biraz sonra tekrar deneyebilirsiniz.", "assistant");
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
    connectionCopy.textContent = isAdmin() ? "Admin mod" : isSupport() ? "Destek uzmanı modu" : "Çalışan modu";
  } catch (error) {
    healthStatus.textContent = "Bağlantı yok";
    knowledgeCount.textContent = "-";
    connectionCopy.textContent = "Sunucu yok";
  }
}

async function loadOverview() {
  const response = await fetch("/api/enterprise/overview", { headers: authHeaders() });
  if (!response.ok) return;
  const data = await response.json();

  document.querySelector("#product-name").textContent = data.product_name;
  document.querySelector("#product-tagline").textContent = data.tagline;
  document.querySelector("#product-maturity").textContent = data.maturity;

  renderMetrics(data.metrics || []);
  renderNamedList("#capability-list", data.capabilities || []);
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
  const response = await fetch("/api/admin/audit", { headers: authHeaders() });
  if (!response.ok) return;
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

async function loadUsers() {
  const response = await fetch("/api/admin/users", { headers: authHeaders() });
  if (!response.ok) return;
  const data = await response.json();
  userList.replaceChildren();

  data.users.forEach((user) => {
    const row = createElement("div", "user-item");
    const info = createElement("div", "user-info");
    info.appendChild(createElement("strong", null, user.display_name));
    info.appendChild(createElement("span", null, `${user.username} · ${roleLabels[user.role] || user.role} · ${user.active ? "aktif" : "pasif"}`));

    const actions = createElement("div", "user-actions");
    const reset = createElement("button", null, "Şifre");
    reset.type = "button";
    reset.addEventListener("click", () => resetUserPassword(user.username));

    const toggle = createElement("button", null, user.active ? "Pasifleştir" : "Aktifleştir");
    toggle.type = "button";
    toggle.addEventListener("click", () => setUserStatus(user.username, !user.active));

    actions.append(reset, toggle);
    row.append(info, actions);
    userList.appendChild(row);
  });
}

async function loadIntegrations() {
  const response = await fetch("/api/admin/integrations", { headers: authHeaders() });
  if (!response.ok) return;
  const data = await response.json();
  const list = document.querySelector("#integration-list");
  list.replaceChildren();

  data.integrations.forEach((item) => {
    const row = createElement("div", "stack-item integration-item");
    const title = createElement("div", "stack-title");
    title.appendChild(createElement("strong", null, item.name));
    title.appendChild(createElement("span", null, item.enabled ? "Aktif" : item.status));
    row.appendChild(title);
    row.appendChild(createElement("p", null, item.description));

    const actions = createElement("div", "inline-actions");
    const toggle = createElement("button", null, item.enabled ? "Pasifleştir" : "Aktifleştir");
    toggle.type = "button";
    toggle.addEventListener("click", () => toggleIntegration(item.id, !item.enabled));
    actions.appendChild(toggle);
    row.appendChild(actions);
    list.appendChild(row);
  });
}

async function toggleIntegration(id, enabled) {
  await fetch(`/api/admin/integrations/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ enabled, status: enabled ? "Aktif" : "Pasif" }),
  });
  await Promise.all([loadIntegrations(), loadAudit()]);
}

async function createUser(event) {
  event.preventDefault();
  const payload = {
    display_name: newUserDisplay.value.trim() || null,
    email: newUserEmail.value.trim() || null,
    username: newUserUsername.value.trim(),
    password: newUserPassword.value,
    role: newUserRole.value,
  };
  if (!payload.username || payload.password.length < 6) {
    userOutput.textContent = "Hesap kullanıcı adı ve en az 6 karakter şifre gerekli.";
    return;
  }

  const response = await fetch("/api/admin/users", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok) {
    userOutput.textContent = result.detail || "Hesap oluşturulamadı.";
    return;
  }

  userOutput.textContent = `${result.username} kaydı veritabanına işlendi. Geçici şifre güvenli kanaldan iletilmeli.`;
  newUserDisplay.value = "";
  newUserEmail.value = "";
  newUserUsername.value = "";
  newUserPassword.value = "";
  newUserRole.value = "employee";
  await Promise.all([loadUsers(), loadOverview(), loadAudit()]);
}

async function resetUserPassword(username) {
  const password = prompt(`${username} için yeni geçici şifre`);
  if (!password || password.length < 6) {
    userOutput.textContent = "Şifre en az 6 karakter olmalı.";
    return;
  }
  const response = await fetch(`/api/admin/users/${encodeURIComponent(username)}/password`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ password }),
  });
  userOutput.textContent = response.ok ? `${username} şifresi güncellendi.` : "Şifre güncellenemedi.";
  await Promise.all([loadUsers(), loadAudit()]);
}

async function setUserStatus(username, active) {
  const response = await fetch(`/api/admin/users/${encodeURIComponent(username)}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ active }),
  });
  if (!response.ok) {
    const result = await response.json();
    userOutput.textContent = result.detail || "Hesap durumu değiştirilemedi.";
    return;
  }
  userOutput.textContent = `${username} ${active ? "aktifleştirildi" : "pasifleştirildi"}.`;
  await Promise.all([loadUsers(), loadAudit()]);
}

async function loadConversationHistory() {
  const response = await fetch(`/api/conversations/${sessionId}`, { headers: authHeaders() });
  if (!response.ok) return;
  const data = await response.json();
  messages.replaceChildren();
  data.messages.forEach((item) => {
    addMessage(item.content, item.role === "user" ? "user" : "assistant");
  });
}

async function loadTickets() {
  const endpoint = isAdmin() ? "/api/admin/tickets" : isSupport() ? "/api/support/tickets" : "/api/tickets/me";
  let data;
  try {
    const response = await fetch(endpoint, { headers: authHeaders() });
    data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Ticket listesi alınamadı.");
  } catch (error) {
    ticketOutput.textContent = error.message || "Ticket listesi alınamadı.";
    return;
  }
  ticketList.replaceChildren();

  if (!data.tickets.length) {
    const copy = isSupport() ? "Açık destek kuyruğunda talep yok." : "Henüz ticket yok.";
    ticketList.appendChild(createElement("p", "empty-state", copy));
    return;
  }

  data.tickets.slice(0, 12).forEach((ticket) => {
    const row = createElement("div", "ticket-item");
    const info = createElement("div", "ticket-info");
    info.appendChild(createElement("strong", null, `${ticket.id} · ${ticket.title}`));
    info.appendChild(createElement("span", null, `${ticket.category} · ${ticket.priority} · ${ticketStatusLabels[ticket.status] || ticket.status} · Çalışan: ${ticket.requester}`));
    info.appendChild(createElement("span", "ticket-meta", `Atanan: ${ticket.assignee || "Henüz yok"}`));
    if (ticket.resolution_note) {
      info.appendChild(createElement("em", "resolution-note", `Çözüm: ${ticket.resolution_note}`));
    }
    const actions = createElement("div", "inline-actions");
    if (canManageTickets()) {
      const actionSet = [];
      if (ticket.status === "open") {
        actionSet.push(["in_progress", "İşleme al"]);
      } else if (ticket.status === "in_progress") {
        actionSet.push(["in_progress", ticket.assignee === currentUser.username ? "Üzerimde" : "Devral"]);
      }
      if (ticket.status !== "resolved") {
        actionSet.push(["resolved", "Çöz"]);
      }
      actionSet.forEach(([status, label]) => {
        const button = createElement("button", null, label);
        button.type = "button";
        if (status === "in_progress" && ticket.status === "in_progress" && ticket.assignee === currentUser.username) {
          button.disabled = true;
        }
        button.addEventListener("click", () => updateTicketStatus(ticket.id, status, button));
        actions.appendChild(button);
      });
    } else {
      const ask = createElement("button", null, "Sohbete taşı");
      ask.type = "button";
      ask.addEventListener("click", () => submitMessage(`${ticket.id} talebimin durumu nedir? Özet: ${ticket.summary}`));
      actions.appendChild(ask);
    }
    row.append(info, actions);
    ticketList.appendChild(row);
  });
}

async function updateTicketStatus(ticketId, status, button = null) {
  const endpoint = isAdmin() ? `/api/admin/tickets/${encodeURIComponent(ticketId)}` : `/api/support/tickets/${encodeURIComponent(ticketId)}`;
  const payload = { status };
  if (isSupport() && status === "in_progress") {
    payload.assignee = currentUser.username;
  }
  const resolutionNote =
    status === "resolved"
      ? prompt("Çözüm notu yazın. Çalışan bu notu kendi talebinde görecek.", "Sorun incelendi ve çözüldü.")
      : null;
  if (status === "resolved" && !resolutionNote) return;
  if (resolutionNote) {
    payload.resolution_note = resolutionNote;
  }
  const originalLabel = button?.textContent;
  if (button) {
    button.disabled = true;
    button.textContent = "İşleniyor";
  }
  ticketOutput.textContent = "";
  try {
    const response = await fetch(endpoint, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload),
    });
    const updated = await response.json();
    if (!response.ok) throw new Error(updated.detail || "Ticket güncellenemedi.");

    ticketOutput.replaceChildren();
    ticketOutput.appendChild(createElement("strong", null, `${updated.id} güncellendi`));
    ticketOutput.appendChild(
      createElement(
        "p",
        null,
        `${ticketStatusLabels[updated.status] || updated.status} · Atanan: ${updated.assignee || "Henüz yok"}`
      )
    );
    if (updated.resolution_note) {
      ticketOutput.appendChild(createElement("span", "mini-line", `Çözüm: ${updated.resolution_note}`));
    }

    const refreshes = [loadTickets()];
    if (isAdmin()) refreshes.push(loadAudit(), loadOverview());
    await Promise.all(refreshes);
  } catch (error) {
    ticketOutput.textContent = error.message || "Ticket güncellenemedi.";
    if (button) {
      button.disabled = false;
      button.textContent = originalLabel;
    }
  }
}

async function createTicketDraft(event) {
  event.preventDefault();
  const message = ticketMessage.value.trim();
  if (!message) return;

  const response = await fetch("/api/tickets", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      message,
      priority: ticketPriority.value,
      requester: canManageTickets() ? ticketRequester.value.trim() || null : null,
    }),
  });
  const ticket = await response.json();
  if (!response.ok) {
    ticketOutput.textContent = ticket.detail || "Ticket açılamadı.";
    return;
  }
  ticketOutput.replaceChildren();
  ticketOutput.appendChild(createElement("strong", null, `${ticket.id} açıldı`));
  ticketOutput.appendChild(createElement("p", null, `${ticket.category} · ${ticket.priority} · ${ticket.status}`));
  ticketOutput.appendChild(createElement("span", "mini-line", ticket.summary));
  ticketMessage.value = "";
  ticketRequester.value = canManageTickets() ? ticketRequester.value : "";
  const refreshes = [loadTickets()];
  if (isAdmin()) refreshes.push(loadOverview(), loadAudit());
  await Promise.all(refreshes);
}

async function addKnowledgeDocument(event) {
  event.preventDefault();
  const title = documentTitle.value.trim();
  const content = documentContent.value.trim();
  if (!title || content.length < 20) return;

  const response = await fetch("/api/admin/documents", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ title, content, category: "Admin" }),
  });
  const result = await response.json();
  if (!response.ok) {
    documentOutput.textContent = result.detail || "Doküman eklenemedi";
    return;
  }
  documentOutput.textContent = `${result.status}: ${result.indexed_chunks} parça indekslendi`;
  documentTitle.value = "";
  documentContent.value = "";
  checkHealth();
  loadOverview();
  loadAudit();
  loadDocuments();
}

async function loadDocuments() {
  const response = await fetch("/api/admin/documents", { headers: authHeaders() });
  if (!response.ok) return;
  const data = await response.json();
  documentList.replaceChildren();

  data.documents.forEach((doc) => {
    const row = createElement("div", "document-item");
    const info = createElement("div", "document-info");
    info.appendChild(createElement("strong", null, doc.title));
    info.appendChild(createElement("span", null, `${doc.category} · ${doc.filename} · ${Math.ceil(doc.size / 1024)} KB`));
    const actions = createElement("div", "inline-actions");
    const remove = createElement("button", null, "Sil");
    remove.type = "button";
    remove.addEventListener("click", () => deleteDocument(doc.filename));
    actions.appendChild(remove);
    row.append(info, actions);
    documentList.appendChild(row);
  });
}

async function deleteDocument(filename) {
  if (!confirm(`${filename} silinsin mi?`)) return;
  const response = await fetch(`/api/admin/documents/${encodeURIComponent(filename)}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  const result = await response.json();
  documentOutput.textContent = response.ok ? `${filename} silindi. ${result.indexed_chunks} parça kaldı.` : result.detail || "Doküman silinemedi.";
  await Promise.all([loadDocuments(), checkHealth(), loadOverview(), loadAudit()]);
}

function scrollToLatest() {
  messages.scrollTop = messages.scrollHeight;
}

authTabs.forEach((tab) => tab.addEventListener("click", () => setAuthMode(tab.dataset.authMode)));
authForm.addEventListener("submit", submitAuth);
logoutButton.addEventListener("click", logout);

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
  loadTickets();
  if (isAdmin()) {
    loadOverview();
    loadAudit();
    loadUsers();
    loadDocuments();
    loadIntegrations();
  }
});
ticketForm.addEventListener("submit", createTicketDraft);
documentForm.addEventListener("submit", addKnowledgeDocument);
userForm.addEventListener("submit", createUser);

setAuthMode("login");
restoreSession();
