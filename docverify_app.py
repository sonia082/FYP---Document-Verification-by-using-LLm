import os
import re
import tempfile

import streamlit as st
from PIL import Image

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None


# PAGE CONFIG

st.set_page_config(page_title="AI Document Verification", page_icon=" ", layout="wide")


# SIDEBAR - CONFIG

st.sidebar.title("Settings")

tesseract_cmd = st.sidebar.text_input(
    "Tesseract exe path (Windows only)",
    value="",
    help="Sirf Windows par apna .exe path yahan likhein (e.g. C:\\...\\tesseract.exe). "
         "Streamlit Cloud / Linux / Mac par ye khali hi chhodein — Tesseract system "
         "se automatically mil jayega (packages.txt ke zariye install hota hai).",
)
poppler_path = st.sidebar.text_input(
    "Poppler /bin path (Windows only)",
    value="",
    help="Sirf Windows par apna poppler bin folder path yahan likhein. "
         "Streamlit Cloud / Linux / Mac par khali hi chhodein.",
)

use_tiny_llm = st.sidebar.checkbox("Enable Tiny-LLM double-check", value=False)
model_path = st.sidebar.text_input(
    "Tiny-LLM model folder",
    value=r"E:\Softwares\model\Tiny-LLM",
    disabled=not use_tiny_llm,
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Note: Yeh app apna khud ka virtual environment use karega jisme "
    "`streamlit`, `pytesseract`, `pdf2image`, `pillow`, aur (agar Tiny-LLM "
    "chahiye to) `transformers` + `torch` installed hon. Tesseract OCR aur "
    "Poppler system-level bhi install hone chahiye (Streamlit Cloud par "
    "`packages.txt` file se: tesseract-ocr, tesseract-ocr-urd, poppler-utils)."
)

if pytesseract is None:
    st.sidebar.error("pytesseract installed nahi hai — pip install pytesseract")
if convert_from_path is None:
    st.sidebar.error("pdf2image installed nahi hai — pip install pdf2image")

# Sirf tab apply karo jab user ne khud kuch likha ho (Windows use-case).
# Linux/Streamlit Cloud par khali chhodne se pytesseract system PATH se
# khud tesseract dhoond leta hai.
if pytesseract and tesseract_cmd.strip():
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd.strip()


# DOCUMENT REQUIREMENTS

DOCUMENT_REQUIREMENTS = {
    "Support Students": [
        "Student ID Card",
        "Enrollment/Admission Letter",
        "Fee Challan / Invoice",
        "Transcript / Mark Sheet",
        "Recommendation Letter",
    ],
    "Care for Patients": [
        "Doctor's Prescription",
        "Hospital Admission Slip",
        "Medical Test Reports",
        "Treatment Cost Estimate / Bill",
        "Disability Certificate",  # Optional
    ],
    "Feed the Hungry": [
        "CNIC Front",
        "CNIC Back",
        "Proof of Income",
        "Household Registration Certificate",  # Optional
        "Utility Bills",
    ],
    "Support Orphans": [
        "Orphan Certificate",
        "Death Certificate",
        "Guardian CNIC Copy",
        "Orphanage Registration",
        "School Enrollment Certificate",
    ],
}

OPTIONAL_DOCUMENTS = [
    "Disability Certificate",
    "Household Registration Certificate",
]

