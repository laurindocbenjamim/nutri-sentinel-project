/**
 * SMARTurinalysis & Blood Analysis OCR - Frontend Orchestration
 */

document.addEventListener("DOMContentLoaded", () => {
    // 2. Drag & Drop Upload logic
    const uploadZone = document.getElementById("blood-upload-zone");
    const fileInput = document.getElementById("blood-file-input");
    const fileInfo = document.getElementById("blood-file-info");
    const filenameSpan = document.getElementById("blood-filename");
    const btnProcess = document.getElementById("btn-process-blood");
    const statusBox = document.getElementById("blood-status-box");
    const statusText = document.getElementById("blood-status-text");
    const emptyResults = document.getElementById("blood-empty-results");
    const resultsContainer = document.getElementById("blood-results-container");
    const patientName = document.getElementById("patient-name-val");
    const reportDate = document.getElementById("report-date-val");
    const resultsBody = document.getElementById("blood-results-body");
    const aiText = document.getElementById("blood-ai-text");

    let selectedFile = null;

    if (uploadZone && fileInput) {
        uploadZone.addEventListener("click", () => fileInput.click());

        uploadZone.addEventListener("dragover", (e) => {
            e.preventDefault();
            uploadZone.classList.add("dragover");
        });

        uploadZone.addEventListener("dragleave", () => {
            uploadZone.classList.remove("dragover");
        });

        uploadZone.addEventListener("drop", (e) => {
            e.preventDefault();
            uploadZone.classList.remove("dragover");
            if (e.dataTransfer.files.length > 0) {
                handleFileSelect(e.dataTransfer.files[0]);
            }
        });

        fileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) {
                handleFileSelect(e.target.files[0]);
            }
        });
    }

    function handleFileSelect(file) {
        selectedFile = file;
        filenameSpan.textContent = file.name;
        fileInfo.classList.remove("hidden");
        btnProcess.disabled = false;
    }

    if (btnProcess) {
        btnProcess.addEventListener("click", async () => {
            if (!selectedFile) return;

            statusBox.classList.remove("hidden");
            statusText.textContent = "Analyzing document using Clinical Multi-Agent pipeline...";
            btnProcess.disabled = true;

            const formData = new FormData();
            formData.append("file", selectedFile);

            try {
                const response = await fetch("/api/blood-analysis/upload", {
                    method: "POST",
                    body: formData
                });

                if (!response.ok) {
                    if (response.status === 401) {
                        throw new Error("Unauthorized session token. Please reload.");
                    }
                    const err = await response.json();
                    throw new Error(err.detail || "Upload analysis failed.");
                }

                const data = await response.json();
                renderBloodResults(data);
                statusBox.classList.add("hidden");
            } catch (err) {
                console.error(err);
                statusText.textContent = `Error: ${err.message}`;
                btnProcess.disabled = false;
            }
        });
    }

    let currentBloodData = null;

    // 3. Modern Tabs & Zoom Modal logic
    const tabBloodResults = document.getElementById("tab-blood-results");
    const tabs = [
        [tabBloodResults, document.getElementById("tab-content-results")],
        [document.getElementById("tab-blood-eval"), document.getElementById("tab-content-eval")]
    ];
    tabs.forEach(([btn, content]) => {
        if (!btn || !content) return;
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            tabs.forEach(([b, c]) => {
                const active = b === btn;
                c.classList.toggle("hidden", !active);
                b.classList.toggle("active", active);
                b.style.borderBottom = active ? "2px solid var(--accent)" : "2px solid transparent";
                b.style.color = active ? "var(--text-primary)" : "var(--text-secondary)";
            });
        });
    });

    const modal = document.getElementById("chart-zoom-modal");
    const btnZoom = document.getElementById("btn-zoom-chart");
    const btnClose = document.getElementById("btn-close-zoom-modal");

    if (btnZoom && modal && btnClose) {
        btnZoom.addEventListener("click", (e) => {
            e.preventDefault();
            if (!currentBloodData) return;
            modal.classList.remove("hidden");
            window.drawBloodChart(currentBloodData.biomarkers, "blood-chart-zoom");
        });
        const hideModal = () => modal.classList.add("hidden");
        btnClose.addEventListener("click", hideModal);
        modal.addEventListener("click", (e) => { if (e.target === modal) hideModal(); });
    }

    // 4. CSV Download logic
    const btnDownloadCSV = document.getElementById("btn-download-blood-csv");
    if (btnDownloadCSV) {
        btnDownloadCSV.addEventListener("click", () => {
            if (!currentBloodData || !currentBloodData.biomarkers) return;
            const csv = "Biomarker,Value,Unit,Reference Range,Status Flag\n" +
                currentBloodData.biomarkers.map(i => `"${i.biomarker}","${i.value}","${i.unit}","${i.reference_range}","${i.flag}"`).join("\n");
            const link = document.createElement("a");
            link.href = "data:text/csv;charset=utf-8," + encodeURI(csv);
            link.download = `blood_analysis_${(currentBloodData.patient_name || "report").toLowerCase().replace(/\s+/g, "_")}.csv`;
            link.click();
        });
    }

    function renderBloodResults(data) {
        currentBloodData = data;
        patientName.textContent = data.patient_name || "Unknown";
        reportDate.textContent = data.report_date || "Unknown";

        resultsBody.innerHTML = "";
        data.biomarkers.forEach(item => {
            const tr = document.createElement("tr");
            let flagClass = "normal";
            const flagLower = (item.flag || "").toLowerCase();
            if (flagLower.includes("high") || flagLower.includes("abnormal")) {
                flagClass = "high";
            } else if (flagLower.includes("low")) {
                flagClass = "low";
            }

            tr.innerHTML = `
                <td style="font-weight: 600;">${item.biomarker}</td>
                <td>${item.value}</td>
                <td style="color: var(--text-secondary);">${item.unit}</td>
                <td style="color: var(--text-secondary);">${item.reference_range}</td>
                <td><span class="status-badge ${flagClass}">${item.flag}</span></td>
            `;
            resultsBody.appendChild(tr);
        });

        aiText.textContent = data.recommendations || "No evaluation notes provided.";

        emptyResults.classList.add("hidden");
        resultsContainer.classList.remove("hidden");

        // Force transition to Extracted Results tab on new report load
        if (tabBloodResults) tabBloodResults.click();

        if (window.drawBloodChart) {
            window.drawBloodChart(data.biomarkers);
        }

        // Wire the Send to Nutrition AI button
        const btnBloodToNutr = document.getElementById("btn-blood-to-nutrition");
        if (btnBloodToNutr) {
            btnBloodToNutr.onclick = () => {
                if (window.sendBloodToNutrition) {
                    window.sendBloodToNutrition(currentBloodData);
                }
            };
        }
    }
});
