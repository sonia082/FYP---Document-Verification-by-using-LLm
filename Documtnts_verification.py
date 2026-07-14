import os
import re
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from transformers import AutoTokenizer, AutoModelForCausalLM
pytesseract.pytesseract.tesseract_cmd = r"E:\Softwares\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"E:\Softwares\Release-24.08.0-0\poppler-24.08.0\Library\bin"
MODEL_PATH = r"E:\Softwares\model\Tiny-LLM"

print(" Loading local Tiny-LLM model...")
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        device_map="cpu",
        dtype=None

    )
    print(" Tiny-LLM loaded successfully!\n")
except Exception as e:
    print(f" Error loading model: {e}")
    print("⚠ Ensure model files (config.json, tokenizer.json, model.safetensors) exist in folder.")
    exit()


# DOCUMENT REQUIREMENTS

DOCUMENT_REQUIREMENTS = {
    "Support Students": [
        "Student ID Card",
        "Enrollment/Admission Letter",
        "Fee Challan / Invoice",
        "Transcript / Mark Sheet",
        "Recommendation Letter"
    ],
    "Care for Patients": [
        "Doctor's Prescription",
        "Hospital Admission Slip",
        "Medical Test Reports",
        "Treatment Cost Estimate / Bill",
        "Disability Certificate"  # Optional
    ],
    "Feed the Hungry": [
        "CNIC Front",
        "CNIC Back",
        "Proof of Income",
        "Household Registration Certificate",  # Optional
        "Utility Bills"
    ],
    "Support Orphans": [
        "Orphan Certificate",
        "Death Certificate",
        "Guardian CNIC Copy",
        "Orphanage Registration",
        "School Enrollment Certificate"
    ]
}


#  Optional Documents
OPTIONAL_DOCUMENTS = [
    "Disability Certificate",
    "Household Registration Certificate"
]


# TEXT EXTRACTION

def extract_text(file_path):
    try:
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            image = Image.open(file_path).convert("L")  # grayscale
            image = image.point(lambda x: 0 if x < 140 else 255, '1')  # thresholding
            return pytesseract.image_to_string(image, lang="eng+urd")

        elif file_path.lower().endswith('.pdf'):
            pages = convert_from_path(file_path, first_page=1, last_page=1, poppler_path=POPPLER_PATH)
            if pages:
                image = pages[0].convert("L")
                image = image.point(lambda x: 0 if x < 140 else 255, '1')
                return pytesseract.image_to_string(image, lang="eng+urd")

        return ""
    except Exception as e:
        print(f"⚠️ Error extracting text: {e}")
        return ""

#  NAME / ID EXTRACTION FUNCTION

def extract_name(text):
    """
    Extracts probable name or ID from document text (English + Urdu)
    """
    patterns = [
        r"Name[:\-]?\s*([A-Za-z\s]+)",
        r"Student Name[:\-]?\s*([A-Za-z\s]+)",
        r"Patient Name[:\-]?\s*([A-Za-z\s]+)",
        r"Guardian Name[:\-]?\s*([A-Za-z\s]+)",
        r"CNIC[:\-]?\s*([0-9\-]{13,15})",
        r"ID[:\-]?\s*([A-Za-z0-9\-]+)",
        r"نام[:：]?\s*([؀-ۿ\s]+)"  # Urdu name
    ]
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if 3 <= len(name) <= 40:
                return name
    return None

# RULE-BASED VERIFICATION

