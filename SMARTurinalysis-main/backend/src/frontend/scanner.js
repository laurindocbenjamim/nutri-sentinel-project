/**
 * Guided Urinalysis Scanner Module
 */
(function() {
    let stream = null;
    let scanInterval = null;
    let isScanning = false;
    
    let renderResultsCallback = null;
    let updateStatusCallback = null;
    
    const scannerModal = document.getElementById("scanner-modal");
    const video = document.getElementById("scanner-video");
    const scannerStatus = document.getElementById("scanner-status-text");
    
    window.initScanner = function(renderResults, updateStatus) {
        renderResultsCallback = renderResults;
        updateStatusCallback = updateStatus;
        
        const btnScan = document.getElementById("btn-scan");
        const btnClose = document.getElementById("btn-close-scanner");
        
        if (btnScan) btnScan.addEventListener("click", startScanner);
        if (btnClose) btnClose.addEventListener("click", stopScanner);
    };
    
    async function startScanner() {
        try {
            scannerModal.classList.remove("hidden");
            scannerStatus.innerHTML = `<span style="color: var(--accent-hover);">Requesting camera access...</span>`;
            stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } }
            });
            video.srcObject = stream;
            isScanning = true;
            scannerStatus.innerHTML = `<span style="color: var(--text-secondary);">Scanning... Hold stripe steady.</span>`;
            
            scanInterval = setInterval(captureAndUploadFrame, 1000);
        } catch (err) {
            scannerStatus.innerHTML = `<span style="color: #ef4444;">Camera Error: ${err.message}</span>`;
        }
    }
    
    function stopScanner() {
        isScanning = false;
        if (scanInterval) {
            clearInterval(scanInterval);
            scanInterval = null;
        }
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
        video.srcObject = null;
        scannerModal.classList.add("hidden");
    }
    
    async function captureAndUploadFrame() {
        if (!isScanning) return;
        
        const canvas = document.createElement("canvas");
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        canvas.toBlob(async (blob) => {
            if (!blob || !isScanning) return;
            const file = new File([blob], "scan_frame.png", { type: "image/png" });
            const formData = new FormData();
            formData.append("file", file);
            
            try {
                scannerStatus.innerHTML = `<span style="color: var(--accent-hover);">Analyzing frame...</span>`;
                const res = await fetch("/api/analysis/upload", {
                    method: "POST",
                    body: formData
                });
                const data = await res.json();
                
                if (res.ok && isScanning) {
                    isScanning = false;
                    scannerStatus.innerHTML = `<span style="color: var(--success);">✔ Stripe detected!</span>`;
                    setTimeout(() => {
                        stopScanner();
                        if (renderResultsCallback) renderResultsCallback(data);
                        if (updateStatusCallback) updateStatusCallback(false, "Analysis complete from real-time scan.");
                    }, 500);
                } else {
                    scannerStatus.innerHTML = `<span style="color: var(--text-secondary);">Hold steady. Align the stripe.</span>`;
                }
            } catch (err) {
                if (isScanning) {
                    scannerStatus.innerHTML = `<span style="color: var(--text-secondary);">Hold steady. Align the stripe.</span>`;
                }
            }
        }, "image/png");
    }
})();
