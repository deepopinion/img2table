import os
import io

try:
    from img2table.ocr import OCRWrapper
    from img2table.document import Image
    from ocr_wrapper import GoogleOCR
    from pdf2image import convert_from_path
except ImportError:
    print("Please install img2table first with 'pip install -e .' and the ocr_wrapper as well as pdf2image")
    raise

#
# Configure GoogleOCR Credentials
#
if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    if os.path.isfile("/credentials.json"):
        credentials_path = "/credentials.json"
    else:
        credentials_path = "~/.config/gcloud/credentials.json"
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.expanduser(credentials_path)

#
# Configure path to test cases
#
src = "./examples/data/TestCases.pdf"
# src = "./examples/data/TestCases_1.pdf"
# src = "../table_ocr_test/Plattendicke.pdf"


#
# Custom implementation using the extended heuristic as well as the ocr_wrapper
#
imgs = convert_from_path(src)
scanner = GoogleOCR()
bboxes = [scanner.ocr(img) for img in imgs]
ocr = OCRWrapper()

tables = []
for page, img in enumerate(imgs):
    img_bytes = io.BytesIO()
    img.save(img_bytes, format=img.format)
    img_bytes = img_bytes.getvalue()

    doc = Image(img_bytes, bboxes=bboxes[page] if bboxes else None)
    extracted_tables = doc.extract_tables(
        ocr=ocr,
        borderless_tables=False,
        implicit_rows=False,
        min_confidence=50,
        detect_borderless_headers=False, # Setting this to true should enable detection of TestCase 7
    )
    tables.extend(extracted_tables)


print(f"Detected {len(tables)} tables.")
for table in tables:
    print("\n\n")
    print("TITLE: " + str(table.title))
    print(table.df)
