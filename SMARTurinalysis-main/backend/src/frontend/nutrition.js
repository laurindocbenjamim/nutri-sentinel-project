/**
 * NutriSentinel — Nutritional Agents Frontend
 * WebSocket-driven pipeline with progress bar and modern block layout.
 */

// ── Biomarker → UrinalysisData mapping ────────────────────────────────────────
const BIOMARKER_FIELD_MAP = {
  "Glicose": "Glucose", "Glucose": "Glucose",
  "Corpos Cetónicos": "Ketone", "Cetona": "Ketone",
  "Proteína": "Protein", "Proteínas": "Protein",
  "Leucócitos": "Leukocytes",
  "Nitritos": "Nitrite",
  "pH": "pHValue",
  "Densidade": "SpecificGravity",
};

const SAFE_DEFAULTS = {
  Glucose: "Negative", Ketone: "Negative", Protein: "Negative",
  Leukocytes: "Negative", Nitrite: "Negative",
  pHValue: 7.0, SpecificGravity: 1.015,
};

function normalizeValue(field, raw) {
  const val = (raw || "").trim();
  if (field === "pHValue" || field === "SpecificGravity") {
    const n = parseFloat(val.replace(",", "."));
    return isNaN(n) ? SAFE_DEFAULTS[field] : n;
  }
  if (field === "Leukocytes") {
    const n = parseFloat(val.split(" ")[0].replace(",", "."));
    if (!isNaN(n) && n < 50) return (n >= 4 && n <= 11) ? "Negative" : "Positive";
    return val || SAFE_DEFAULTS[field];
  }
  if (field === "Glucose") {
    const n = parseFloat(val.split(" ")[0].replace(",", "."));
    if (!isNaN(n)) {
      if (n <= 110) return "Negative";
      if (n <= 180) return "Trace";
      if (n <= 250) return "+";
      if (n <= 350) return "++";
      return "+++";
    }
  }
  return val || SAFE_DEFAULTS[field];
}

function mapBiomarkersToUrinalysis(biomarkers) {
  const result = { ...SAFE_DEFAULTS };
  (biomarkers || []).forEach(({ biomarker, value }) => {
    for (const [ptName, field] of Object.entries(BIOMARKER_FIELD_MAP)) {
      if (biomarker.toLowerCase().includes(ptName.toLowerCase())) {
        result[field] = normalizeValue(field, value);
        break;
      }
    }
  });
  return result;
}

function mapUrinalysisResultsToData(results) {
  const m = { ...SAFE_DEFAULTS };
  const vals = results || {};
  if (vals.Glucose)        m.Glucose = normalizeValue("Glucose", String(vals.Glucose.value || "Negative"));
  if (vals.Ketone)         m.Ketone  = vals.Ketone.value || "Negative";
  if (vals.Protein)        m.Protein = vals.Protein.value || "Negative";
  if (vals.Leukocytes)     m.Leukocytes = vals.Leukocytes.value || "Negative";
  if (vals.Nitrite)        m.Nitrite    = vals.Nitrite.value || "Negative";
  if (vals.pHValue)        m.pHValue    = parseFloat(String(vals.pHValue.value)) || 7.0;
  if (vals.SpecificGravity) m.SpecificGravity = parseFloat(String(vals.SpecificGravity.value)) || 1.015;
  return m;
}

// ── Shared state (set from other panels before navigating) ────────────────────
window._nutriData = window._nutriData || {};

function setNutriData(source, data, urinalysis) {
  window._nutriData = { source, data, urinalysis };
}

// ── DOM helpers ───────────────────────────────────────────────────────────────
function el(id) { return document.getElementById(id); }
function show(id) { el(id)?.classList.remove("hidden"); }
function hide(id) { el(id)?.classList.add("hidden"); }

// ── Progress bar control ──────────────────────────────────────────────────────
const STEPS = [
  { icon: "🛡️", label: "Gatekeeper" },
  { icon: "🔍", label: "Router & DB" },
  { icon: "🧬", label: "Specialists" },
  { icon: "🍽️", label: "Diet Builder" },
  { icon: "🔎", label: "Auditor" },
  { icon: "✅", label: "Delivery" },
];

function renderStepsPipeline() {
  const container = el("nutr-pipeline-steps");
  if (!container) return;
  container.innerHTML = STEPS.map((s, i) => `
    <div class="pipeline-step" id="pipe-step-${i + 1}">
      <div class="step-icon">${s.icon}</div>
      <div class="step-label">${s.label}</div>
    </div>
  `).join('<div class="pipe-connector"></div>');
}

