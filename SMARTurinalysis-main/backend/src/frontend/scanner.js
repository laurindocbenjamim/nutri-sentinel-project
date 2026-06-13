/**
 * Guided Urinalysis Scanner Module
 * Handles manual photo capture, blur validation, and uploads to the backend.
 */
(function() {
    let stream = null;
    let isScanning = false;
    
    let renderResultsCallback = null;
    let updateStatusCallback = null;
    
    const scannerModal = document.getElementById("scanner-modal");
    const video = document.getElementById("scanner-video");
    const scannerStatus = document.getElementById("scanner-status-text");
    const btnCapture = document.getElementById("btn-capture-scan");
    
    window.initScanner = function(renderResults, updateStatus) {
        renderResultsCallback = renderResults;
        updateStatusCallback = updateStatus;
        
        const btnScan = document.getElementById("btn-scan");
        const btnClose = document.getElementById("btn-close-scanner");
        
        if (btnScan) btnScan.addEventListener("click", startScanner);
        if (btnClose) btnClose.addEventListener("click", stopScanner);
        if (btnCapture) btnCapture.addEventListener("click", captureAndUploadFrame);
    };
    
    async function startScanner() {
        try {
            scannerModal.classList.remove("hidden");
            scannerStatus.innerHTML = `<span style="color: var(--accent-hover);">Requesting camera access...</span>`;
            if (btnCapture) btnCapture.disabled = false;
            
            stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } }
            });
            video.srcObject = stream;
            isScanning = true;
            scannerStatus.innerHTML = `<span style="color: var(--text-secondary);">Position reference card & stick, then click Capture & Analyze.</span>`;
        } catch (err) {
            scannerStatus.innerHTML = `<span style="color: #ef4444;">Camera Error: ${err.message}</span>`;
        }
    }
    
    function stopScanner() {
        isScanning = false;
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
        video.srcObject = null;
        scannerModal.classList.add("hidden");
    }
    
    async function captureAndUploadFrame() {
        if (!isScanning) return;
        
        // Disable button during processing to prevent multiple requests
        if (btnCapture) btnCapture.disabled = true;
        scannerStatus.innerHTML = `<span style="color: var(--accent-hover);">Analyzing frame... Please hold camera steady.</span>`;
        
        const canvas = document.createElement("canvas");
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        canvas.toBlob(async (blob) => {
            if (!blob) {
                scannerStatus.innerHTML = `<span style="color: #ef4444;">Capture Error: Failed to capture video frame.</span>`;
                if (btnCapture) btnCapture.disabled = false;
                return;
            }
            
            const file = new File([blob], "scan_frame.png", { type: "image/png" });
            const formData = new FormData();
            formData.append("file", file);
            
            try {
                const res = await fetch("/api/analysis/upload", {
                    method: "POST",
                    body: formData
                });
                const data = await res.json();
                
                if (res.ok && data.success) {
                    isScanning = false;
                    scannerStatus.innerHTML = `<span style="color: var(--success);">✔ Reading successful!</span>`;
                    setTimeout(() => {
                        stopScanner();
                        if (renderResultsCallback) renderResultsCallback(data);
                        if (updateStatusCallback) updateStatusCallback(false, "Analysis complete.");
                    }, 800);
                } else {
                    const errMsg = data.error || data.detail || "Could not align elements.";
                    scannerStatus.innerHTML = `<span style="color: #ef4444;">❌ ${errMsg}</span>`;
                    if (btnCapture) btnCapture.disabled = false;
                }
            } catch (err) {
                scannerStatus.innerHTML = `<span style="color: #ef4444;">❌ Connection Error: ${err.message}</span>`;
                if (btnCapture) btnCapture.disabled = false;
            }
        }, "image/png");
    }
})();
