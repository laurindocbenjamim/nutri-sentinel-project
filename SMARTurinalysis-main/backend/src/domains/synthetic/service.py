"""
Synthetic Image Generation Service.
Generates template RefCard.jpg, UrineStick.jpg, and combined mock photos.
"""

import os
import cv2
import numpy as np

# Define directories relative to this file
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
REF_IMAGES_DIR = os.path.join(BACKEND_DIR, "referenceimages")

# Color palette for RefCard (BGR format)
PALETTE = {
    0: [[200, 240, 220], [170, 220, 150], [120, 200, 100], [80, 170, 80], [50, 120, 80], [40, 80, 60], [30, 60, 40]],  # Glucose
    1: [[240, 245, 245], [210, 210, 245], [160, 140, 230], [120, 80, 210], [90, 40, 180], [60, 20, 140], [40, 10, 100]],  # Bilirubin
    2: [[235, 240, 245], [210, 200, 230], [180, 150, 210], [150, 100, 190], [120, 60, 160], [90, 30, 130], [60, 10, 100]],  # Ketone
    3: [[150, 90, 40], [120, 120, 50], [90, 150, 60], [80, 180, 100], [100, 200, 150], [120, 220, 200], [150, 240, 240]],  # Spec Grav
    4: [[80, 220, 240], [80, 200, 200], [80, 170, 160], [60, 140, 120], [40, 110, 80], [20, 80, 50], [10, 50, 30]],       # Blood
    5: [[40, 120, 220], [50, 160, 200], [80, 190, 180], [100, 200, 120], [80, 180, 70], [60, 140, 50], [40, 100, 30]],       # pH
    6: [[100, 230, 245], [90, 210, 210], [80, 190, 160], [60, 160, 120], [40, 130, 80], [20, 100, 50], [10, 70, 30]],      # Protein
    7: [[200, 230, 240], [170, 190, 230], [140, 140, 220], [110, 90, 200], [80, 50, 180], [50, 20, 150], [30, 10, 120]],     # Urobilinogen
    8: [[240, 240, 240], [225, 215, 235], [210, 190, 230], [190, 160, 220], [170, 130, 210], [150, 100, 200], [120, 70, 190]], # Nitrite
    9: [[245, 245, 245], [230, 215, 235], [210, 180, 225], [190, 140, 210], [170, 100, 195], [150, 70, 180], [120, 40, 160]], # Leukocytes
}

def generate_ref_card(width: int = 800, height: int = 1200) -> np.ndarray:
    """
    Generate high-resolution synthetic reference card.
    """
    card = np.ones((height, width, 3), dtype=np.uint8) * 255
    cv2.rectangle(card, (10, 10), (width - 10, height - 10), (40, 40, 40), 6)
    
    # Corners for homography
    for x, y in [(60, 60), (width-60, 60), (60, height-60), (width-60, height-60)]:
        cv2.drawMarker(card, (x, y), (0, 0, 0), cv2.MARKER_CROSS, 40, 4)
        cv2.circle(card, (x, y), 15, (0, 0, 0), 2)
        
    cv2.putText(card, "SMART Urinalysis RefCard", (150, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)

    start_x, start_y = 0.186, 0.956
    next_col, row_height = 0.104, 0.039
    next_row = [0, 0.089, 0.157, 0.237, 0.295, 0.377, 0.435, 0.513, 0.581, 0.644]
    analytes = ["GLU", "BIL", "KET", "SG", "BLD", "pH", "PRO", "URO", "NIT", "LEU"]

    for r in range(10):
        y_text = int((start_y - next_row[r] - row_height/2) * height)
        cv2.putText(card, analytes[r], (30, y_text + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 80, 80), 2)
        
        for c in range(7):
            x1 = int((start_x + c * next_col) * width)
            x2 = int((start_x + (c + 1) * next_col) * width)
            y1 = int((start_y - next_row[r] - row_height) * height)
            y2 = int((start_y - next_row[r]) * height)
            
            cv2.rectangle(card, (x1, y1), (x2, y2), PALETTE[r][c], -1)
            cv2.rectangle(card, (x1, y1), (x2, y2), (200, 200, 200), 2)

    return card

def generate_urine_stick(width: int = 200, height: int = 1600) -> np.ndarray:
    """
    Generate high-resolution synthetic urine stick.
    """
    stick = np.ones((height, width, 3), dtype=np.uint8) * 220
    cv2.rectangle(stick, (5, 5), (width - 5, height - 5), (80, 80, 80), 3)
    
    # ID marks and crosshairs for ORB matching texture
    cv2.rectangle(stick, (10, 10), (width - 10, 60), (0, 0, 0), -1)
    cv2.drawMarker(stick, (width//2, 35), (255, 255, 255), cv2.MARKER_CROSS, 20, 2)
    cv2.drawMarker(stick, (width//2, height - 35), (0, 0, 0), cv2.MARKER_CROSS, 20, 2)

    # 11 pads (1 ID mark + 10 test fields)
    for i in range(11):
        y_center = int(130.0 + i * 136.0)
        y1, y2 = y_center - 48, y_center + 48
        x1, x2 = 40, width - 40
        
        color = [50, 50, 50] if i == 0 else PALETTE[i - 1][0]
        cv2.rectangle(stick, (x1, y1), (x2, y2), color, -1)
        cv2.rectangle(stick, (x1, y1), (x2, y2), (0, 0, 0), 3)
        # Add high-contrast cross inside pad for ORB tracking
        cv2.drawMarker(stick, (width//2, y_center), (255, 255, 255) if i == 0 else (0, 0, 0), cv2.MARKER_CROSS, 12, 1)

    return stick

def generate_mock_photo(card: np.ndarray, stick: np.ndarray, selected_indices: dict = None) -> np.ndarray:
    """
    Create a high-resolution combined photo of RefCard and UrineStick.
    """
    canvas = np.ones((1600, 1600, 3), dtype=np.uint8) * 45
    for y in range(1600):
        val = int(45 + 15 * (y / 1600))
        canvas[y, :, :] = [val - 5, val, val + 5]

    modified_stick = stick.copy()
    if selected_indices:
        for r_idx, c_idx in selected_indices.items():
            y_center = int(130.0 + (r_idx + 1) * 136.0)
            y1, y2 = y_center - 48, y_center + 48
            x1, x2 = 40, stick.shape[1] - 40
            cv2.rectangle(modified_stick, (x1, y1), (x2, y2), PALETTE[r_idx][c_idx], -1)
            cv2.rectangle(modified_stick, (x1, y1), (x2, y2), (0, 0, 0), 3)
            cv2.drawMarker(modified_stick, (stick.shape[1]//2, y_center), (0, 0, 0), cv2.MARKER_CROSS, 12, 1)

    # Place RefCard at x=150, y=200
    canvas[200:200+card.shape[0], 150:150+card.shape[1]] = card
    # Place UrineStick at x=1150, y=0 (vertical placement)
    canvas[0:stick.shape[0], 1150:1150+stick.shape[1]] = modified_stick

    return canvas

def ensure_templates_exist() -> None:
    """
    Ensure the referenceimages/ directory and templates exist.
    """
    os.makedirs(REF_IMAGES_DIR, exist_ok=True)
    card_path = os.path.join(REF_IMAGES_DIR, "RefCard.jpg")
    stick_path = os.path.join(REF_IMAGES_DIR, "UrineStick.jpg")
    
    cv2.imwrite(card_path, generate_ref_card())
    cv2.imwrite(stick_path, generate_urine_stick())
