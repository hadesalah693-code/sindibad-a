const API = "";
const LANG_KEY = "sindibad_lang";
let dashboardData = null;
let lang = "ar";
let appStarted = false;

const I18N = {
  ar: {
    pageTitle: "سندباد AI | Doha Oasis",
    brandTag: "Executive Intelligence",
    liveKpis: "مؤشرات حية",
    strategicInsights: "رؤى استراتيجية",
    connected: "متصل بقاعدة البيانات",
    emptyTitle: "مستشارك الاستراتيجي جاهز",
    emptyDesc: "اختر أحد التقارير أدناه، أو اكتب سؤالك في الأسفل.",
    heroKpiHint: "اضغط لفتح التقرير ←",
    reportFooter: "سندباد AI · Doha Oasis",
    placeholder: "اكتب سؤالك الاستراتيجي هنا...",
    employees: "موظف",
    departments: "إدارات",
    subtitle: "اختر سؤالاً جاهزاً أو اكتب سؤالك في الأسفل.",
    loadingTitle: "سندباد يحلل البيانات",
    reportSource: "Excel · Doha Oasis",
    sendError: "تعذر الاتصال بالخادم.",
    kpiArrow: "←",
  },
  en: {
    pageTitle: "Sindibad AI | Doha Oasis",
    brandTag: "Executive Intelligence",
    liveKpis: "Live KPIs",
    strategicInsights: "Strategic Insights",
    connected: "Connected to database",
    emptyTitle: "Your strategic advisor is ready",
    emptyDesc: "Pick a report below, or type your question in the composer.",
    heroKpiHint: "Click to open report →",
    reportFooter: "Sindibad AI · Doha Oasis",
    placeholder: "Ask your strategic question here...",
    employees: "employees",
    departments: "departments",
    subtitle: "Pick a ready-made report or type your question below.",
    loadingTitle: "Sindibad is analyzing",
    reportSource: "Excel · Doha Oasis",
    sendError: "Could not connect to the server.",
    kpiArrow: "→",
  },
};

function t(key) {
  return I18N[lang][key] ?? I18N.en[key] ?? key;
}

function pick(obj, arKey, enKey) {
  return lang === "ar" ? obj[arKey] : obj[enKey];
}

function applyShellI18n() {
  const html = document.documentElement;
  html.lang = lang === "ar" ? "ar" : "en";
  html.dir = lang === "ar" ? "rtl" : "ltr";
  document.title = t("pageTitle");

  const brandTag = document.querySelector(".brand-tag");
  if (brandTag) brandTag.textContent = t("brandTag");

  document.getElementById("insightsSectionLabel").textContent = t("strategicInsights");
  document.getElementById("liveBadgeText").textContent = t("connected");
  document.getElementById("emptyTitle").textContent = t("emptyTitle");
  document.getElementById("emptyDesc").innerHTML = t("emptyDesc");
  document.getElementById("queryInput").placeholder = t("placeholder");
  document.querySelector(".loading-title").textContent = t("loadingTitle");
  document.getElementById("langBtn").textContent = lang === "ar" ? "EN" : "AR";
}

function setLanguage(next) {
  lang = next === "en" ? "en" : "ar";
  localStorage.setItem(LANG_KEY, lang);
  applyShellI18n();
  if (dashboardData) renderDashboard();
}

function dismissLangGate() {
  const gate = document.getElementById("langGate");
  const shell = document.getElementById("appShell");
  gate?.classList.add("lang-gate--hide");
  shell?.classList.remove("app-hidden");
  document.body.classList.remove("lang-gate-open");
  window.setTimeout(() => gate?.classList.add("hidden"), 420);
}

function startApp() {
  if (appStarted) return;
  appStarted = true;
  loadDashboard();
}

function initApp() {
  const saved = localStorage.getItem(LANG_KEY);
  const gate = document.getElementById("langGate");
  const shell = document.getElementById("appShell");

  document.querySelectorAll(".lang-pick").forEach((btn) => {
    btn.addEventListener("click", () => {
      setLanguage(btn.dataset.lang);
      dismissLangGate();
      startApp();
    });
  });

  if (saved === "ar" || saved === "en") {
    lang = saved;
    gate?.classList.add("hidden");
    shell?.classList.remove("app-hidden");
    startApp();
    return;
  }

  document.body.classList.add("lang-gate-open");
  shell?.classList.add("app-hidden");
}

function reportProfile(type) {
  return REPORT_PROFILES[type] || REPORT_PROFILES.generic;
}

const REPORT_ACTION_LABELS = {
  costs: {
    primary_ar: "خطة تخفيض التكاليف",
    primary_en: "Cost Reduction Plan",
    primaryStyle: "primary",
  },
  exit_risk: {
    primary_ar: "جدولة مواعيد المتابعة",
    primary_en: "Schedule follow-ups",
    primaryStyle: "danger",
  },
  iso: {
    primary_ar: "خطة تحسين ISO 30414",
    primary_en: "ISO Improvement Plan",
    primaryStyle: "primary",
  },
  correlation: {
    primary_ar: "تحليل ارتباط معمق",
    primary_en: "Deep Correlation Analysis",
    primaryStyle: "primary",
  },
  generic: {
    primary_ar: "تحليل تفصيلي",
    primary_en: "Detailed Analysis",
    primaryStyle: "primary",
  },
  greeting: null,
};

