# Future Investigations & Recommendations

Based on the research findings in the publication *Smartphone-Based Colorimetric Analysis of Urine Test Strips for At-Home Prenatal Care*, the authors outline several limitations in the current implementation and recommend specific directions for future development.

---

## 🔍 1. Computer Vision & Object Detection

*   **Stick Detection via Deep Learning**:
    *   *Finding*: The ORB-based feature matching approach only successfully detected **40%** of the urine sticks due to their low-contrast features and lack of distinctive texture. In contrast, the region-based convolutional neural network (**Mask R-CNN**) achieved **85.5%** accuracy with a small training set of 117 images.
    *   *Recommendation*: Abandon feature matching for urine stick localization. Focus on expanding the training dataset and tuning hyperparameters of the Mask R-CNN (or modern alternatives like YOLO/Segment Anything) for robust edge detection under varying environments.
*   **Handling Blurry Input**:
    *   *Finding*: Blur in captured photos was the primary cause of failure for both reference card and stick detection.
    *   *Recommendation*: Implement a client-side blur-detection preprocessing step (e.g., using Laplace variance) to immediately intercept out-of-focus captures and prompt the user to retake the photo.

---

## 🎨 2. Colorimetric Analysis & Accuracy

*   **Hybrid Color Matching Algorithms**:
    *   *Finding*: No single color-matching method (Hue channel, Matching Factor, or Euclidean distance) on its own is sufficient for clinical validation. Hue comparison performed best (F1-score 0.81), while Euclidean distance performed worst (F1-score 0.70). Leukocytes, in particular, generated high rates of false-positive classifications.
    *   *Recommendation*: Develop a hybrid classifier (or ensemble model) combining multiple HSV/RGB channel metrics. Explore machine learning classifiers (e.g., SVM, Random Forest, or K-NN) trained on calibrated colors to handle high-noise parameters like leukocytes.
*   **Sensor Calibrations**:
    *   *Finding*: Variations in smartphone camera hardware, color profiles, and automatic white balance adjustments introduce noise.
    *   *Recommendation*: Investigate the influence of specific smartphone sensor parameters and design a normalization mapping to calibrate colors across different mobile vendors.

---

## 👥 3. Clinical Validation & Ground Truth

*   **Reference POCT Verification**:
    *   *Finding*: The study relied on visual evaluation by humans as the ground truth, which is subjective and prone to observer error.
    *   *Recommendation*: Integrate a professional point-of-care testing (POCT) color analysis device to serve as an objective ground truth to properly validate the camera-based algorithm.
*   **Broader Pathological Range**:
    *   *Finding*: The dataset had limited coverage of abnormal values, as the user study involved mostly healthy individuals and control urine was only available in two levels.
    *   *Recommendation*: Conduct larger clinical studies—particularly targeting pregnant women—to acquire a wider distribution of pathological urine parameters (e.g., preeclampsia/eclampsia biomarkers).

---

## 📱 4. User Experience & Usability

*   **Timer & Guidance Optimization**:
    *   *Finding*: The average usability (SUS) score was **71.9**, and many users struggled to capture/evaluate the strip within the manufacturer's strict reaction times (specifically at 60s, where 5 parameters must be read simultaneously).
    *   *Recommendation*: Streamline the web-application flow, improve the interactive guidance, or transition to easier-to-use test strips.
*   **Real-Time Feedback**:
    *   *Finding*: In the study, processing was handled asynchronously offline.
    *   *Recommendation*: Optimize the analysis pipeline to run in real-time on-device (WebAssembly or ONNX runtime) or stream results back to the user instantly.
