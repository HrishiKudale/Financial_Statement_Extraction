import fitz  
import pytesseract
from PIL import Image
import io
import re
import os
import json
from difflib import get_close_matches  

# Path to Tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# File paths
INPUT_PDF_PATH = r"C:\Users\User\Desktop\task\data\data (4).pdf"
OUTPUT_JSON_PATH = r"C:\Users\User\Desktop\task\json_outputs\data (4).json"

# Clean up text
def clean_text(text):
    return re.sub(r"[^\x00-\x7F]+", " ", text).strip()

# OCR extract from page
def extract_text_from_page(page):
    pix = page.get_pixmap(dpi=300)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    text = pytesseract.image_to_string(img, config="--psm 6")
    return clean_text(text)

#Normalize label for matching
def normalize(text):
    return re.sub(r'[^a-z]', '', text.lower())

#Fuzzy match labels
def match_label(line, known_labels):
    for label in known_labels:
        matches = get_close_matches(normalize(line), [normalize(label)], cutoff=0.7)
        if matches:
            return label
    return None

#Robust financial parser
def parse_financial_data(text):
    financial_data = {}

    row_labels = [
        "Revenue from operations",
        "Other income",
        "Total income",
        "Cost of construction and development",
        "Changes in inventories of work-in-progress and finished properties",
        "Employee benefit expense",
        "Finance costs",
        "Depreciation and amortisation expenses",
        "Other expenses",
        "Total expenses",
        "Profit/loss before tax",
        "Current tax",
        "Deferred tax",
        "Profit/loss for the period/year",
        "Other comprehensive income/loss",
        "Total comprehensive income/loss for the period/year, net of tax"
    ]

    #Extract periods like "31 Dec 2023", "30 Sep 2023"
    periods = re.findall(r"\d{1,2} \w{3,9} \d{4}", text)

    #Fallback periods
    if len(periods) < 6:
        periods = [
            "Quarter ended 31 December 2024",
            "Quarter ended 30 September 2024",
            "Quarter ended 31 December 2023",
            "Year to date period ended 31 December 2024",
            "Year to date period ended 31 December 2023",
            "Year ended 31 March 2024"
        ]

    #Parse each line and use fuzzy label detection
    lines = text.split('\n')
    for line in lines:
        if not line.strip():
            continue
        # Find numbers
        numbers = re.findall(r'-?\d[\d,]*\.?\d*', line)
        if not numbers:
            continue

        matched_label = match_label(line, row_labels)
        if matched_label:
            clean_values = [float(n.replace(',', '')) for n in numbers]
            for i, val in enumerate(clean_values):
                if i < len(periods):
                    if periods[i] not in financial_data:
                        financial_data[periods[i]] = {}
                    financial_data[periods[i]][matched_label] = val
        else:
            print(f"[WARN] No label match for: {line.strip()}")

    return financial_data

#Main processor
def process_pdf(path):
    doc = fitz.open(path)

    #Page 6 (Consolidated)
    print("[INFO] Extracting Consolidated from page 6")
    page_consolidated = doc[5]
    text_consolidated = extract_text_from_page(page_consolidated)
    print("\n--- PAGE 6 OCR TEXT (First 3000 chars) ---\n", text_consolidated[:3000])
    consolidated_data = parse_financial_data(text_consolidated)

    # Page 11 (Standalone)
    print("[INFO] Extracting Standalone from page 11")
    page_standalone = doc[10]
    text_standalone = extract_text_from_page(page_standalone)
    print("\n--- PAGE 11 OCR TEXT (First 3000 chars) ---\n", text_standalone[:3000])
    standalone_data = parse_financial_data(text_standalone)

    return {
        "Standalone_financial_results_for_all_months": standalone_data,
        "Balance_sheet": "Balance_sheet_are_not_present",
        "Cash_flow_statements": "Cash_flow_statements_are_not_present",
        "Statement_Consolidated_finanacial_results_for_all_months": consolidated_data,
    }

# RUN AND SAVE JSON
if __name__ == "__main__":
    print(f"Processing: {os.path.basename(INPUT_PDF_PATH)}")
    extracted_data = process_pdf(INPUT_PDF_PATH)

    print("\n--- Extracted JSON Preview ---")
    print(json.dumps(extracted_data, indent=4))

    os.makedirs(os.path.dirname(OUTPUT_JSON_PATH), exist_ok=True)

    try:
        with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(extracted_data, f, indent=4)
        print(f" JSON Saved to: {OUTPUT_JSON_PATH}")
    except Exception as e:
        print(f" Error saving JSON: {e}")
