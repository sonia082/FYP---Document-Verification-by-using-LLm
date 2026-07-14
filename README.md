# AidLink — Document Verification App

A Streamlit web app that verifies uploaded documents (images/PDFs) against a
required document checklist, using OCR (English + Urdu) and rule-based
keyword matching, with an optional local Tiny-LLM double-check.

```
docverify_app/
├── docverify_app.py            # Streamlit web app (main app)
├── Documtnts_verification.py   # Original CLI/terminal version
└── requirements.txt            # Python dependencies
```

## What This App Does

1. User selects an **aid category** (e.g. "Support Students", "Care for
   Patients", "Feed the Hungry", "Support Orphans").
2. The app shows the **list of required documents** for that category
   (some are marked Optional).
3. User **uploads** each document as an image (PNG/JPG) or PDF — no need
   to type file paths.
4. For each uploaded document, the app:
   - Extracts text using **Tesseract OCR** (supports English + Urdu),
     converting PDFs to images first via **Poppler**.
   - Tries to detect a **Name/ID** from the text and checks it's
     consistent across all uploaded documents (flags a **Name Mismatch**
     if one document belongs to a different person).
   - Runs **rule-based keyword matching** against a per-document-type
     keyword list (English + Urdu keywords) to check the document looks
     genuine.
   - Optionally sends the extracted text to a **local Tiny-LLM** model for
     a second opinion (Verified / Mismatch / Invalid).
5. Shows a final **Verification Summary** with a success percentage and an
   overall **VERIFIED / REJECTED** status (verified if 70%+ of required
   documents pass).

## Setup & Run

```bash
cd docverify_app
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
streamlit run docverify_app.py
```

### System-level requirements (not installed via pip)

- **Tesseract OCR** — must be installed on your machine, with the
  `eng` and `urd` language packs.
- **Poppler** — required by `pdf2image` to convert PDF pages to images.

## Sidebar Configuration

| Setting | Description |
|---|---|
| **Tesseract exe path** | Path to the Tesseract executable. On Windows this is a `.exe` file; on Linux/Mac it's usually just `tesseract`. |
| **Poppler /bin path** | Path to Poppler's `bin` folder. Can be left empty on Linux/Mac if Poppler is already on the system PATH. |
| **Enable Tiny-LLM double-check** | Off by default (loads a heavy model). Turn on to get a second AI opinion on each document. |
| **Tiny-LLM model folder** | Local folder path containing the Tiny-LLM model files (only used if the checkbox above is enabled). |

## Document Categories & Requirements

| Category | Required Documents |
|---|---|
| **Support Students** | Student ID Card, Enrollment/Admission Letter, Fee Challan/Invoice, Transcript/Mark Sheet, Recommendation Letter |
| **Care for Patients** | Doctor's Prescription, Hospital Admission Slip, Medical Test Reports, Treatment Cost Estimate/Bill, Disability Certificate *(Optional)* |
| **Feed the Hungry** | CNIC Front, CNIC Back, Proof of Income, Household Registration Certificate *(Optional)*, Utility Bills |
| **Support Orphans** | Orphan Certificate, Death Certificate, Guardian CNIC Copy, Orphanage Registration, School Enrollment Certificate |

## Enabling Tiny-LLM (optional)

The Tiny-LLM double-check is **off by default** because it needs a large
model loaded into memory. To enable it:

1. Uncomment `transformers` and `torch` in `requirements.txt` and install:
   ```bash
   pip install transformers torch
   ```
2. Check "Enable Tiny-LLM double-check" in the sidebar.
3. Provide the local folder path containing the model files
   (`config.json`, `tokenizer.json`, `model.safetensors`, etc.).

## Two Versions Included

- **`docverify_app.py`** — the current Streamlit web UI. Documents are
  uploaded through the browser (drag & drop / file picker). This is the
  recommended version to run.
- **`Documtnts_verification.py`** — the original command-line (terminal)
  version. Documents are provided by typing file paths, and the Tiny-LLM
  model is loaded automatically at startup (no toggle). Kept here for
  reference / offline batch use.

## Notes

- Hardcoded Windows paths (`E:\...`) in the Streamlit version are
  editable from the sidebar, since these paths differ across machines.
- OCR quality depends heavily on image clarity — blurry or low-resolution
  uploads may return "No text found."
- Name/ID matching is a simple pattern-based extraction and may not catch
  every document layout; it's a helpful check, not a guarantee.
