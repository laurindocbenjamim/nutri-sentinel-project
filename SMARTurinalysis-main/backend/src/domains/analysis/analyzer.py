"""
Analyzer module for comparing test field colors with reference card fields
and mapping them to clinical results.
"""

import cv2
import numpy as np
import math
from helper import field_extraction as fex
from helper import color_calculation as colcalc

# Clinical result mappings matching the reference card columns after deletions
CLINICAL_MAPPINGS = {
    "Glucose": ["Negative", "100 mg/dL (5.5 mmol/L)", "250 mg/dL (14 mmol/L)", "500 mg/dL (28 mmol/L)", "1000 mg/dL (55 mmol/L)", "2000+ mg/dL (111+ mmol/L)"],
    "Bilirubin": ["Negative", "Small (+)", "Moderate (++)", "Large (+++)"],
    "Ketone": ["Negative", "Trace (5 mg/dL)", "Small (15 mg/dL)", "Moderate (40 mg/dL)", "Large (80 mg/dL)", "Large+ (160 mg/dL)"],
    "SpecificGravity": ["1.000", "1.005", "1.010", "1.015", "1.020", "1.025", "1.030"],
    "Hemoglobin": ["Negative", "Trace non-hemolyzed", "Trace hemolyzed", "Small (+)", "Moderate (++)", "Large (+++)", "Large++ (+++)"],
    "pHValue": ["5.0", "6.0", "6.5", "7.0", "7.5", "8.0", "8.5"],
    "Protein": ["Negative", "Trace", "30 mg/dL (+)", "100 mg/dL (++)", "300 mg/dL (+++)", "2000+ mg/dL (++++)"],
    "Urobilinogen": ["0.2 mg/dL (Normal)", "1.0 mg/dL", "2.0 mg/dL", "4.0 mg/dL", "8.0 mg/dL"],
    "Nitrite": ["Negative", "Positive (+)", "Positive (++)"],
    "Leukocytes": ["Negative", "Trace", "Small (+)", "Moderate (++)", "Large (+++)"]
}

ANALYTES_KEYS = [
    "Glucose", "Bilirubin", "Ketone", "SpecificGravity", 
    "Hemoglobin", "pHValue", "Protein", "Urobilinogen", 
    "Nitrite", "Leukocytes"
]

def extract_testfields(img_stick: np.ndarray) -> list:
    """
    Extracts the 10 testfields directly using exact normalized coordinates
    since the stick is already warped to standard dimensions (400x50).
    """
    # 11 pads (1 ID mark + 10 test fields)
    centers_x = [32.5, 66.5, 100.5, 134.5, 168.5, 202.5, 236.5, 270.5, 304.5, 338.5, 372.5]
    field_width = 16  # 400 * 0.04
    field_height = 30  # 50 * 0.6
    
    testfields = []
    # Skip ID mark (index 0), extract 1 to 10
    for i in range(1, 11):
        x_center = centers_x[i]
        x1 = int(x_center - field_width / 2)
        x2 = int(x_center + field_width / 2)
        y1 = int(25.0 - field_height / 2)
        y2 = int(25.0 + field_height / 2)
        
        field = img_stick[y1:y2, x1:x2]
        testfields.append(field)
    return testfields

def get_mean_bgr(img: np.ndarray) -> list:
    """
    Returns the mean BGR color of an image.
    """
    mean_val = cv2.mean(img)
    return [mean_val[0], mean_val[1], mean_val[2]]

def compute_matching_factor(bgr_stick: list, bgr_ref: list) -> float:
    """
    Calculates the matching factor between two BGR colors.
    """
    delta_red = abs(bgr_stick[2] - bgr_ref[2])
    delta_green = abs(bgr_stick[1] - bgr_ref[1])
    delta_blue = abs(bgr_stick[0] - bgr_ref[0])
    
    # Matching Factor weighted formula
    m_factor = 1.0 - ((0.6429 * delta_red + 0.1786 * delta_green * 100 / 255 + 0.1786 * delta_blue * 100 / 255) / 380.0)
    return m_factor

def analyze_urine(img_card: np.ndarray, img_stick: np.ndarray) -> dict:
    """
    Extracts fields and compares colors, returning matched clinical values.
    """
    # 1. Extract reference fields (applying deletions)
    reffields = fex.separate_reffields(img_card)
    
    # 2. Extract test fields
    testfields = extract_testfields(img_stick)
    
    results = {}
    
    for i, analyte in enumerate(ANALYTES_KEYS):
        stick_field = testfields[i]
        ref_options = reffields[i]
        
        stick_bgr = get_mean_bgr(stick_field)
        
        best_score = -1.0
        best_idx = 0
        
        for idx, ref_img in enumerate(ref_options):
            ref_bgr = get_mean_bgr(ref_img)
            score = compute_matching_factor(stick_bgr, ref_bgr)
            
            if score > best_score:
                best_score = score
                best_idx = idx
                
        # Map to clinical value
        mappings = CLINICAL_MAPPINGS[analyte]
        clinical_value = mappings[min(best_idx, len(mappings) - 1)]
        
        results[analyte] = {
            "value": clinical_value,
            "confidence": round(best_score * 100, 2),
            "stick_color_bgr": [round(c, 1) for c in stick_bgr]
        }
        
    return results