/** Confirmation messages — like demo: click → status pill, not a new report */
const REPORT_ACTION_SUCCESS = {
  costs: {
    full: { ar: "✨ تقرير التكاليف الكامل جاهز.", en: "✨ Full cost report is ready." },
    plan: { ar: "✅ تم إعداد خطة تخفيض التكاليف.", en: "✅ Cost reduction plan prepared." },
  },
  exit_risk: {
    full: { ar: "✨ تقرير مخاطر المغادرة جاهز.", en: "✨ Exit risk report is ready." },
    plan: { ar: "✅ تمت جدولة مواعيد المتابعة.", en: "✅ Follow-up appointments scheduled." },
  },
  iso: {
    full: { ar: "✨ تقرير ISO 30414 جاهز.", en: "✨ ISO 30414 report is ready." },
    plan: { ar: "✅ تم إعداد خطة تحسين ISO 30414.", en: "✅ ISO improvement plan prepared." },
  },
  correlation: {
    full: { ar: "✨ تحليل الارتباط جاهز.", en: "✨ Correlation analysis is ready." },
    plan: { ar: "✅ تم توسيع التحليل.", en: "✅ Analysis expanded." },
  },
  generic: {
    full: { ar: "✨ التقرير جاهز.", en: "✨ Report is ready." },
    plan: { ar: "✅ تم إعداد التحليل التفصيلي.", en: "✅ Detailed analysis prepared." },
  },
};

function renderStandardActionBar(type) {
  const ar = lang === "ar";
  const labels = REPORT_ACTION_LABELS[type];
  if (!labels) return "";
  const primaryLabel = ar ? labels.primary_ar : labels.primary_en;
  const primaryClass = labels.primaryStyle === "danger" ? "rab-danger" : "rab-primary";
  const secondaryLabel = ar ? "عرض التقرير الكامل" : "View full report";
  return `
    <div class="report-action-bar" data-report-type="${esc(type)}">
      <button class="rab-btn rab-outline" type="button" data-report-action="full">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        ${esc(secondaryLabel)}
      </button>
      <button class="rab-btn ${primaryClass}" type="button" data-report-action="plan">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2z"/></svg>
        ${esc(primaryLabel)}
      </button>
      <div class="report-complete-pill hidden" role="status" aria-live="polite">
        <span class="report-complete-text"></span>
      </div>
    </div>`;
}

function showReportActionConfirmation(canvas, action) {
  const bar = canvas.querySelector(".report-action-bar");
  if (!bar || bar.classList.contains("report-action-bar--done")) return;

  const type = bar.dataset.reportType || "generic";
  const msgs = REPORT_ACTION_SUCCESS[type] || REPORT_ACTION_SUCCESS.generic;
  const ar = lang === "ar";
  const text = msgs[action] ? (ar ? msgs[action].ar : msgs[action].en) : (ar ? msgs.full.ar : msgs.full.en);

  bar.querySelectorAll(".rab-btn").forEach((b) => b.classList.add("hidden"));
  const pill = bar.querySelector(".report-complete-pill");
  const pillText = bar.querySelector(".report-complete-text");
  if (pill && pillText) {
    pillText.textContent = text;
    pill.classList.remove("hidden");
  }
  bar.classList.add("report-action-bar--done");
}

function bindReportActions(root) {
  if (!root) return;
  root.querySelectorAll("[data-report-action]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const canvas = btn.closest(".report-canvas");
      if (!canvas) return;
      showReportActionConfirmation(canvas, btn.dataset.reportAction);
    });
  });
}

function wrapReportCanvas({ query, headline, type, theme, bodyHtml }) {
  const profile = reportProfile(type);
  const themeClass = theme || profile.theme || "neutral";
  const title = headline || (lang === "ar" ? profile.labelAr : profile.labelEn);
  const completeBar = renderStandardActionBar(type);
  return `
    <div class="chat-turn turn-${type}">
      <article class="report-canvas">
        <header class="report-canvas-head ${themeClass}">
          <div class="rc-head-icon">${profile.icon}</div>
          <div class="rc-head-text">
            <h3>${esc(title)}</h3>
            <div class="rc-head-meta">
              <span class="query-chip">${esc(query)}</span>
              <span>${nowTime()}</span>
            </div>
          </div>
          <span class="rc-head-badge">${t("reportSource")}</span>
        </header>
        <div class="report-canvas-body">${bodyHtml}</div>
        ${completeBar}
        <footer class="report-canvas-foot">
          <span>${t("reportFooter")}</span>
          <span>${nowTime()}</span>
        </footer>
      </article>
    </div>`;
}

function bindQueryElements(root = document) {
  root.querySelectorAll("[data-query]").forEach((el) => {
    el.addEventListener("click", () => ask(decodeURIComponent(el.dataset.query)));
  });
}

