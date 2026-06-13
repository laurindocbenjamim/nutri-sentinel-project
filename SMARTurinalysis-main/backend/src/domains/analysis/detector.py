"""
Detector module for aligning and cropping the Urine Stick and RefCard from an image.
Uses ORB feature matching and homography.
"""

import os
import cv2
import numpy as np
import imutils
import math
from src.domains.synthetic.service import REF_IMAGES_DIR

# Max features for ORB
MAX_FEATURES = 3000

class UrineDetector:
    """
    Handles detection and perspective warping of the RefCard and UrineStick.
    """
    def __init__(self):
        self._initialized = False
        self._ref_card = None
        self._ref_stick = None
        self.orb = cv2.ORB_create(MAX_FEATURES)

    def _lazy_init(self) -> None:
        """
        Lazily loads the template reference images and precomputes ORB keypoints/descriptors.
        If files do not exist, they are dynamically generated.
        """
        if self._initialized:
            return
            
        card_file = os.path.join(REF_IMAGES_DIR, "RefCard.jpg")
        stick_file = os.path.join(REF_IMAGES_DIR, "UrineStick.jpg")
        
        if not os.path.exists(card_file) or not os.path.exists(stick_file):
            from src.domains.synthetic.service import SyntheticGenerator
            generator = SyntheticGenerator()
            generator.ensure_templates_exist()
            
        self._ref_card = cv2.imread(card_file)
        self._ref_stick = cv2.imread(stick_file)
        
        if self._ref_card is None or self._ref_stick is None:
            raise FileNotFoundError("Reference card or stick templates could not be loaded.")
            
        ref_card_gray = cv2.cvtColor(self._ref_card, cv2.COLOR_BGR2GRAY)
        self.kp_card, self.des_card = self.orb.detectAndCompute(ref_card_gray, None)
        
        ref_stick_gray = cv2.cvtColor(self._ref_stick, cv2.COLOR_BGR2GRAY)
        self.kp_stick, self.des_stick = self.orb.detectAndCompute(ref_stick_gray, None)
        
        self._initialized = True

    @property
    def ref_card(self) -> np.ndarray:
        """
        Property to retrieve ref_card template (triggers lazy initialization).
        """
        self._lazy_init()
        return self._ref_card

    @property
    def ref_stick(self) -> np.ndarray:
        """
        Property to retrieve ref_stick template (triggers lazy initialization).
        """
        self._lazy_init()
        return self._ref_stick

    def find_object(self, image: np.ndarray, reference: np.ndarray, good_match_percent: float) -> tuple:
        """
        Finds matching features using ORB, calculates homography, and warps perspective.
        """
        image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        kp1, des1 = self.orb.detectAndCompute(image_gray, None)
        if des1 is None:
            return None, None
            
        if reference is self.ref_card:
            kp2, des2 = self.kp_card, self.des_card
        elif reference is self.ref_stick:
            kp2, des2 = self.kp_stick, self.des_stick
        else:
            reference_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
            kp2, des2 = self.orb.detectAndCompute(reference_gray, None)

        if des2 is None:
            return None, None

        if des1 is None or des2 is None:
            return None, None

        matcher = cv2.DescriptorMatcher_create(cv2.DESCRIPTOR_MATCHER_BRUTEFORCE_HAMMING)
        matches = matcher.match(des1, des2, None)
        matches = sorted(matches, key=lambda x: x.distance)

        num_good_matches = int(len(matches) * good_match_percent)
        matches = matches[:num_good_matches]

        if len(matches) < 4:
            return None, None

        pts1 = np.zeros((len(matches), 2), dtype=np.float32)
        pts2 = np.zeros((len(matches), 2), dtype=np.float32)

        for i, match in enumerate(matches):
            pts1[i, :] = kp1[match.queryIdx].pt
            pts2[i, :] = kp2[match.trainIdx].pt

        h, _ = cv2.findHomography(pts1, pts2, cv2.RANSAC)
        h_rev, _ = cv2.findHomography(pts2, pts1, cv2.RANSAC)

        if h is None or h_rev is None:
            return None, None

        ref_h, ref_w, _ = reference.shape
        
        # Warp perspective to get aligned object
        warped = cv2.warpPerspective(image, h, (ref_w, ref_h))
        
        # Calculate corners in the original image
        top_left = h_rev.dot(np.array([0, 0, 1]))
        down_left = h_rev.dot(np.array([0, ref_h, 1]))
        down_right = h_rev.dot(np.array([ref_w, ref_h, 1]))
        top_right = h_rev.dot(np.array([ref_w, 0, 1]))

        corners = np.array([
            top_left[:2]/top_left[2],
            down_left[:2]/down_left[2],
            down_right[:2]/down_right[2],
            top_right[:2]/top_right[2]
        ], dtype='int32')

        return warped, corners

    def detect_stick(self, image: np.ndarray, corners_refcard: np.ndarray) -> np.ndarray:
        """
        Detects, crops and rotates the Urine Stick.
        """
        # Copy to avoid mutating original image
        img_copy = image.copy()
        
        # Black out RefCard in image copy to avoid false matches
        if corners_refcard is not None:
            cv2.fillPoly(img_copy, [corners_refcard], 0)

        # Warp translation to prevent crop cut-offs
        img_h, img_w, _ = img_copy.shape
        T = np.float32([[1, 0, img_w/2], [0, 1, img_h/2]])
        img_mod = cv2.warpAffine(img_copy, T, (img_w*2, img_h*2))

        # Detect the stick
        res = self.find_object(img_mod, self.ref_stick, 0.1)
        if res is None or res[0] is None:
            return None
            
        detected_stick, _ = res
        
        # Orient horizontally
        if detected_stick.shape[1] < detected_stick.shape[0]:
            detected_stick = imutils.rotate_bound(detected_stick, -90)
            
        # Ensure it has exactly the rotated template dimensions (400x50)
        cropped = cv2.resize(detected_stick, (400, 50))
        return cropped