RULES = {
    "Student ID Card": ["student", "id", "roll", "department", "university", "campus",
                        "شناختی", "یونیورسٹی", "طالبعلم"],
    "Enrollment/Admission Letter": ["admission", "enrollment", "program", "semester", "session",
                                    "داخلہ", "پروگرام", "سمسٹر"],
    "Fee Challan / Invoice": ["fee", "challan", "invoice", "amount", "due date",
                              "فیس", "چالان", "رسید", "رقم", "ادائیگی"],
    "Transcript / Mark Sheet": ["transcript", "marks", "gpa", "semester", "subject",
                                "نتیجہ", "نمبروں", "پرچہ"],
    "Recommendation Letter": ["recommendation", "reference", "professor", "faculty", "سفارش"],
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
    "CNIC Front": ["identity", "card", "republic", "pakistan", "name", "شناختی", "کارڈ", "پاکستانی", "نام"],
    "CNIC Back": ["permanent address", "current address", "cnic", "مستقل پتہ", "موجودہ پتہ", "تاریخ"],
    "Proof of Income": ["income", "salary", "certificate", "employer", "آمدنی", "تنخواہ", "سرٹیفیکیٹ"],
    "Household Registration Certificate": ["household", "registration", "family", "member",
                                           "خاندان", "رجسٹریشن", "گھرانہ"],
    "Utility Bills": ["electricity", "gas", "water", "bill", "گیس", "بجلی", "پانی", "بل"],
    "Orphan Certificate": ["orphan", "child", "certificate", "یتیم", "بچہ", "سرٹیفیکیٹ"],
    "Death Certificate": ["death", "registration", "issued", "certificate", "وفات", "رجسٹریشن", "سرٹیفیکیٹ"],
    "Guardian CNIC Copy": ["guardian", "cnic", "identity", "سرپرست", "شناختی"],
    "Orphanage Registration": ["orphanage", "registration", "child care", "یتیم خانہ", "رجسٹریشن"],
    "School Enrollment Certificate": ["school", "admission", "certificate", "education",
                                      "سکول", "داخلہ", "تعلیم"],
}

NAME_PATTERNS = [
    r"Name[:\-]?\s*([A-Za-z\s]+)",
    r"Student Name[:\-]?\s*([A-Za-z\s]+)",
    r"Patient Name[:\-]?\s*([A-Za-z\s]+)",
    r"Guardian Name[:\-]?\s*([A-Za-z\s]+)",
    r"CNIC[:\-]?\s*([0-9\-]{13,15})",
    r"ID[:\-]?\s*([A-Za-z0-9\-]+)",
    r"نام[:：]?\s*([؀-ۿ\s]+)",
]


# TINY-LLM (loaded once, lazily, only if enabled)

@st.cache_resource(show_spinner="Loading Tiny-LLM model...")
def load_tiny_llm(path: str):
    from transformers import AutoTokenizer, AutoModelForCausalLM
    tokenizer = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(path, device_map="cpu")
    return tokenizer, model



# CORE LOGIC

def extract_text(file_path: str) -> str:
    try:
        if file_path.lower().endswith((".png", ".jpg", ".jpeg")):
            image = Image.open(file_path).convert("L")
            image = image.point(lambda x: 0 if x < 140 else 255, "1")
            return pytesseract.image_to_string(image, lang="eng+urd")

        elif file_path.lower().endswith(".pdf"):
            kwargs = {"first_page": 1, "last_page": 1}
            if poppler_path.strip():
                kwargs["poppler_path"] = poppler_path.strip()
            pages = convert_from_path(file_path, **kwargs)
            if pages:
                image = pages[0].convert("L")
                image = image.point(lambda x: 0 if x < 140 else 255, "1")
                return pytesseract.image_to_string(image, lang="eng+urd")

        return ""
    except Exception as e:
        st.warning(f"OCR error: {e}")
        return ""


def extract_name(text: str):
    for p in NAME_PATTERNS:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if 3 <= len(name) <= 40:
                return name
    return None


def verify_document(category: str, doc_name: str, text: str) -> str:
    text_lower = text.lower()
    keywords = RULES.get(doc_name, [])
    matched = [k for k in keywords if k.lower() in text_lower]
    rule_confidence = len(matched) >= 2

    llm_response = ""
    if use_tiny_llm:
        try:
            tokenizer, model = load_tiny_llm(model_path)
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
            llm_response = tokenizer.decode(outputs[0], skip_special_tokens=True).lower()
        except Exception as e:
            st.warning(f"Tiny-LLM error: {e}")

    if rule_confidence and (not use_tiny_llm or "verified" in llm_response):
        return " Verified - authentic document"
    elif use_tiny_llm and "mismatch" in llm_response:
        return " Mismatch - valid but wrong category"
    elif rule_confidence:
        return " Verified - authentic document"
    else:
        return " Invalid/Fake - content not genuine"