function updateProgress(percent, label, activeStep) {
  const bar = el("nutr-progress-bar");
  const pct = el("nutr-progress-pct");
  const lbl = el("nutr-progress-label");
  if (bar) bar.style.width = `${percent}%`;
  if (pct) pct.textContent = `${percent}%`;
  if (lbl) lbl.textContent = label;

  STEPS.forEach((_, i) => {
    const step = el(`pipe-step-${i + 1}`);
    if (!step) return;
    step.classList.toggle("active", i + 1 === activeStep);
    step.classList.toggle("done", i + 1 < activeStep);
  });
}

// ── Render approved plan ──────────────────────────────────────────────────────
const DAY_LABELS = {
  monday: "Monday", tuesday: "Tuesday", wednesday: "Wednesday",
  thursday: "Thursday", friday: "Friday", saturday: "Saturday", sunday: "Sunday"
};
const MEAL_LABELS = {
  pequeno_almoco: "🌅 Breakfast", almoco: "☀️ Lunch",
  lanche: "🍎 Snack", jantar: "🌙 Dinner"
};

function renderPlan(plan) {
  const summary = plan.diet_summary || {};
  const macros  = summary.macro_distribution || {};
  const finance = plan.financial_metrics || {};
  const weekly  = plan.weekly_plan || {};

  // Summary blocks
  el("nutr-diet-type").textContent     = summary.diet_type    || "—";
  el("nutr-calories").textContent      = `${summary.target_calories_kcal || "—"} kcal`;
  el("nutr-carbs").textContent         = `${macros.carbohydrates_g || "—"} g`;
  el("nutr-protein").textContent       = `${macros.proteins_g || "—"} g`;
  el("nutr-fat").textContent           = `${macros.fats_g || "—"} g`;
  el("nutr-budget-tier").textContent   = finance.user_budget_tier || "—";
  el("nutr-weekly-cost").textContent   = `~€${finance.estimated_weekly_cost_eur || "—"}`;

  // Weekly plan tabs
  const tabsEl   = el("nutr-day-tabs");
  const contentEl = el("nutr-day-content");
  tabsEl.innerHTML = "";
  contentEl.innerHTML = "";

  const days = Object.keys(weekly);
  days.forEach((day, idx) => {
    // Tab button
    const btn = document.createElement("button");
    btn.className = "nutr-day-tab" + (idx === 0 ? " active" : "");
    btn.textContent = DAY_LABELS[day] || day;
    btn.dataset.day = day;
    btn.addEventListener("click", () => {
      document.querySelectorAll(".nutr-day-tab").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      document.querySelectorAll(".nutr-day-panel").forEach(p => p.classList.add("hidden"));
      el(`nutr-day-${day}`)?.classList.remove("hidden");
    });
    tabsEl.appendChild(btn);

    // Day panel
    const panel = document.createElement("div");
    panel.id = `nutr-day-${day}`;
    panel.className = "nutr-day-panel" + (idx !== 0 ? " hidden" : "");

    const dayData = weekly[day];
    const meals = Object.entries(MEAL_LABELS).map(([key, lbl]) => {
      const meal = dayData[key];
      if (!meal) return "";
      const allergens = (meal.allergens_checked || []).join(", ") || "None";
      return `
        <div class="meal-block">
          <div class="meal-header">
            <span class="meal-label">${lbl}</span>
            <span class="glycemic-badge gl-${(meal.glycemic_load || "").toLowerCase().replace(/[^a-z]/g,"")}">${meal.glycemic_load || ""}</span>
          </div>
          <p class="meal-desc">${meal.description}</p>
          <div class="meal-ingredients">
            ${(meal.ingredients || []).map(i => `<span class="ingredient-chip">${i}</span>`).join("")}
          </div>
          <div class="meal-allergens">🚫 Allergens checked: <em>${allergens}</em></div>
        </div>`;
    }).join("");

    panel.innerHTML = `<div class="meals-grid">${meals}</div>`;
    contentEl.appendChild(panel);
  });

  // Legal disclaimer
  const disc = (plan.metadata || {}).legal_disclaimer || "";
  if (disc) el("nutr-disclaimer").textContent = disc;

  show("nutr-results-section");

  // Build full-text for download
  buildDownloadText(plan);
}