function greeting() {
  const h = new Date().getHours();
  if (lang === "ar") {
    if (h < 12) return "صباح الخير — لوحة القيادة";
    if (h < 17) return "مرحباً بك في سندباد";
    return "مساء الخير — لوحة القيادة";
  }
  if (h < 12) return "Good morning — Command Center";
  return "Welcome to Sindibad";
}

const REPORT_PROFILES = {
  costs: {
    minMs: 3400,
    theme: "danger",
    icon: "💰",
    labelAr: "تقرير مالي",
    labelEn: "Financial Report",
    stepsAr: [
      "جاري قراءة ورقة Finance من Excel...",
      "حساب التكاليف القابلة للتجنب...",
      "تجميع النتائج حسب الإدارة...",
      "إعداد التقرير التنفيذي...",
    ],
    stepsEn: ["Reading Finance sheet...", "Calculating avoidable costs...", "Grouping by department...", "Preparing report..."],
  },
  exit_risk: {
    minMs: 3800,
    theme: "warning",
    icon: "👥",
    labelAr: "رادار المواهب",
    labelEn: "Talent Radar",
    stepsAr: [
      "جاري قراءة بيانات Employees...",
      "تحليل مخاطر المغادرة...",
      "تحديد الموظفين عاليي الخطر...",
      "بناء خطة التدخّل...",
    ],
    stepsEn: ["Reading Employees sheet...", "Analyzing exit risk...", "Identifying high-risk staff...", "Building action plan..."],
  },
  iso: {
    minMs: 3600,
    theme: "success",
    icon: "✓",
    labelAr: "امتثال ISO 30414",
    labelEn: "ISO 30414 Compliance",
    stepsAr: [
      "جاري قراءة Evidence_Readiness...",
      "مراجعة حالة الأدلة...",
      "تقييم المخاطر والفجوات...",
      "إعداد ملخص الاستعداد...",
    ],
    stepsEn: ["Reading Evidence_Readiness...", "Reviewing evidence status...", "Assessing risks...", "Preparing readiness summary..."],
  },
  correlation: {
    minMs: 3200,
    theme: "accent",
    icon: "↔",
    labelAr: "تحليل الارتباط",
    labelEn: "Correlation Insight",
    stepsAr: [
      "جاري قراءة Dashboard من Excel...",
      "حساب معامل الارتباط...",
      "مقارنة المقاييس المترابطة...",
      "صياغة التوصية الاستراتيجية...",
    ],
    stepsEn: ["Reading Dashboard sheet...", "Computing correlation...", "Comparing linked metrics...", "Drafting recommendation..."],
  },
  generic: {
    minMs: 2800,
    theme: "neutral",
    icon: "📊",
    labelAr: "تحليل استراتيجي",
    labelEn: "Strategic Analysis",
    stepsAr: [
      "جاري قراءة Correlation_Data...",
      "تحليل المقاييس المطلوبة...",
      "استخراج الرؤى...",
    ],
    stepsEn: ["Reading Correlation_Data...", "Analyzing requested metrics...", "Extracting insights..."],
  },
  greeting: {
    minMs: 900,
    theme: "accent",
    icon: "✦",
    labelAr: "تحية",
    labelEn: "Greeting",
    stepsAr: ["مرحباً بك في سندباد...", "جاري تجهيز الرؤى العاجلة..."],
    stepsEn: ["Welcome to Sindibad...", "Preparing urgent insights..."],
  },
};

