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
