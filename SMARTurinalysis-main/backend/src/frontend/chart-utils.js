/**
 * SMARTurinalysis - Charting & Exporting Utilities
 */

window.downloadCSV = function(results) {
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
};

window.drawChart = function(results) {
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
};

window.drawBloodChart = function(biomarkers, canvasId = "blood-chart") {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const scale = canvas.width / 600 || 1;

    const margin = { top: 25 * scale, right: 30 * scale, bottom: 20 * scale, left: 120 * scale };
    const width = canvas.width - margin.left - margin.right;
    const height = canvas.height - margin.top - margin.bottom;

    const numItems = biomarkers.length;
    if (numItems === 0) return;
    const rowHeight = height / numItems;
    const barHeight = Math.min(14 * scale, rowHeight * 0.45);

    biomarkers.forEach((item, index) => {
        const y = margin.top + index * rowHeight + rowHeight / 2;
        
        ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
        ctx.font = `bold ${Math.round(11 * scale)}px sans-serif`;
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";
        let label = item.biomarker;
        if (label.length > 15) label = label.substring(0, 13) + "..";
        ctx.fillText(label, margin.left - 15 * scale, y);

        let val = parseFloat(item.value);
        let rangeParts = item.reference_range.split('-').map(p => parseFloat(p.trim()));
        let minVal = rangeParts[0];
        let maxVal = rangeParts[1];

        const trackX = margin.left;
        const trackWidth = width;
        ctx.fillStyle = "rgba(255, 255, 255, 0.08)";
        ctx.beginPath();
        ctx.roundRect(trackX, y - barHeight / 2, trackWidth, barHeight, 4 * scale);
        ctx.fill();

        const normalStart = 0.25;
        const normalEnd = 0.75;
        const normalRangeWidth = normalEnd - normalStart;

        if (!isNaN(minVal) && !isNaN(maxVal) && !isNaN(val)) {
            const zoneX = trackX + normalStart * trackWidth;
            const zoneW = normalRangeWidth * trackWidth;
            ctx.fillStyle = "rgba(16, 185, 129, 0.12)";
            ctx.fillRect(zoneX, y - barHeight / 2, zoneW, barHeight);

            let pct;
            if (val <= minVal) {
                pct = 0.05 + 0.20 * (minVal > 0 ? (val / minVal) : 0);
                if (pct < 0.05) pct = 0.05;
            } else if (val >= maxVal) {
                const overFactor = maxVal > 0 ? ((val - maxVal) / maxVal) : 0;
                pct = 0.75 + Math.min(0.20, 0.10 * overFactor);
            } else {
                pct = normalStart + normalRangeWidth * ((val - minVal) / (maxVal - minVal));
            }

            const pinX = trackX + pct * trackWidth;
            let pinColor = "#10b981";
            const flag = (item.flag || "").toLowerCase();
            if (flag.includes("high") || flag.includes("low") || flag.includes("abnormal")) {
                pinColor = flag.includes("high") ? "#ef4444" : "#f59e0b";
            }

            const fillW = pct * trackWidth;
            const grad = ctx.createLinearGradient(trackX, y, pinX, y);
            grad.addColorStop(0, "rgba(255,255,255,0.01)");
            grad.addColorStop(1, pinColor + "25");
            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.roundRect(trackX, y - barHeight / 2, fillW, barHeight, 4 * scale);
            ctx.fill();

            ctx.fillStyle = pinColor;
            ctx.shadowBlur = 4 * scale;
            ctx.shadowColor = pinColor;
            ctx.beginPath();
            ctx.arc(pinX, y, barHeight / 2 + 2 * scale, 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 0;
            
            ctx.fillStyle = "#ffffff";
            ctx.font = `${Math.round(9 * scale)}px sans-serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "bottom";
            ctx.fillText(`${item.value} ${item.unit}`, pinX, y - barHeight / 2 - 2 * scale);
        } else {
            let pinColor = "#10b981";
            const flag = (item.flag || "").toLowerCase();
            if (flag.includes("high") || flag.includes("low") || flag.includes("abnormal")) {
                pinColor = flag.includes("high") ? "#ef4444" : "#f59e0b";
            }
            const pinX = trackX + 0.5 * trackWidth;
            ctx.fillStyle = pinColor;
            ctx.beginPath();
            ctx.arc(pinX, y, barHeight / 2 + 2 * scale, 0, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = "#ffffff";
            ctx.font = `${Math.round(9 * scale)}px sans-serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "bottom";
            ctx.fillText(`${item.value} ${item.unit}`, pinX, y - barHeight / 2 - 2 * scale);
        }
    });
};