function detectQueryProfile(query) {
  const q = query.toLowerCase();
  if (/السلام عليكم|سلام عليكم|assalamu alaikum|assalam alaikum|salam alaikum|^hello$|good morning|good afternoon|good evening/.test(q)) return "greeting";
  if (/تكلف|تكاليف|للتجنب|avoidable|cost|ميزان|overtime|turnover cost/.test(q)) return "costs";
  if (/مغادر|exit risk|attrition|مخاطر مغادر/.test(q) || (/موظف/.test(q) && /مخاطر|risk|مغادر|خط/.test(q))) return "exit_risk";
  if (/30414|iso|آيزو|evidence|readiness|استعداد/.test(q)) return "iso";
  if (/علاقة|العلاقة|ارتباط|correlat|relationship/.test(q)) return "correlation";
  return "generic";
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function nowTime() {
  return new Date().toLocaleTimeString(lang === "ar" ? "ar-QA" : "en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function chartColor() {
  return getComputedStyle(document.documentElement).getPropertyValue("--text").trim() || "#0f172a";
}

function stripMarkdown(text) {
  return (text || "")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/^## .+\n*/gm, "")
    .replace(/^> /gm, "")
    .replace(/^- /gm, "• ");
}

function renderRichSummary(text) {
  return stripMarkdown(text).replace(/\n/g, "<br/>");
}

function renderReportHeader(type, headline, ar) {
  const profile = REPORT_PROFILES[type] || REPORT_PROFILES.generic;
  const label = headline || (ar ? profile.labelAr : profile.labelEn);
  return `
    <div class="report-header ${profile.theme}">
      <span class="rh-icon">${profile.icon}</span>
      <div class="rh-text">
        <strong>${esc(label)}</strong>
        <span class="rh-source">${esc(t("reportSource"))}</span>
      </div>
    </div>`;
}

function renderStatsBar(stats) {
  if (!stats?.length) return "";
  return `
    <div class="stats-bar">
      ${stats.map((s) => `
        <div class="stat-item ${s.theme || ""}">
          <span class="stat-val">${esc(s.value)}</span>
          <span class="stat-lbl">${esc(s.label)}</span>
        </div>`).join("")}
    </div>`;
}

async function runLoadingAnimation(profileKey) {
  const profile = REPORT_PROFILES[profileKey] || REPORT_PROFILES.generic;
  const ar = lang === "ar";
  const steps = ar ? profile.stepsAr : profile.stepsEn;
  const stepsEl = document.getElementById("loadingSteps");
  const barEl = document.getElementById("loadingBar");
  const titleEl = document.querySelector(".loading-title");

  titleEl.textContent = t("loadingTitle");
  stepsEl.innerHTML = steps.map((s, i) => `<li data-i="${i}">${esc(s)}</li>`).join("");
  barEl.style.width = "0%";

  const overlay = document.getElementById("loading");
  overlay.classList.remove("hidden");

  const stepMs = profile.minMs / steps.length;
  const start = Date.now();

  for (let i = 0; i < steps.length; i++) {
    stepsEl.querySelectorAll("li").forEach((li, j) => {
      li.classList.toggle("done", j < i);
      li.classList.toggle("active", j === i);
    });
    barEl.style.width = `${Math.round(((i + 1) / steps.length) * 100)}%`;
    await sleep(stepMs);
  }

  const elapsed = Date.now() - start;
  if (elapsed < profile.minMs) await sleep(profile.minMs - elapsed);

  stepsEl.querySelectorAll("li").forEach((li) => li.classList.add("done"));
  barEl.style.width = "100%";
  await sleep(280);
  overlay.classList.add("hidden");
}

function renderStrategyCard(html, ar) {
  const title = ar ? "توصية استراتيجية" : "Strategic Recommendation";
  const heading = ar ? "التوصية الاستراتيجية:" : "Strategic Recommendation:";
  return `
    <p class="strategy-heading">${heading}</p>
    <div class="strategy-card">
      <div class="strategy-header">
        <span class="strategy-icon">💡</span>
        <strong>${title}</strong>
      </div>
      <div class="strategy-body">${html}</div>
    </div>`;
}

async function loadDashboard() {
  const res = await fetch(`${API}/api/v1/dashboard`);
  dashboardData = await res.json();
  renderDashboard();
}

function renderDashboard() {
  applyShellI18n();
  const c = dashboardData.company;
  const companyName = lang === "ar" ? c.name_ar : c.name_en;
  document.getElementById("companyMeta").innerHTML = `
    <span class="co-chip"><strong>${companyName}</strong></span>
    <span class="co-chip">FY <strong>${c.fiscal_year}</strong></span>
    <span class="co-chip"><strong>${c.employees.toLocaleString()}</strong> ${t("employees")}</span>
    <span class="co-chip"><strong>${c.departments}</strong> ${t("departments")}</span>
  `;

  document.getElementById("greeting").textContent = greeting();
  document.getElementById("subtitle").textContent = t("subtitle");

  const queries = {};
  dashboardData.preset_questions.forEach((q) => {
    queries[q.id] = pick(q, "query_ar", "query_en");
  });

  const kpiIcons = { costs: "💰", exit_risk: "👥", iso: "✓" };

  document.getElementById("heroKpiRow").innerHTML = dashboardData.kpis
    .map((k) => {
      const label = pick(k, "label_ar", "label_en");
      const value = k.value_en && lang === "en" ? k.value_en : (k.value_ar || k.value);
      return `
    <button class="hero-kpi ${k.theme}" type="button" data-query="${encodeURIComponent(queries[k.id] || "")}">
      <div class="hero-kpi-icon">${kpiIcons[k.id] || "●"}</div>
      <div class="hero-kpi-body">
        <div class="hero-kpi-label">${label}</div>
        <div class="hero-kpi-value">${value}</div>
        <div class="hero-kpi-hint">${t("heroKpiHint")}</div>
      </div>
    </button>`;
    })
    .join("");

  document.getElementById("presetCards").innerHTML = dashboardData.preset_questions
    .map(
      (q) => `
    <button class="insight-item ${q.theme}" type="button" data-query="${encodeURIComponent(pick(q, "query_ar", "query_en"))}">
      <span class="nav-icon">${q.icon}</span>
      <div class="nav-text">
        <h4>${pick(q, "title_ar", "title_en")}</h4>
        <p>${pick(q, "subtitle_ar", "subtitle_en")}</p>
      </div>
    </button>`
    )
    .join("");

  const greetingTag = dashboardData.quick_tags.find((tag) => tag.label_ar === "تحية" || tag.label_en === "Greeting");
  const promptItems = [
    ...dashboardData.preset_questions.map((q) => ({
      theme: q.theme,
      icon: q.icon,
      title: pick(q, "title_ar", "title_en"),
      sub: pick(q, "subtitle_ar", "subtitle_en"),
      query: pick(q, "query_ar", "query_en"),
      wide: false,
    })),
    ...(greetingTag
      ? [{
          theme: "accent",
          icon: "👋",
          title: pick(greetingTag, "label_ar", "label_en"),
          sub: lang === "ar" ? "تحية وتوجيه تنفيذي" : "Executive briefing",
          query: pick(greetingTag, "query_ar", "query_en"),
          wide: true,
        }]
      : []),
  ];

  document.getElementById("promptGrid").innerHTML = promptItems
    .map(
      (p) => `
    <button class="prompt-card ${p.theme}${p.wide ? " wide" : ""}" type="button" data-query="${encodeURIComponent(p.query)}">
      <span class="prompt-card-icon">${p.icon}</span>
      <span class="prompt-card-title">${esc(p.title)}</span>
      <span class="prompt-card-sub">${esc(p.sub)}</span>
    </button>`
    )
    .join("");

  document.getElementById("composerTags").innerHTML = dashboardData.quick_tags
    .map(
      (tag) =>
        `<button class="tag" type="button" data-query="${encodeURIComponent(pick(tag, "query_ar", "query_en"))}">${pick(tag, "label_ar", "label_en")}</button>`
    )
    .join("");

  bindQueryElements(document.getElementById("heroKpiRow"));
  bindQueryElements(document.getElementById("presetCards"));
  bindQueryElements(document.getElementById("promptGrid"));
  bindQueryElements(document.getElementById("composerTags"));
}

function renderHeroMetric(hero, theme) {
  if (!hero) return "";
  return `
    <div class="hero-metric ${theme}">
      <div class="hero-row">
        <span class="hero-icon">${hero.icon || "⚠"}</span>
        <span class="hero-label">${esc(hero.label)}:</span>
        <span class="hero-value">${esc(hero.value)}</span>
      </div>
      ${hero.breakdown ? `<div class="hero-breakdown">${esc(hero.breakdown)}</div>` : ""}
    </div>`;
}

function renderMetricsGrid(metrics, premium = false) {
  if (!metrics?.length) return "";
  const cls = premium ? "insight-grid" : "metrics-grid";
  return `
    <div class="${cls}">
      ${metrics.map((m) => `
        <div class="metric-card ${m.theme || ""}${premium ? " premium" : ""}">
          ${m.icon ? `<span class="mc-icon">${m.icon}</span>` : ""}
          <div class="mc-label">${esc(m.label)}</div>
          <div class="mc-value">${esc(m.value)}</div>
          <div class="mc-sub">${esc(m.sub)}</div>
        </div>`).join("")}
    </div>`;
}

function renderEmployeeAlerts(alerts, ar) {
  if (!alerts?.length) return "";
  const urgentLabel = ar ? "تنبيه عاجل" : "Urgent Alert";
  const riskLabel = ar ? "خطر مغادرة مرتفع" : "High Exit Risk";
  const recLabel = ar ? "التوصية:" : "Recommendation:";
  const scoreLabel = ar ? "درجة الخطر/100" : "Risk/100";

  return `
    <div class="alert-cards">
      ${alerts.map((a) => `
        <div class="alert-card">
          <div class="alert-card-top">
            <div class="alert-score">
              <span class="score-num">${a.score}</span>
              <span class="score-label">${scoreLabel}</span>
            </div>
            <div class="alert-main">
              <div class="alert-badge">
                <span class="dot"></span>
                ${urgentLabel} — ${a.index}/${a.total} — ${riskLabel}
              </div>
              <div class="alert-name">
                ${esc(a.name)} <span>(${esc(a.employee_id)})</span>
              </div>
              <div class="alert-dept">${esc(a.department)}${a.job_title ? ` · ${esc(a.job_title)}` : ""}</div>
              <div class="alert-reasons">
                ${(a.reasons || []).map((r) => `<span class="reason-chip">${esc(r)}</span>`).join("")}
              </div>
            </div>
          </div>
          <div class="alert-card-footer">
            <strong>${recLabel}</strong>${esc(a.recommendation)}
          </div>
        </div>`).join("")}
    </div>`;
}

function renderActionBar(actions) {
  if (!actions?.length) return "";
  return `
    <div class="action-bar">
      ${actions.map((a) => `
        <button class="action-btn ${a.style || "outline"}" type="button">${esc(a.label)}</button>
      `).join("")}
    </div>`;
}

function renderListCard(title, items, theme) {
  if (!items?.length) return "";
  return `
    <div class="list-card">
      <div class="list-card-header ${theme}">
        <span class="header-icon">⚠</span>
        <span>${esc(title)}</span>
      </div>
      ${items.map((item) => `
        <div class="list-row">
          <div class="list-avatar ${theme}">${esc(item.letter || "?")}</div>
          <div class="list-info">
            <div class="name">${esc(item.name)}</div>
            ${item.subtitle ? `<div class="sub">${esc(item.subtitle)}</div>` : ""}
          </div>
          <div class="list-value ${theme}">${esc(item.value)}</div>
        </div>`).join("")}
    </div>`;
}

function statusClass(status) {
  const s = String(status || "").toLowerCase();
  if (s.includes("validated") && !s.includes("partial")) return "validated";
  if (s.includes("partial")) return "partial";
  return "progress";
}

function riskClass(risk) {
  const r = String(risk || "").toLowerCase();
  if (r === "high") return "high";
  if (r === "medium") return "medium";
  return "low";
}

function renderIsoTable(table, meta) {
  if (!table?.length) return "";
  const title = meta?.title || "ISO 30414 Readiness by Area";
  const badge = meta?.badge || table.length;

  return `
    <div class="iso-table-card">
      <div class="iso-table-header">
        <h4>${esc(title)}</h4>
        <span class="iso-badge">${badge}</span>
      </div>
      <div style="overflow-x:auto">
        <table class="iso-table">
          <thead>
            <tr>
              <th>Area</th>
              <th>Status</th>
              <th>Risk</th>
              <th>Complete</th>
            </tr>
          </thead>
          <tbody>
            ${table.map((row) => {
              let pct = row["Completeness %"];
              if (typeof pct === "number" && pct <= 1) pct = pct * 100;
              else pct = parseFloat(pct) || 0;
              const fillClass = pct >= 70 ? "good" : pct >= 40 ? "mid" : "";
              const status = row["Validation Status"] || "—";
              const risk = row["Risk Level"] || "—";
              return `
              <tr>
                <td>${esc(row["ISO Area"])}</td>
                <td><span class="status-pill ${statusClass(status)}">${esc(status)}</span></td>
                <td><span class="risk-text ${riskClass(risk)}">${esc(risk)}</span></td>
                <td>
                  <div class="progress-cell">
                    <div class="progress-bar"><div class="progress-fill ${fillClass}" style="width:${Math.min(pct, 100)}%"></div></div>
                    <span class="progress-pct">${pct.toFixed(0)}%</span>
                  </div>
                </td>
              </tr>`;
            }).join("")}
          </tbody>
        </table>
      </div>
    </div>`;
}

function renderGenericTable(table) {
  if (!table?.length) return "";
  const keys = Object.keys(table[0]);
  const labels = {
    Employee_Name: "الاسم", Department: "الإدارة", Job_Title: "المسمى",
    Engagement_Score: "المشاركة", Performance_Score: "الأداء",
    department: "الإدارة", turnover: "الدوران", overtime: "الإضافي",
    recruitment: "التوظيف", total: "الإجمالي",
  };
  return `
    <div class="list-card">
      <table class="iso-table">
        <thead><tr>${keys.map((k) => `<th>${esc(labels[k] || k)}</th>`).join("")}</tr></thead>
        <tbody>${table.map((row) => `
          <tr>${keys.map((k) => {
            let v = row[k];
            if (typeof v === "number" && k.includes("total")) v = v.toLocaleString();
            return `<td>${esc(v ?? "—")}</td>`;
          }).join("")}</tr>`).join("")}
        </tbody>
      </table>
    </div>`;
}

function plotLayout(title, compact, showLegend = false) {
  const c = chartColor();
  return {
    title: title ? { text: title, font: { family: "IBM Plex Sans Arabic", size: compact ? 11 : 13, color: c } } : undefined,
    margin: compact ? { t: 28, r: 8, b: 48, l: 40 } : { t: 44, r: 16, b: 64, l: 48 },
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { family: "IBM Plex Sans Arabic", color: c, size: compact ? 10 : 11 },
    xaxis: { tickangle: -25, gridcolor: "rgba(148,163,184,0.1)", showgrid: false },
    yaxis: { gridcolor: "rgba(148,163,184,0.1)" },
    showlegend: showLegend,
    legend: showLegend ? { orientation: "h", y: 1.15, x: 0, font: { size: 10 } } : undefined,
    barmode: showLegend ? "group" : undefined,
  };
}

function mountChart(containerId, chartData, theme) {
  if (chartData.type === "grouped_bar" && chartData.series) {
    mountGroupedChart(containerId, chartData);
    return;
  }
  const colors = { danger: "#f87171", warning: "#fbbf24", success: "#34d399" };
  const color = chartData.color || colors[theme] || "#6366f1";
  Plotly.newPlot(
    containerId,
    [{ x: chartData.labels, y: chartData.values, type: "bar", marker: { color, opacity: 0.85 } }],
    plotLayout(chartData.title, true),
    { responsive: true, displayModeBar: false }
  );
}

function mountGroupedChart(containerId, chartData) {
  const traces = chartData.series.map((s) => ({
    x: chartData.labels,
    y: s.values,
    name: s.name,
    type: "bar",
    marker: { color: s.color, opacity: 0.88 },
  }));
  Plotly.newPlot(
    containerId,
    traces,
    plotLayout(chartData.title, true, true),
    { responsive: true, displayModeBar: false }
  );
}

function mountPlotlyChart(containerId, figure, title) {
  Plotly.newPlot(
    containerId,
    figure.data,
    { ...figure.layout, ...plotLayout(title, false) },
    { responsive: true, displayModeBar: false }
  );
}

function renderChartBlock(chartData, chartId, theme, wide = false) {
  if (!chartData) return { html: "", chartId: null };
  const legend = chartData.series
    ? `<div class="chart-legend">${chartData.series.map((s) => `<span><i style="background:${s.color}"></i>${esc(s.name)}</span>`).join("")}</div>`
    : "";
  return {
    html: `
      <div class="chart-card ${theme} ${wide ? "wide" : ""}">
        <div class="chart-card-title">${esc(chartData.title)}</div>
        ${legend}
        <div id="${chartId}" style="height:${wide ? 260 : 220}px"></div>
      </div>`,
    chartId,
  };
}

function buildChatTurn(query, data) {
  const ui = data.ui || {};
  const theme = ui.theme || "success";
  const type = data.response_type || data.metadata?.type || "generic";
  const layout = ui.layout || type;
  const ar = lang === "ar";
  const chartId = `chart-${Date.now()}`;

  const isCorrelation = type === "correlation" || layout === "correlation";
  const isExitRisk = type === "exit_risk" || layout === "employee_alerts";
  const isCosts = type === "costs" || layout === "costs_report";
  const isIso = type === "iso" || layout === "iso_compliance";
  const isGreeting = type === "greeting" || layout === "greeting";

  if (isGreeting) {
    const messages = ui.messages || [data.executive_summary || ""];
    const bodyHtml = `
      <div class="greeting-content">
        ${messages.map((msg) => `<div class="greeting-bubble report-section">${renderRichSummary(msg)}</div>`).join("")}
      </div>`;

    return {
      html: wrapReportCanvas({
        query,
        headline: data.headline || (ar ? "تحية وتوجيه" : "Greeting & Briefing"),
        type: "greeting",
        theme: "accent",
        bodyHtml,
      }),
      chartId: null,
      chartData: null,
      plotlyChart: null,
      theme,
      extraCharts: [],
    };
  }

  if (isCosts) {
    let bodyHtml = `<div class="report-section costs-intro">${renderRichSummary(data.executive_summary || "")}</div>`;
    const chartBlock = renderChartBlock(data.simple_chart || data.chart, chartId, theme, false);
    bodyHtml += chartBlock.html;
    if (ui.list_items?.length) {
      bodyHtml += renderListCard(ui.list_title || data.headline, ui.list_items, theme);
    }

    return {
      html: wrapReportCanvas({
        query,
        headline: data.headline,
        type: "costs",
        theme,
        bodyHtml,
      }),
      chartId: chartBlock.chartId,
      chartData: chartBlock.chartId ? (data.simple_chart || data.chart) : null,
      plotlyChart: null,
      theme,
      extraCharts: [],
    };
  }

  const summary = isCorrelation
    ? renderRichSummary(data.executive_summary || "")
    : stripMarkdown(data.executive_summary || data.display_markdown || "");

  let bodyHtml = `<div class="report-section type-${type}${isCorrelation ? " insight-bubble" : ""}">${summary}</div>`;
  let chartPayload = null;
  let plotlyChart = null;

  if (isExitRisk) {
    if (ui.stats?.length) bodyHtml += renderStatsBar(ui.stats);
    bodyHtml += renderEmployeeAlerts(ui.employee_alerts, ar);
    bodyHtml += renderActionBar(ui.actions);
    const chartBlock = renderChartBlock(data.simple_chart || data.chart, chartId, theme, true);
    bodyHtml += chartBlock.html;
    chartPayload = data.simple_chart || data.chart;
  } else if (isCorrelation) {
    if (ui.metrics?.length) bodyHtml += renderMetricsGrid(ui.metrics, true);
    const recHtml = ui.recommendation_html || data.strategic_actions?.[0] || "";
    if (recHtml) bodyHtml += renderStrategyCard(renderRichSummary(recHtml), ar);
  } else if (isIso) {
    if (ui.metrics?.length) bodyHtml += renderMetricsGrid(ui.metrics, true);
    if (data.table) bodyHtml += renderIsoTable(data.table, ui.table_meta);
    if (data.strategic_actions?.length) {
      bodyHtml += renderStrategyCard(esc(data.strategic_actions[0]), ar);
    }
  } else {
    if (ui.metrics?.length) bodyHtml += renderMetricsGrid(ui.metrics);
    if (ui.hero) bodyHtml += renderHeroMetric(ui.hero, theme);
    const chartBlock = renderChartBlock(data.simple_chart, chartId, theme, false);
    bodyHtml += chartBlock.html;
    chartPayload = data.simple_chart;
    if (data.key_findings?.length) {
      bodyHtml += `<ul class="findings-list">${data.key_findings.slice(0, 5).map((f) => `<li>${stripMarkdown(f)}</li>`).join("")}</ul>`;
    }
    if (data.strategic_actions?.length) {
      bodyHtml += renderStrategyCard(esc(data.strategic_actions[0]), ar);
    }
  }

  const extraCharts = [];
  const chartsList = data.charts_meta?.length
    ? data.charts_meta
    : (data.charts || []).map((c, i) => ({ figure: c, title: lang === "ar" ? `رسم ${i + 1}` : `Chart ${i + 1}` }));

  if (!isExitRisk && !isCorrelation && !isCosts && !isIso) {
    chartsList.forEach((c, i) => {
      const id = `extra-${Date.now()}-${i}`;
      extraCharts.push({ id, figure: c.figure, title: c.title });
      bodyHtml += `
        <div class="chart-card">
          <div class="chart-card-title">${esc(c.title)}</div>
          <div id="${id}" style="height:280px"></div>
        </div>`;
    });
  }

  if (isExitRisk || isCosts) {
    /* chartPayload set above */
  } else if (isCorrelation && ui.show_chart !== false && data.charts_meta?.length) {
    plotlyChart = data.charts_meta[0];
  } else if (!isCorrelation && !isIso) {
    /* chartPayload set above */
  }

  const reportType = isExitRisk ? "exit_risk" : isIso ? "iso" : isCorrelation ? "correlation" : type;

  return {
    html: wrapReportCanvas({
      query,
      headline: data.headline,
      type: reportType,
      theme,
      bodyHtml,
    }),
    chartId: chartPayload || plotlyChart ? chartId : null,
    chartData: chartPayload,
    plotlyChart,
    theme,
    extraCharts,
  };
}

async function ask(query) {
  if (!query.trim()) return;
  document.getElementById("queryInput").value = query;

  const profileKey = detectQueryProfile(query);

  try {
    const [data] = await Promise.all([
      fetch(`${API}/api/v1/advise`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, include_charts: true, language: lang }),
      }).then((r) => r.json()),
      runLoadingAnimation(profileKey),
    ]);
    showResponse(query, data);
  } catch {
    document.getElementById("loading").classList.add("hidden");
    showResponse(query, { executive_summary: t("sendError"), grounded: false });
  }
}

