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

    // Default to healthy preset
    applyPreset("healthy");
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
            drawChart(currentResults);
        } else {
            chartContainer.classList.add("hidden");
            btnShowChart.textContent = "Visualize Chart";
        }
    });

    btnDownloadCSV.addEventListener("click", () => {
        if (!currentResults) return;
        downloadCSV(currentResults);
    });

    function downloadCSV(results) {
        let csvContent = "data:text/csv;charset=utf-8,";
        csvContent += "Analyte,Reading,Stick Color BGR,Confidence Score\n";
        Object.entries(results).forEach(([analyte, info]) => {
            const bgr = info.stick_color_bgr.join(";");
            csvContent += `"${analyte}","${info.value}","${bgr}",${info.confidence}\n`;
        });
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", "urinalysis_results.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    function drawChart(results) {
        const canvas = document.getElementById("analyte-chart");
        const ctx = canvas.getContext("2d");
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const margin = { top: 20, right: 20, bottom: 50, left: 50 };
        const width = canvas.width - margin.left - margin.right;
        const height = canvas.height - margin.top - margin.bottom;

        const entries = Object.entries(results).map(([name, info]) => {
            let level = 0;
            const match = info.value.match(/Level\s+(\d+)/i);
            if (match) {
                level = parseInt(match[1]);
            } else if (info.value.toLowerCase().includes("negative")) {
                level = 0;
            } else {
                const numeric = parseFloat(info.value);
                if (!isNaN(numeric)) {
                    level = numeric > 1 ? Math.min(6, Math.round(numeric)) : 0;
                }
            }
            return { name, level };
        });

        const numBars = entries.length;
        const barSpacing = 12;
        const barWidth = (width - barSpacing * (numBars - 1)) / numBars;
        const maxLevel = 6;

        ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(margin.left, margin.top);
        ctx.lineTo(margin.left, margin.top + height);
        ctx.lineTo(margin.left + width, margin.top + height);
        ctx.stroke();

        ctx.fillStyle = "rgba(255, 255, 255, 0.6)";
        ctx.font = "10px sans-serif";
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";
        for (let i = 0; i <= maxLevel; i++) {
            const y = margin.top + height - (i / maxLevel) * height;
            ctx.fillText(`Lvl ${i}`, margin.left - 10, y);
            
            ctx.strokeStyle = "rgba(255, 255, 255, 0.05)";
            ctx.beginPath();
            ctx.moveTo(margin.left, y);
            ctx.lineTo(margin.left + width, y);
            ctx.stroke();
        }

        entries.forEach((item, index) => {
            const barHeight = (item.level / maxLevel) * height;
            const x = margin.left + index * (barWidth + barSpacing);
            const y = margin.top + height - barHeight;

            const grad = ctx.createLinearGradient(x, y, x, margin.top + height);
            grad.addColorStop(0, "#38bdf8");
            grad.addColorStop(1, "rgba(56, 189, 248, 0.15)");
            ctx.fillStyle = grad;
            ctx.fillRect(x, y, barWidth, barHeight);

            ctx.strokeStyle = "#38bdf8";
            ctx.lineWidth = 1.5;
            ctx.strokeRect(x, y, barWidth, barHeight);

            ctx.save();
            ctx.translate(x + barWidth / 2, margin.top + height + 10);
            ctx.rotate(-Math.PI / 6);
            ctx.textAlign = "right";
            ctx.textBaseline = "middle";
            ctx.fillStyle = "rgba(255, 255, 255, 0.75)";
            ctx.font = "9px sans-serif";
            let dispName = item.name;
            if (dispName.length > 8) dispName = dispName.substring(0, 7) + ".";
            ctx.fillText(dispName, 0, 0);
            ctx.restore();
        });
    }
});
