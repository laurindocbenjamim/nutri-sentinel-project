# SMARTurinalysis

## Smartphone-based Colorimetric Analysis of Urine Dipsticks for At-Home Prenatal Care

This project detects and evaluates urine dipsticks from smartphone images.
Steps:
- Detection of the stick and reference card via ORB feature matching (or Mask R-CNN)
- Localisation of the individual test and reference fields
- Color analysis and comparison

## Project Structure

```
SMARTurinalysis-main/
├── object_detection.py          # Entry point 1: detect stick + reference card
├── color_analysis.py            # Entry point 2: colorimetric analysis
├── requirements.txt             # Python dependencies
├── referenceimages/             # YOU MUST CREATE THIS (see below)
│   ├── RefCard.jpg
│   └── UrineStick.jpg
├── control_urine/               # YOU MUST CREATE THIS (see below)
│   └── <subject_id>/
│       └── <step>/
│           └── <images...>
├── helper/
│   ├── color_calculation.py     # HSV / color math
│   ├── correct_stick_rotation.py
│   ├── edge_detector.py         # Canny edge detection
│   ├── field_extraction.py      # Separate test/reference fields
│   ├── image_selection.py       # Tkinter file picker
│   ├── split.py                 # Dataset splitting
│   └── support.py               # I/O utilities
└── mask-rcnn/                   # Mask R-CNN (optional)
    ├── requirements.txt
    ├── setup.py
    ├── mrcnn/                   # Matterport Mask R-CNN implementation
    └── urinestick/
        ├── urinestick.py        # Training & detection script
        ├── training_stick_detection.ipynb
        ├── Detect_all_sticks.ipynb
        └── inspect_stickmodel.ipynb
```

## Prerequisites

- **Python** 3.7+ (recommended)
- **pip**

## Setup

```bash
# 1. Navigate to the project
cd SMARTurinalysis-main

# 2. (Recommended) Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Install Mask R-CNN for deep learning detection
cd mask-rcnn
pip install -r requirements.txt
python setup.py install
cd ..
```

## Data Sources

Images are loaded from three sources depending on the script:

| Source | Script | How it works |
|---|---|---|
| **Hardcoded path** | `object_detection.py` | Reads from `../control_urine/<subject>/<step>/` and `../referenceimages/` (paths relative to the script) |
| **Hardcoded path** | `color_analysis.py` | Reads aligned objects from `results/aligned_objects_subjects/` (previously saved by `object_detection.py`). The original image directory is hardcoded as `../data` |
| **tkinter dialog** | `correct_stick_rotation.py` | Pops up a native OS folder chooser at runtime via `tkinter.filedialog.askdirectory()` |
| **Command-line arg** | `mask-rcnn/urinestick/urinestick.py` | `--dataset=/path/to/dataset` |

### What is tkinter?

`tkinter` is Python's built-in interface to the Tk GUI toolkit. It is part of the standard library (no `pip install` needed). The project uses `tkinter.filedialog` to open native file/folder picker dialogs — `select_image()` and `select_folder()` in `helper/image_selection.py`. Note that while `image_selection` is imported in `color_analysis.py`, it is **not actively called** there (the data path is hardcoded instead). The tkinter dialog is only actually used by `helper/correct_stick_rotation.py`.

## Required Data

The following directories and files are **not included** and must be provided:

### Reference Images
Create `referenceimages/` with two template images used for feature matching:

```
SMARTurinalysis-main/
└── referenceimages/
    ├── RefCard.jpg       # Photo of the reference color card
    └── UrineStick.jpg    # Photo of a blank urine stick
```

### Input Images

Two separate directories are expected by different scripts:

```
parent_project/
├── control_urine/               # Used by object_detection.py
│   └── <subject_id>/
│       └── <step>/              # e.g. "0min", "30s", "120s"
│           └── <image>          # smartphone photo(s)
└── data/                        # Used by color_analysis.py
    └── <subject_id>/
        └── <step>/
            └── <image>
```

Steps are defined in `color_analysis.py` as `EVAL_TIMES = [30, 40, 45, 60, 120]`.

## How to Run

### Pipeline: Object Detection

Detects the urine stick and reference card in each photo using ORB feature matching and homography:

```bash
python object_detection.py
```

Results saved to:
- `results/aligned_objects/` — cropped stick and card images
- `results/matches/` — feature matching visualizations
- `results/corners.json` — corner coordinates