function scrollToReportStart(reportEl) {
  if (!reportEl) return;
  const scrollHost = document.getElementById("workspaceBody");
  const anchor = reportEl.querySelector(".report-canvas-head") || reportEl;
  if (scrollHost) {
    const top =
      anchor.getBoundingClientRect().top -
      scrollHost.getBoundingClientRect().top +
      scrollHost.scrollTop -
      16;
    scrollHost.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
    return;
  }
  anchor.scrollIntoView({ behavior: "smooth", block: "start" });
}

function showResponse(query, data) {
  document.getElementById("emptyState").classList.add("hidden");
  const feed = document.getElementById("chatFeed");
  feed.classList.remove("hidden");

  const turn = buildChatTurn(query, data);
  feed.insertAdjacentHTML("beforeend", turn.html);
  const reportEl = feed.lastElementChild;
  if (reportEl) bindReportActions(reportEl);
  scrollToReportStart(reportEl);

  if (turn.chartId && turn.chartData) {
    setTimeout(() => mountChart(turn.chartId, turn.chartData, turn.theme), 80);
  } else if (turn.chartId && turn.plotlyChart) {
    setTimeout(
      () => mountPlotlyChart(turn.chartId, turn.plotlyChart.figure, turn.plotlyChart.title),
      80
    );
  }

  turn.extraCharts.forEach((c, i) => {
    setTimeout(() => mountPlotlyChart(c.id, c.figure, c.title), 120 * (i + 1));
  });
}