def save_upload_to_temp(uploaded_file) -> str:
    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        return tmp.name



# MAIN UI

st.title(" Smart AI Document Verification")
st.caption("Tiny-LLM + Urdu Support — ab web UI ke sath")

category = st.selectbox("Category select karein", list(DOCUMENT_REQUIREMENTS.keys()))

st.markdown("### Required Documents")
required_docs = DOCUMENT_REQUIREMENTS[category]
for doc in required_docs:
    flag = " *(Optional)*" if doc in OPTIONAL_DOCUMENTS else ""
    st.markdown(f"- {doc}{flag}")

st.markdown("### Upload Documents")
uploaded_files = {}
cols = st.columns(2)
for i, doc_name in enumerate(required_docs):
    with cols[i % 2]:
        f = st.file_uploader(
            f"{doc_name}" + (" (Optional)" if doc_name in OPTIONAL_DOCUMENTS else ""),
            type=["png", "jpg", "jpeg", "pdf"],
            key=f"upload_{category}_{doc_name}",
        )
        if f is not None:
            uploaded_files[doc_name] = f

run = st.button(" Verify Documents", type="primary", disabled=(pytesseract is None))

if run:
    if not uploaded_files:
        st.error("At least upload one documents.")
    else:
        results = []
        verified_count = 0
        base_name, base_doc = None, None
        required_count = len([d for d in required_docs if d not in OPTIONAL_DOCUMENTS])

        progress = st.progress(0.0)
        for idx, (doc_name, uploaded_file) in enumerate(uploaded_files.items()):
            with st.expander(f"📎 {doc_name}", expanded=True):
                tmp_path = save_upload_to_temp(uploaded_file)
                text = extract_text(tmp_path)
                os.unlink(tmp_path)

                if not text.strip():
                    st.warning("No text found (check Urdu OCR setup / image quality).")
                    results.append({"document_type": doc_name, "result": "No text"})
                    progress.progress((idx + 1) / len(uploaded_files))
                    continue

                name_or_id = extract_name(text)
                if name_or_id:
                    st.info(f"Detected Name/ID: **{name_or_id}**")
                else:
                    st.caption("No clear name/ID found.")

                mismatch = False
                if base_name is None and name_or_id:
                    base_name = name_or_id
                    base_doc = doc_name
                elif base_name and name_or_id and name_or_id.lower() != base_name.lower():
                    st.error(f"Name Mismatch: '{doc_name}' differs from '{base_doc}'")
                    results.append({"document_type": doc_name, "result": " Name Mismatch"})
                    mismatch = True

                if not mismatch:
                    with st.spinner("Verifying..."):
                        result = verify_document(category, doc_name, text)
                    st.write(f"**Result:** {result}")
                    results.append({"document_type": doc_name, "result": result})
                    if " " in result and doc_name not in OPTIONAL_DOCUMENTS:
                        verified_count += 1

                with st.popover("Show extracted text"):
                    st.text(text[:1000])

            progress.progress((idx + 1) / len(uploaded_files))

        #Summary
        st.markdown("---")
        st.markdown("##  Verification Summary")
        st.markdown(f"**Category:** {category}")

        for res in results:
            st.markdown(f"- {res['document_type']} → {res['result']}")

        for doc_name in required_docs:
            if doc_name not in uploaded_files:
                if doc_name in OPTIONAL_DOCUMENTS:
                    st.markdown(f"- {doc_name} →  Optional, skipped")
                else:
                    st.markdown(f"- {doc_name} →  Not uploaded")

        percentage = (verified_count / required_count) * 100 if required_count > 0 else 0
        st.metric("Verified", f"{verified_count}/{required_count}")
        st.progress(min(percentage / 100, 1.0))
        st.markdown(f"**Success Rate:** {percentage:.1f}%")

        if percentage >= 70:
            st.success(" PROFILE STATUS: VERIFIED")
        else:
            st.error(" PROFILE STATUS: REJECTED")
