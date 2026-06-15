const ANALYTES = [
    "Glucose", "Bilirubin", "Ketone", "SpecificGravity", 
    "Hemoglobin", "pHValue", "Protein", "Urobilinogen", 
    "Nitrite", "Leukocytes"
];

const PRESETS = {
    healthy: { 0: 0, 1: 0, 2: 0, 3: 3, 4: 0, 5: 3, 6: 0, 7: 0, 8: 0, 9: 0 },
    diabetic: { 0: 4, 1: 0, 2: 4, 3: 3, 4: 0, 5: 2, 6: 0, 7: 0, 8: 0, 9: 0 },
    uti: { 0: 0, 1: 0, 2: 0, 3: 2, 4: 0, 5: 1, 6: 2, 7: 0, 8: 2, 9: 4 }
};

document.addEventListener("DOMContentLoaded", () => {
    // Navigation Switching logic
    const btnNavUrinalysis = document.getElementById("btn-nav-urinalysis");
    const btnNavBlood = document.getElementById("btn-nav-blood");
    const viewUrinalysis = document.getElementById("view-urinalysis");
    const viewBlood = document.getElementById("view-blood");
    const btnTogglePanel = document.getElementById("btn-toggle-panel");

    if (btnNavUrinalysis && btnNavBlood && viewUrinalysis && viewBlood) {
        const viewNutrition = document.getElementById("view-nutrition");
        const btnNavNutrition = document.getElementById("btn-nav-nutrition");
        const allViews = [viewUrinalysis, viewBlood, viewNutrition].filter(Boolean);
        const allBtns  = [btnNavUrinalysis, btnNavBlood, btnNavNutrition].filter(Boolean);

        function switchView(activeView, activeBtn) {
            allViews.forEach(v => v.classList.add("hidden"));
            allBtns.forEach(b => b.classList.remove("active"));
            activeView.classList.remove("hidden");
            activeBtn.classList.add("active");
        }

        btnNavUrinalysis.addEventListener("click", () => {
            switchView(viewUrinalysis, btnNavUrinalysis);
            if (btnTogglePanel) btnTogglePanel.classList.remove("hidden");
        });

        btnNavBlood.addEventListener("click", () => {
            switchView(viewBlood, btnNavBlood);
            if (btnTogglePanel) btnTogglePanel.classList.add("hidden");
        });

        if (btnNavNutrition && viewNutrition) {
            btnNavNutrition.addEventListener("click", () => {
                switchView(viewNutrition, btnNavNutrition);
                if (btnTogglePanel) btnTogglePanel.classList.add("hidden");
                if (window.initNutritionView) window.initNutritionView();
            });
        }
    }

    const selectionList = document.getElementById("selection-list");
    const presetSelect = document.getElementById("preset-select");
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const spinner = document.getElementById("spinner");
    const statusText = document.getElementById("status-text");
    const loaderOverlay = document.getElementById("loader-overlay");
    const loaderText = document.getElementById("loader-text");
    const btnDownload = document.getElementById("btn-download");
    const chartContainer = document.getElementById("chart-container");
    const btnShowChart = document.getElementById("btn-show-chart");
    const btnDownloadCSV = document.getElementById("btn-download-csv");
    let currentResults = null;

    // Initialize Analyte Selectors
    ANALYTES.forEach((name, idx) => {
        const row = document.createElement("div");
        row.className = "analyte-row";
        row.innerHTML = `
            <span>${name}</span>
            <select id="sel-${idx}" class="analyte-select">
                <option value="0">Negative / Level 0</option>
                <option value="1">Level 1</option>
                <option value="2">Level 2</option>
                <option value="3">Level 3</option>
                <option value="4">Level 4</option>
                <option value="5">Level 5</option>
                <option value="6">Level 6</option>
            </select>
        `;
        selectionList.appendChild(row);
    });

    const applyPreset = (presetName) => {
        const values = PRESETS[presetName];
        for (let i = 0; i < 10; i++) {
            const select = document.getElementById(`sel-${i}`);
            if (select) select.value = values[i] || 0;
        }
    };

    // Session token initialization helper
    let sessionInitialized = false;
    const ensureSession = async () => {
        if (sessionInitialized) return;
        try {
            await fetch("/api/session/init", { method: "POST" });
            sessionInitialized = true;
        } catch (err) {
            console.error("Session initialization failed:", err);
        }
    };

    // Default to healthy preset and initialize session
    applyPreset("healthy");
    ensureSession();
    presetSelect.addEventListener("change", (e) => applyPreset(e.target.value));

    // Upload & Drag-Drop Listeners
    dropZone.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            btnDownload.classList.add("hidden");
            uploadImage(e.target.files[0]);
        }
    });
    dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.style.borderColor = "#38bdf8"; });
    dropZone.addEventListener("dragleave", () => { dropZone.style.borderColor = "rgba(255,255,255,0.2)"; });
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.style.borderColor = "rgba(255,255,255,0.2)";
        if (e.dataTransfer.files.length > 0) {
            btnDownload.classList.add("hidden");
            uploadImage(e.dataTransfer.files[0]);
        }
    });

    // Generate Mock Photo Listener
    document.getElementById("btn-generate").addEventListener("click", async () => {
        await ensureSession();
        const selections = {};
        for (let i = 0; i < 10; i++) {
            selections[i] = parseInt(document.getElementById(`sel-${i}`).value);
        }
        const evalTime = parseInt(document.getElementById("eval-time-select").value);

        try {
            btnDownload.classList.add("hidden");
            updateStatus(true, "Generating synthetic camera shot...");
            const res = await fetch("/api/synthetic/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ selections, eval_time: evalTime })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Generation failed");

            // Auto-submit the generated mock photo
            updateStatus(true, "Mock photo created. Running colorimetric analysis...");
            btnDownload.href = data.mock_image_url;
            btnDownload.classList.remove("hidden");
            const mockRes = await fetch(data.mock_image_url);
            const blob = await mockRes.blob();
            const file = new File([blob], "mock_photo.png", { type: "image/png" });
            uploadImage(file);
        } catch (err) {
            updateStatus(false, `Error: ${err.message}`);
        }
    });

    async function uploadImage(file) {
        await ensureSession();
        const formData = new FormData();
        formData.append("file", file);

        try {
            updateStatus(true, "Aligning and analyzing stick...");
            const res = await fetch("/api/analysis/upload", {
                method: "POST",
                body: formData
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Analysis failed");

            renderResults(data);
            updateStatus(false, "Analysis complete.");
        } catch (err) {
            updateStatus(false, `Error: ${err.message}`);
        }
    }

    function updateStatus(loading, text) {
        if (loading) {
            spinner.classList.remove("hidden");
            loaderOverlay.classList.remove("hidden");
            loaderText.textContent = text;
        } else {
            spinner.classList.add("hidden");
            loaderOverlay.classList.add("hidden");
        }
        statusText.textContent = text;
    }

    function renderResults(data) {
        // Display Aligned Images
        document.getElementById("img-aligned-card").src = data.aligned_card_url + "?t=" + Date.now();
        document.getElementById("img-aligned-stick").src = data.aligned_stick_url + "?t=" + Date.now();
        document.getElementById("alignment-visualizer").classList.remove("hidden");

        currentResults = data.results;
        if (!chartContainer.classList.contains("hidden")) {
            drawChart(currentResults);
        }

        // Display Table
        const body = document.getElementById("results-body");
        body.innerHTML = "";
        
        Object.entries(data.results).forEach(([analyte, info]) => {
            const tr = document.createElement("tr");
            const bgr = info.stick_color_bgr;
            const rgbString = `rgb(${bgr[2]}, ${bgr[1]}, ${bgr[0]})`;
            
            tr.innerHTML = `
                <td><strong>${analyte}</strong></td>
                <td>${info.value}</td>
                <td><span class="color-dot" style="background-color: ${rgbString}"></span> [${bgr.join(', ')}]</td>
                <td><span class="score-badge">${info.confidence}%</span></td>
            `;
            body.appendChild(tr);
        });
        document.getElementById("results-table-container").classList.remove("hidden");
    }

    btnShowChart.addEventListener("click", () => {
        if (!currentResults) return;
        if (chartContainer.classList.contains("hidden")) {
            chartContainer.classList.remove("hidden");
            btnShowChart.textContent = "Hide Chart";
            window.drawChart(currentResults);
        } else {
            chartContainer.classList.add("hidden");
            btnShowChart.textContent = "Visualize Chart";
        }
    });

    btnDownloadCSV.addEventListener("click", () => {
        if (!currentResults) return;
        window.downloadCSV(currentResults);
    });

    // ── Send urinalysis results to Nutrition AI ──────────────────────────────
    const btnUrineToNutr = document.getElementById("btn-urine-to-nutrition");
    if (btnUrineToNutr) {
        btnUrineToNutr.addEventListener("click", () => {
            if (currentResults && window.sendUrinalysisToNutrition) {
                window.sendUrinalysisToNutrition(currentResults);
            }
        });
    }

    // Toggle Test Bench Panel
    const syntheticPanel = document.getElementById("synthetic-panel");
    const mainGrid = document.getElementById("main-grid");
    if (btnTogglePanel && syntheticPanel && mainGrid) {
        btnTogglePanel.addEventListener("click", () => {
            syntheticPanel.classList.toggle("hidden");
            mainGrid.classList.toggle("collapsed");
            
            if (syntheticPanel.classList.contains("hidden")) {
                btnTogglePanel.textContent = "🧪 Show Panel";
                btnTogglePanel.style.borderColor = "rgba(255,255,255,0.15)";
            } else {
                btnTogglePanel.textContent = "🧪 Hide Panel";
                btnTogglePanel.style.borderColor = "var(--accent-hover)";
            }
        });
    }

    // Initialize scanner with callbacks
    if (window.initScanner) {
        window.initScanner(renderResults, updateStatus);
    }
});