function buildDownloadText(plan) {
  const summary = plan.diet_summary || {};
  const macros  = summary.macro_distribution || {};
  const finance = plan.financial_metrics || {};
  const weekly  = plan.weekly_plan || {};
  let txt = "NutriSentinel — Personalised Weekly Diet Plan\n";
  txt += "═".repeat(54) + "\n\n";
  txt += `Diet Type  : ${summary.diet_type}\n`;
  txt += `Calories   : ${summary.target_calories_kcal} kcal/day\n`;
  txt += `Carbs      : ${macros.carbohydrates_g} g\n`;
  txt += `Protein    : ${macros.proteins_g} g\n`;
  txt += `Fat        : ${macros.fats_g} g\n`;
  txt += `Budget     : ${finance.user_budget_tier} — ~€${finance.estimated_weekly_cost_eur}/week\n\n`;
  Object.entries(weekly).forEach(([day, data]) => {
    txt += `\n── ${(DAY_LABELS[day] || day).toUpperCase()} ──\n`;
    Object.entries(MEAL_LABELS).forEach(([key, lbl]) => {
      const meal = data[key];
      if (!meal) return;
      txt += `  ${lbl}\n    ${meal.description}\n    Ingredients: ${(meal.ingredients || []).join(", ")}\n\n`;
    });
  });
  txt += "\n" + "═".repeat(54) + "\n";
  txt += (plan.metadata || {}).legal_disclaimer || "";
  window._planTxt = txt;

  const btn = el("nutr-btn-download");
  if (btn) btn.disabled = false;
}

function downloadPlanTxt() {
  const txt = window._planTxt || "No plan generated.";
  const blob = new Blob([txt], { type: "text/plain;charset=utf-8" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = "nutrisentinel_diet_plan.txt";
  a.click();
  URL.revokeObjectURL(url);
}

// ── WebSocket pipeline trigger ────────────────────────────────────────────────
function startNutritionPipeline(urinalysis, userId) {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const wsUrl    = `${protocol}://${location.host}/api/nutrition/ws/generate`;
  const ws       = new WebSocket(wsUrl);

  show("nutr-progress-section");
  hide("nutr-results-section");
  hide("nutr-emergency-section");
  el("nutr-btn-generate").disabled = true;
  updateProgress(5, "🔌 Connecting to agent pipeline...", 1);

  ws.onopen = () => {
    ws.send(JSON.stringify({ urinalysis, user_id: userId || "anonymous" }));
  };

  ws.onmessage = ({ data }) => {
    const msg = JSON.parse(data);
    switch (msg.event) {
      case "progress":
        updateProgress(msg.percent, msg.label, msg.step);
        break;
      case "approved":
        renderPlan(msg.plan);
        updateProgress(100, "✅ Plan approved and delivered!", 6);
        break;
      case "emergency":
        el("nutr-emergency-msg").textContent = msg.alert.alert_message || "";
        el("nutr-emergency-helpline").textContent = msg.alert.helpline || "";
        show("nutr-emergency-section");
        updateProgress(100, "⚠️ Emergency lock triggered.", 1);
        break;
      case "error":
        updateProgress(100, `❌ ${msg.message}`, 6);
        break;
      case "done":
        el("nutr-btn-generate").disabled = false;
        ws.close();
        break;
    }
  };

  ws.onerror = () => {
    updateProgress(100, "❌ WebSocket connection error.", 6);
    el("nutr-btn-generate").disabled = false;
  };
}

// ── Navigation init (called from app.js) ─────────────────────────────────────
window.initNutritionView = function () {
  renderStepsPipeline();
  const data = window._nutriData || {};

  // Pre-fill source banner
  if (data.source) {
    el("nutr-source-label").textContent = `Data from: ${data.source}`;
    show("nutr-source-banner");
  }

  // Pre-fill summary boxes with incoming data if available
  if (data.urinalysis) {
    const u = data.urinalysis;
    el("nutr-in-glucose").textContent  = u.Glucose  || "—";
    el("nutr-in-ketone").textContent   = u.Ketone   || "—";
    el("nutr-in-protein").textContent  = u.Protein  || "—";
    el("nutr-in-ph").textContent       = u.pHValue  || "—";
    el("nutr-in-density").textContent  = u.SpecificGravity || "—";
    show("nutr-input-summary");
  }

  // Generate button
  el("nutr-btn-generate").addEventListener("click", () => {
    const urinalysis = data.urinalysis || { ...SAFE_DEFAULTS };
    const userId = "test_user_laurindo";
    startNutritionPipeline(urinalysis, userId);
  });

  // Download button
  el("nutr-btn-download").addEventListener("click", downloadPlanTxt);
};

// ── "Send to Nutritional Agents" helpers ─────────────────────────────────────
window.sendUrinalysisToNutrition = function (results) {
  const urinalysis = mapUrinalysisResultsToData(results);
  setNutriData("Urinalysis Panel", results, urinalysis);
  document.getElementById("btn-nav-nutrition")?.click();
};

window.sendBloodToNutrition = function (bloodData) {
  const urinalysis = mapBiomarkersToUrinalysis(bloodData.biomarkers || []);
  setNutriData(`Blood Analysis — ${bloodData.patient_name || "Patient"}`, bloodData, urinalysis);
  document.getElementById("btn-nav-nutrition")?.click();
};