document.getElementById("sendBtn").addEventListener("click", () => ask(document.getElementById("queryInput").value));
document.getElementById("queryInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter") ask(e.target.value);
});

document.getElementById("themeBtn").addEventListener("click", () => {
  const html = document.documentElement;
  html.setAttribute("data-theme", html.getAttribute("data-theme") === "dark" ? "light" : "dark");
});

document.getElementById("langBtn").addEventListener("click", () => {
  setLanguage(lang === "ar" ? "en" : "ar");
});

// ── Mobile sidebar toggle ──
(function () {
  const toggle  = document.getElementById("menuToggle");
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebarOverlay");
  const closeBtn = document.getElementById("sidebarClose");

  function openSidebar() {
    sidebar.classList.add("open");
    overlay.classList.add("active");
    document.body.style.overflow = "hidden";
  }
  function closeSidebar() {
    sidebar.classList.remove("open");
    overlay.classList.remove("active");
    document.body.style.overflow = "";
  }

  if (toggle)  toggle.addEventListener("click", openSidebar);
  if (closeBtn) closeBtn.addEventListener("click", closeSidebar);
  if (overlay) overlay.addEventListener("click", closeSidebar);

  // Close on Escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeSidebar();
  });

  // Auto-close sidebar when a preset is clicked on mobile
  document.addEventListener("click", (e) => {
    const item = e.target.closest(".insight-item, .kpi-item");
    if (item && window.innerWidth <= 768) closeSidebar();
  });
})();

initApp();
