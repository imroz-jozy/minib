import pdfplumber

    # ================= PDF IMPORT LOGIC =================
def extract_text_from_pdf(pdf_path):
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += (page.extract_text() or "") + "\n"
            print(f"Extracted {len(text)} characters from PDF.")
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return None
        return text