def verify_document(category, doc_name, text):
    text_lower = text.lower()
    rules = {
        # --- Students ---
        "Student ID Card": ["student", "id", "roll", "department", "university", "campus",
                            "شناختی", "یونیورسٹی", "طالبعلم"],
        "Enrollment/Admission Letter": ["admission", "enrollment", "program", "semester", "session",
                                        "داخلہ", "پروگرام", "سمسٹر"],
        "Fee Challan / Invoice": ["fee", "challan", "invoice", "amount", "due date",
                                  "فیس", "چالان", "رسید", "رقم", "ادائیگی"],
        "Transcript / Mark Sheet": ["transcript", "marks", "gpa", "semester", "subject",
                                    "نتیجہ", "نمبروں", "پرچہ"],
        "Recommendation Letter": ["recommendation", "reference", "professor", "faculty", "سفارش"],

        # --- Patients ---
        "Doctor's Prescription": ["doctor", "prescription", "hospital", "medicine", "diagnosis",
                                  "ڈاکٹر", "ہسپتال", "دوائی", "نسخہ"],
        "Hospital Admission Slip": ["hospital", "admission", "ward", "patient",
                                    "داخلہ", "وارڈ", "مریض", "ہسپتال"],
        "Medical Test Reports": ["lab", "report", "blood", "test", "result",
                                 "رپورٹ", "خون", "ٹیسٹ", "نتیجہ"],
        "Treatment Cost Estimate / Bill": ["treatment", "bill", "estimate", "hospital", "charges",
                                           "علاج", "بل", "تخمینہ", "چارجز"],
        "Disability Certificate": ["disability", "certificate", "medical", "assessment",
                                   "معذوری", "سرٹیفیکیٹ", "میڈیکل"],

        # --- Feed the Hungry ---
        "CNIC Front": ["identity", "card", "republic", "pakistan", "name", "شناختی", "کارڈ", "پاکستانی", "نام"],
        "CNIC Back": ["permanent address", "current address", "cnic", "مستقل پتہ", "موجودہ پتہ", "تاریخ"],
        "Proof of Income": ["income", "salary", "certificate", "employer", "آمدنی", "تنخواہ", "سرٹیفیکیٹ"],
        "Household Registration Certificate": ["household", "registration", "family", "member", "خاندان", "رجسٹریشن", "گھرانہ"],
        "Utility Bills": ["electricity", "gas", "water", "bill", "گیس", "بجلی", "پانی", "بل"],

        # --- Orphans ---
        "Orphan Certificate": ["orphan", "child", "certificate", "یتیم", "بچہ", "سرٹیفیکیٹ"],
        "Death Certificate": ["death", "registration", "issued", "certificate", "وفات", "رجسٹریشن", "سرٹیفیکیٹ"],
        "Guardian CNIC Copy": ["guardian", "cnic", "identity", "سرپرست", "شناختی"],
        "Orphanage Registration": ["orphanage", "registration", "child care", "یتیم خانہ", "رجسٹریشن"],
        "School Enrollment Certificate": ["school", "Admission", "certificate", "education",
                                          "سکول", "داخلہ", "تعلیم"]
    }

    keywords = rules.get(doc_name, [])
    matched = [k for k in keywords if k.lower() in text_lower]
    rule_confidence = len(matched) >= 2

    #  Tiny-LLM Verification
    prompt = f"""
    You are an AI document verifier.
    Verify if this text (in English/Urdu) represents a valid {doc_name} for the category {category}.
    Text: {text[:400]}

    Reply with one line only:
     Verified - correct and valid
     Mismatch - wrong category
     Invalid/Fake - unrelated or fake
    """
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(**inputs, max_new_tokens=60)
    response = tokenizer.decode(outputs[0], skip_special_tokens=True).lower()

    if rule_confidence and "verified" in response:
        return " Verified - authentic document"
    elif "mismatch" in response:
        return " Mismatch - valid but wrong category"
    else:
        return " Invalid/Fake - content not genuine"


#  MAIN FUNCTION

def main():
    print(" SMART AI DOCUMENT VERIFICATION (Tiny-LLM + Urdu Support)")
    print("=" * 60)

    categories = list(DOCUMENT_REQUIREMENTS.keys())
    for i, cat in enumerate(categories, 1):
        print(f"{i}. {cat}")

    try:
        choice = int(input("\n Select category (1-4): ")) - 1
        category = categories[choice]
    except:
        print(" Invalid choice.")
        return

    print(f"\n Selected Category: {category}")
    print(" Required Documents:")
    for doc in DOCUMENT_REQUIREMENTS[category]:
        optional_flag = " (Optional)" if doc in OPTIONAL_DOCUMENTS else ""
        print(f" • {doc}{optional_flag}")

    uploaded_files = {}
    for doc_name in DOCUMENT_REQUIREMENTS[category]:
        file_path = input(f"\n Enter file path for '{doc_name}' (or press Enter to skip): ").strip().strip('"')
        if not file_path:
            print("Skipped by user.")
            continue
        if not os.path.exists(file_path):
            print(" File not found. Skipping.")
            continue
        uploaded_files[doc_name] = file_path

    # Count only mandatory documents for success rate
    required_files = len([doc for doc in DOCUMENT_REQUIREMENTS[category] if doc not in OPTIONAL_DOCUMENTS])

    results, verified_count = [], 0
    base_name = None
    base_doc = None

    for doc_name, path in uploaded_files.items():
        print(f"\n Processing: {doc_name}")
        text = extract_text(path)
        if not text.strip():
            print(" No text found (check Urdu OCR setup).")
            results.append({'document_type': doc_name, 'result': "No text"})
            continue


        name_or_id = extract_name(text)
        if name_or_id:
            print(f" Detected Name/ID: {name_or_id}")
        else:
            print(" No clear name/ID found.")

        if base_name is None and name_or_id:
            base_name = name_or_id
            base_doc = doc_name
        elif base_name and name_or_id:
            if name_or_id.lower() != base_name.lower():
                print(f" Name Mismatch: '{doc_name}' name differs from '{base_doc}'")
                results.append({'document_type': doc_name, 'result': " Name Mismatch"})
                continue

        print(" Verifying...")
        result = verify_document(category, doc_name, text)
        print(f" Result: {result}")

        results.append({'document_type': doc_name, 'result': result})
        if "✅" in result and doc_name not in OPTIONAL_DOCUMENTS:
            verified_count += 1

    #  Final summary
    print(f"\n{'='*60}\n VERIFICATION SUMMARY\n{'='*60}")
    print(f" Category: {category}")

    for res in results:
        print(f" {res['document_type']} → {res['result']}")

    for doc_name in DOCUMENT_REQUIREMENTS[category]:
        if doc_name not in uploaded_files:
            if doc_name in OPTIONAL_DOCUMENTS:
                print(f" {doc_name} →  Optional, skipped")
            else:
                print(f" {doc_name} →  Not uploaded")

    percentage = (verified_count / required_files) * 100 if required_files > 0 else 0
    print(f"\n Verified: {verified_count}/{required_files}")
    print(f"Success Rate: {percentage:.1f}%")
    print(" PROFILE STATUS:  VERIFIED" if percentage >= 70 else " PROFILE STATUS:  REJECTED")


if __name__ == "__main__":
    main()
