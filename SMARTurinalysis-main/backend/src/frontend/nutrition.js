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
window._nutriData = window._nutriData || { blood: null, urine: null };

function setNutriData(type, source, data, urinalysis) {
  if (type === 'blood') {
    window._nutriData.blood = { source, data, urinalysis };
  } else if (type === 'urine') {
    window._nutriData.urine = { source, data, urinalysis };
  }
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
  // Store plan object globally for CSV download
  window._currentPlan = plan;

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

  const txtBtn = el("nutr-btn-dl-txt");
  const pdfBtn = el("nutr-btn-dl-pdf");
  const csvBtn = el("nutr-btn-dl-csv");
  if (txtBtn) txtBtn.disabled = false;
  if (pdfBtn) pdfBtn.disabled = false;
  if (csvBtn) csvBtn.disabled = false;
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

function downloadPlanCSV() {
  const plan = window._currentPlan;
  if (!plan || !plan.weekly_plan) return alert("No plan generated.");
  let csv = "Day,Meal,Description,Ingredients,Allergens Checked,Glycemic Load\n";
  const days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
  days.forEach(day => {
    const dPlan = plan.weekly_plan[day];
    if (!dPlan) return;
    const meals = ["pequeno_almoco", "almoco", "lanche", "jantar"];
    meals.forEach(m => {
      if (dPlan[m]) {
        const meal = dPlan[m];
        csv += `"${day.toUpperCase()}","${m.toUpperCase()}","${meal.description.replace(/"/g, '""')}","${meal.ingredients.join(', ')}","${meal.allergens_checked.join(', ')}","${meal.glycemic_load}"\n`;
      }
    });
  });
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = "nutrisentinel_diet_plan.csv";
  a.click();
  URL.revokeObjectURL(url);
}

function downloadPlanPDF() {
  const plan = window._currentPlan;
  if (!plan) return alert("No plan generated.");
  if (!window.jspdf || !window.jspdf.jsPDF || !window.jspdf.jsPDF.prototype.autoTable) {
    return alert("PDF engine loading, please try again in a few seconds.");
  }
  
  const doc = new window.jspdf.jsPDF();
  
  // Header: Application Info
  doc.setFont("helvetica", "bold");
  doc.setFontSize(24);
  doc.setTextColor(14, 165, 233); // Brand color (blue)
  doc.text("NutriSentinel", 14, 22);
  
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.setTextColor(100, 116, 139); // Slate-500
  const dateStr = new Date().toLocaleDateString() + " " + new Date().toLocaleTimeString();
  doc.text(`Generated: ${dateStr}  |  Version: 1.0 (AI Agent)`, 14, 28);
  
  // Title
  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.setTextColor(15, 23, 42); // Slate-900
  doc.text("Personalised Weekly Diet Plan", 14, 42);
  
  // Diet Summary Box (using autoTable)
  const sum = plan.diet_summary || {};
  const macros = sum.macro_distribution || {};
  const fin = plan.financial_metrics || {};
  
  doc.autoTable({
    startY: 48,
    head: [['Diet Type', 'Calories', 'Carbs', 'Protein', 'Fat', 'Weekly Cost']],
    body: [[
      sum.diet_type || 'N/A',
      `${sum.target_calories_kcal || 0} kcal`,
      `${macros.carbohydrates_g || 0}g`,
      `${macros.proteins_g || 0}g`,
      `${macros.fats_g || 0}g`,
      `€${fin.estimated_weekly_cost_eur || 0}`
    ]],
    theme: 'grid',
    headStyles: { fillColor: [14, 165, 233], textColor: 255, fontStyle: 'bold' },
    styles: { fontSize: 10, cellPadding: 4, halign: 'center', textColor: 40 }
  });
  
  let finalY = doc.lastAutoTable.finalY + 12;
  
  // Weekly Plan Iteration
  const days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
  const mealNames = ["pequeno_almoco", "almoco", "lanche", "jantar"];
  const labels = {"pequeno_almoco": "Breakfast", "almoco": "Lunch", "lanche": "Snack", "jantar": "Dinner"};
  
  days.forEach(day => {
    const dPlan = plan.weekly_plan[day];
    if (!dPlan) return;
    
    // Page break logic if getting too close to bottom before a new day
    if (finalY > 240) {
      doc.addPage();
      finalY = 20;
    }
    
    // Day Title
    doc.setFont("helvetica", "bold");
    doc.setFontSize(14);
    doc.setTextColor(22, 163, 74); // Green-600
    doc.text(day.toUpperCase(), 14, finalY + 4);
    
    const mealRows = [];
    mealNames.forEach(m => {
      if (dPlan[m]) {
        const meal = dPlan[m];
        mealRows.push([
          labels[m],
          meal.description,
          meal.ingredients.join(", "),
          meal.glycemic_load
        ]);
      }
    });
    
    doc.autoTable({
      startY: finalY + 8,
      head: [['Meal', 'Description', 'Ingredients', 'Glycemic Load']],
      body: mealRows,
      theme: 'striped',
      headStyles: { fillColor: [30, 41, 59], textColor: 255 }, // Slate-800
      columnStyles: {
        0: { fontStyle: 'bold', cellWidth: 25 },
        1: { cellWidth: 70 },
        2: { cellWidth: 60 },
        3: { cellWidth: 25, halign: 'center' }
      },
      styles: { fontSize: 9, cellPadding: 4, textColor: 60 },
      pageBreak: 'auto'
    });
    
    finalY = doc.lastAutoTable.finalY + 12;
  });
  
  // Legal Disclaimer Box
  if (finalY > 260) {
    doc.addPage();
    finalY = 20;
  }
  
  const disclaimer = (plan.metadata && plan.metadata.legal_disclaimer) 
    ? plan.metadata.legal_disclaimer 
    : "LEGAL NOTICE: This diet plan is AI-generated for informational purposes only. It does not replace professional medical or nutritional advice.";
  
  doc.setFont("helvetica", "italic");
  doc.setFontSize(9);
  doc.setTextColor(180, 83, 9); // Amber-700
  doc.text("⚠️ " + disclaimer, 14, finalY, { maxWidth: 180, lineHeightFactor: 1.5 });
  
  doc.save("NutriSentinel_Diet_Plan.pdf");
}

async function showUserProfile() {
  const modal = el("profile-modal");
  const content = el("profile-content");
  if (!modal || !content) return;
  
  show("profile-modal");
  content.innerHTML = "<div style='color:var(--text-secondary);text-align:center;'>Loading profile...</div>";
  
  try {
    const res = await fetch("/api/nutrition/profile/test_user_laurindo");
    if (!res.ok) throw new Error("Failed to fetch profile");
    const profile = await res.json();
    
    content.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
        <div style="background:rgba(255,255,255,0.05);padding:1rem;border-radius:8px;">
          <div style="font-size:0.75rem;color:var(--text-secondary);text-transform:uppercase;">Age</div>
          <div style="font-size:1.2rem;font-weight:600;">${profile.age} years</div>
        </div>
        <div style="background:rgba(255,255,255,0.05);padding:1rem;border-radius:8px;">
          <div style="font-size:0.75rem;color:var(--text-secondary);text-transform:uppercase;">Biological Sex</div>
          <div style="font-size:1.2rem;font-weight:600;text-transform:capitalize;">${profile.sex}</div>
        </div>
        <div style="background:rgba(255,255,255,0.05);padding:1rem;border-radius:8px;">
          <div style="font-size:0.75rem;color:var(--text-secondary);text-transform:uppercase;">Primary Goal</div>
          <div style="font-size:1.2rem;font-weight:600;text-transform:capitalize;">${profile.goal.replace('_', ' ')}</div>
        </div>
        <div style="background:rgba(255,255,255,0.05);padding:1rem;border-radius:8px;">
          <div style="font-size:0.75rem;color:var(--text-secondary);text-transform:uppercase;">Budget Tier</div>
          <div style="font-size:1.2rem;font-weight:600;text-transform:capitalize;">${profile.budget_tier.replace('_', ' ')}</div>
        </div>
      </div>
      
      <div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.2);padding:1rem;border-radius:8px;">
        <div style="font-size:0.75rem;color:#f87171;text-transform:uppercase;margin-bottom:0.5rem;font-weight:600;">Pathologies</div>
        <div style="font-size:0.95rem;color:var(--text-primary);">
          ${profile.pathologies.length ? profile.pathologies.map(p => `• ${p}`).join('<br>') : 'None recorded'}
        </div>
      </div>

      <div style="background:rgba(234,179,8,0.1);border:1px solid rgba(234,179,8,0.2);padding:1rem;border-radius:8px;">
        <div style="font-size:0.75rem;color:#fbbf24;text-transform:uppercase;margin-bottom:0.5rem;font-weight:600;">Allergies</div>
        <div style="font-size:0.95rem;color:var(--text-primary);">
          ${profile.allergies.length ? profile.allergies.map(a => `• ${a}`).join('<br>') : 'None recorded'}
        </div>
      </div>
      
      <div style="background:rgba(14,165,233,0.1);border:1px solid rgba(14,165,233,0.2);padding:1rem;border-radius:8px;">
        <div style="font-size:0.75rem;color:#38bdf8;text-transform:uppercase;margin-bottom:0.5rem;font-weight:600;">Medications</div>
        <div style="font-size:0.95rem;color:var(--text-primary);">
          ${profile.medications.length ? profile.medications.map(m => `• ${m}`).join('<br>') : 'None recorded'}
        </div>
      </div>
    `;
  } catch(e) {
    content.innerHTML = `<div style="color:#f87171;">Error loading profile: ${e.message}</div>`;
  }
}


// ── WebSocket pipeline trigger ────────────────────────────────────────────────
function startNutritionPipeline(urinalysis, bloodData, userId) {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const wsUrl    = `${protocol}://${location.host}/api/nutrition/ws/generate`;
  const ws       = new WebSocket(wsUrl);

  // Trigger animation: split grid into 2 columns and slide in right panel
  const mainGrid = el("nutr-main-grid");
  const rightPanel = el("nutr-right-panel");
  if (mainGrid && rightPanel) {
    mainGrid.style.gridTemplateColumns = "minmax(350px, 1fr) minmax(400px, 1.2fr)";
    rightPanel.style.display = "block";
    
    // Force reflow before applying opacity/transform
    void rightPanel.offsetWidth;
    
    rightPanel.style.opacity = "1";
    rightPanel.style.transform = "translateX(0)";
  }

  show("nutr-progress-section");
  hide("nutr-results-section");
  hide("nutr-emergency-section");
  el("nutr-btn-generate").disabled = true;
  updateProgress(5, "🔌 Connecting to agent pipeline...", 1);

  ws.onopen = () => {
    // Send the combined source payload + notes
    const notesEl = el("nutr-input-notes");
    const notes = notesEl ? notesEl.value.trim() : "";
    
    ws.send(JSON.stringify({ 
      urinalysis: urinalysis || {}, 
      blood_data: bloodData, 
      user_id: userId,
      notes: notes 
    }));
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
window.initNutritionView = (function () {
  let _listenersAttached = false;

  return function () {
    renderStepsPipeline();
    
    // Reset layout on navigation init
    const mainGrid = el("nutr-main-grid");
    const rightPanel = el("nutr-right-panel");
    if (mainGrid && rightPanel) {
      mainGrid.style.gridTemplateColumns = "1fr";
      rightPanel.style.opacity = "0";
      rightPanel.style.transform = "translateX(40px)";
      rightPanel.style.display = "none";
    }

    const data = window._nutriData || { blood: null, urine: null };

    // Determine combined source
    let sources = [];
    if (data.blood && data.blood.source) sources.push(data.blood.source);
    if (data.urine && data.urine.source) sources.push(data.urine.source);

    if (sources.length > 0) {
      el("nutr-source-label").textContent = `Data from: ${sources.join(" & ")}`;
      show("nutr-source-banner");
    } else {
      hide("nutr-source-banner");
    }

    // Determine the combined urinalysis pipeline object to show
    // Prefer urine dipstick if available, else fallback to mapped blood biomarkers
    let primaryUrinalysis = null;
    if (data.urine && data.urine.urinalysis) {
      primaryUrinalysis = data.urine.urinalysis;
    } else if (data.blood && data.blood.urinalysis) {
      primaryUrinalysis = data.blood.urinalysis;
    }

    const summaryEl = el("nutr-input-summary");
    if (summaryEl && primaryUrinalysis) {
      const u = primaryUrinalysis;
      el("nutr-in-glucose").textContent  = u.Glucose  || "—";
      el("nutr-in-ketone").textContent   = u.Ketone   || "—";
      el("nutr-in-protein").textContent  = u.Protein  || "—";
      el("nutr-in-ph").textContent       = u.pHValue  || "—";
      el("nutr-in-density").textContent  = u.SpecificGravity || "—";

      // Full blood biomarker cards
      const oldSection = el("nutr-blood-section");
      if (oldSection) oldSection.remove();

      if (data.blood && data.blood.data && data.blood.data.biomarkers && data.blood.data.biomarkers.length > 0) {
        const bloodBiomarkers = data.blood.data.biomarkers;
        const section = document.createElement("div");
        section.id = "nutr-blood-section";
        section.style.cssText = "margin-top:1.5rem;";

        const heading = document.createElement("h3");
        heading.style.cssText = "font-size:0.9rem;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.75rem;";
        heading.textContent = "Full Blood Panel — " + (data.blood.data.patient_name || "Patient");
        section.appendChild(heading);

        const grid = document.createElement("div");
        grid.style.cssText = "display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:0.6rem;";

        bloodBiomarkers.forEach(function(b) {
          const flagLower = (b.flag || "").toLowerCase();
          let bg = "rgba(255,255,255,0.03)";
          let valueColor = "var(--text-primary)";
          let badgeClass = "normal";
          if (flagLower.includes("high") || flagLower.includes("abnormal")) {
            bg = "rgba(239,68,68,0.08)"; valueColor = "#f87171"; badgeClass = "high";
          } else if (flagLower.includes("low")) {
            bg = "rgba(234,179,8,0.08)"; valueColor = "#fbbf24"; badgeClass = "low";
          } else if (flagLower === "normal") {
            bg = "rgba(16,185,129,0.06)"; valueColor = "var(--success)";
          }
          const card = document.createElement("div");
          card.style.cssText = "background:" + bg + ";border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:0.75rem 1rem;transition:transform 0.15s;";
          card.onmouseenter = function(){ card.style.transform = "translateY(-2px)"; };
          card.onmouseleave = function(){ card.style.transform = "none"; };
          card.innerHTML =
            "<div style='font-size:0.68rem;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.3rem;font-weight:600;'>" + b.biomarker + "</div>" +
            "<div style='font-size:1.05rem;font-weight:700;color:" + valueColor + ";'>" + b.value +
              " <span style='font-size:0.72rem;font-weight:400;color:var(--text-secondary);'>" + (b.unit || "") + "</span></div>" +
            "<div style='font-size:0.7rem;color:var(--text-secondary);margin-top:0.2rem;'>Ref: " + (b.reference_range || "—") + "</div>" +
            "<div style='margin-top:0.45rem;'><span class='status-badge " + badgeClass + "'>" + b.flag + "</span></div>";
          grid.appendChild(card);
        });

        section.appendChild(grid);
        summaryEl.appendChild(section);
      }

      // Full urinalysis analyte cards
      const oldUrineSection = el("nutr-urine-section");
      if (oldUrineSection) oldUrineSection.remove();

      if (data.urine && data.urine.data) {
        const urineData = data.urine.data;
        const section = document.createElement("div");
        section.id = "nutr-urine-section";
        section.style.cssText = "margin-top:1.5rem;";

        const heading = document.createElement("h3");
        heading.style.cssText = "font-size:0.9rem;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.75rem;";
        heading.textContent = "Full Urinalysis Results";
        section.appendChild(heading);

        const grid = document.createElement("div");
        grid.style.cssText = "display:grid;grid-template-columns:repeat(auto-fill,minmax(165px,1fr));gap:0.6rem;";

        Object.entries(urineData).forEach(function(entry) {
          const analyteName = entry[0];
          const info = entry[1];
          if (!info || typeof info.value === "undefined") return;

          const val = String(info.value || "—");
          const conf = info.confidence ? parseFloat(info.confidence).toFixed(1) : null;
          const isNegative = val.toLowerCase() === "negative";
          const isNumericNormal = (analyteName === "pHValue" || analyteName === "SpecificGravity");

          // Color logic: Negative = green, numeric fields = neutral, anything positive = red
          let bg, valueColor, borderColor;
          if (isNegative || isNumericNormal) {
            bg = "rgba(16,185,129,0.06)";
            valueColor = "var(--success)";
            borderColor = "rgba(16,185,129,0.15)";
          } else if (val === "1.0 mg/dL" || val === "trace" || val.toLowerCase() === "trace") {
            bg = "rgba(234,179,8,0.07)";
            valueColor = "#fbbf24";
            borderColor = "rgba(234,179,8,0.2)";
          } else {
            bg = "rgba(239,68,68,0.07)";
            valueColor = "#f87171";
            borderColor = "rgba(239,68,68,0.2)";
          }

          // Color dot from BGR
          let dotStyle = "";
          if (info.stick_color_bgr && info.stick_color_bgr.length === 3) {
            const bgr = info.stick_color_bgr;
            dotStyle = "display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px;vertical-align:middle;background:rgb(" + bgr[2] + "," + bgr[1] + "," + bgr[0] + ");border:1px solid rgba(255,255,255,0.2);";
          }

          const card = document.createElement("div");
          card.style.cssText = "background:" + bg + ";border:1px solid " + borderColor + ";border-radius:10px;padding:0.75rem 1rem;transition:transform 0.15s;";
          card.onmouseenter = function(){ card.style.transform = "translateY(-2px)"; };
          card.onmouseleave = function(){ card.style.transform = "none"; };
          card.innerHTML =
            "<div style='font-size:0.68rem;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.3rem;font-weight:600;'>" + analyteName + "</div>" +
            "<div style='font-size:1.05rem;font-weight:700;color:" + valueColor + ";display:flex;align-items:center;'>" +
              (dotStyle ? "<span style='" + dotStyle + "'></span>" : "") +
              val +
            "</div>" +
            (conf ? "<div style='font-size:0.68rem;color:var(--text-secondary);margin-top:0.3rem;'>Match: <strong>" + conf + "%</strong></div>" : "");
          grid.appendChild(card);
        });

        section.appendChild(grid);
        summaryEl.appendChild(section);
      }

      show("nutr-input-summary");
    }

    // Attach event listeners only once
    if (!_listenersAttached) {
      _listenersAttached = true;

      el("nutr-btn-generate").addEventListener("click", function () {
        const data = window._nutriData || { blood: null, urine: null };
        let urinalysis = null;
        if (data.urine && data.urine.urinalysis) urinalysis = data.urine.urinalysis;
        else if (data.blood && data.blood.urinalysis) urinalysis = data.blood.urinalysis;
        else urinalysis = { ...SAFE_DEFAULTS };

        let bloodData = null;
        if (data.blood && data.blood.data && data.blood.data.biomarkers) {
          bloodData = data.blood.data.biomarkers;
        }

        startNutritionPipeline(urinalysis, bloodData, "test_user_laurindo");
      });

      el("nutr-btn-dl-txt")?.addEventListener("click", downloadPlanTxt);
      el("nutr-btn-dl-csv")?.addEventListener("click", downloadPlanCSV);
      el("nutr-btn-dl-pdf")?.addEventListener("click", downloadPlanPDF);
      el("nutr-btn-profile")?.addEventListener("click", showUserProfile);
      el("btn-close-profile")?.addEventListener("click", () => hide("profile-modal"));
    }
  };
})();

// ── "Send to Nutritional Agents" helpers ─────────────────────────────────────
window.sendUrinalysisToNutrition = function (results) {
  const urinalysis = mapUrinalysisResultsToData(results);
  setNutriData("urine", "Urinalysis Panel", results, urinalysis);
  document.getElementById("btn-nav-nutrition")?.click();
};

window.sendBloodToNutrition = function (bloodData) {
  const urinalysis = mapBiomarkersToUrinalysis(bloodData.biomarkers || []);
  setNutriData("blood", `Blood Analysis — ${bloodData.patient_name || "Patient"}`, bloodData, urinalysis);
  document.getElementById("btn-nav-nutrition")?.click();
};