### Pipeline: Color Analysis

Analyzes the aligned objects against the reference card:

```bash
python color_analysis.py
```

Requires aligned objects from the previous step. Results saved to `results/results.json`.

### Mask R-CNN (Alternative Detection)

```bash
cd mask-rcnn

# Train a new model from COCO pre-trained weights
python urinestick/urinestick.py train --dataset=/path/to/dataset --weights=coco

# Resume training from last checkpoint
python urinestick/urinestick.py train --dataset=/path/to/dataset --weights=last

# Run inference on a single image
python urinestick/urinestick.py splash --weights=/path/to/weights.h5 --image=<path>
```

The pre-trained COCO weights (`mask_rcnn_coco.h5`) are downloaded automatically.

## Web API & Interactive Dashboard

A production-ready FastAPI backend and a responsive glassmorphic SPA dashboard are included in the `backend/` directory.

### Features
- **Bounded Monolith Design**: Segregated into `synthetic` and `analysis` domains.
- **Time-Dependent Generation**: The synthetic generator simulates the chemical reaction over time according to Siemens Multistix 10 SG specifications (30s, 40s, 45s, 60s, 120s).
- **ORB Feature Cache**: Templates are pre-computed on initialization, achieving concurrent request latencies of under 0.5 seconds.
- **Sentry Integration**: Exception and performance tracking built-in.

### Running with Uvicorn

To run the web app:

```bash
cd backend
# Run uvicorn pointing to the app module with auto-reload
PYTHONPATH=..:. uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser and navigate to `http://127.0.0.1:8000` to access the interactive dashboard.

### API Endpoints

#### 1. Synthetic Image Generator
- **Endpoint**: `POST /api/synthetic/generate`
- **Description**: Generates a composite mock photo containing the reference card and urine stick.
- **Request Payload**:
  ```json
  {
    "selections": {
      "0": 3,
      "1": 1
    },
    "eval_time": 60
  }
  ```
  *Note:* `selections` maps analyte indices (0-9) to color indices (0-6). `eval_time` specifies the reaction time in seconds (30, 40, 45, 60, 120). Pad colors for analytes whose reaction times exceed `eval_time` are automatically held at the default/unreacted state (index 0).
- **Expected Response**:
  ```json
  {
    "success": true,
    "mock_image_url": "/static/mock_photo.png",
    "ref_card_url": "/static/RefCard.jpg",
    "message": "Templates and mock photo generated successfully."
  }
  ```

#### 2. Urinalysis Processing
- **Endpoint**: `POST /api/analysis/upload`
- **Description**: Uploads a raw camera image to align the stick and reference card, perform colorimetric analysis, and output results.
- **Request Payload**: `Multipart/form-data` with key `file` containing the image.
- **Expected Response**:
  ```json
  {
    "success": true,
    "aligned_card_url": "/static/aligned_card.png",
    "aligned_stick_url": "/static/aligned_stick.png",
    "results": {
      "Glucose": "Negative",
      "Bilirubin": "Negative",
      "Ketone": "15 mg/dL",
      "SpecificGravity": "1.015",
      "Hemoglobin": "Negative",
      "pHValue": "6.0",
      "Protein": "Negative",
      "Urobilinogen": "0.2 EU/dL",
      "Nitrite": "Negative",
      "Leukocytes": "Negative"
    }
  }
  ```

#### 3. Templates
- `GET /api/synthetic/templates/card` - Returns the `RefCard.jpg` template image.
- `GET /api/synthetic/templates/stick` - Returns the `UrineStick.jpg` template image.

---

## 📈 Future Investigations

For future research directions, dataset expansion, and improvements to computer vision/colorimetric accuracy suggested by the paper's authors, see the detailed [Future Investigations & Recommendations](docs/future_investigations.md) document.

## Related Publication

M. Flaucher et al., "Smartphone-Based Colorimetric Analysis of Urine Test Strips for At-Home Prenatal Care," in IEEE Journal of Translational Engineering in Health and Medicine, vol. 10, pp. 1-9, 2022, Art no. 2800109, doi: 10.1109/JTEHM.2022.3179147.

## Authors

- **Madeleine Flaucher** — Initial work

## Acknowledgments

- [Matterport Inc.](https://github.com/matterport/Mask_RCNN) — Mask R-CNN implementation
