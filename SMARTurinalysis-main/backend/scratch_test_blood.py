import os
import sys

# Ensure correct python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from src.domains.blood_analysis.service import BloodAnalysisService

def main():
    pdf_path = "/home/datatuning/Downloads/PythonProjects/nutri-sentinel-project/unilabs results 2.pdf"
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    print("Reading file...")
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    print("Running BloodAnalysisService...")
    service = BloodAnalysisService()
    result = service.process_blood_report(file_bytes, "application/pdf")
    print("\n--- PIPELINE RESULT ---")
    print(f"Patient Name: {result.get('patient_name')}")
    print(f"Report Date: {result.get('report_date')}")
    print(f"Biomarkers count: {len(result.get('biomarkers', []))}")
    print(f"Recommendations: {result.get('recommendations')[:200]}...")

if __name__ == "__main__":
    main()
