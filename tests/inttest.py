import os
import io

try:
    from img2table.ocr import VisionOCR, OCRWrapper
    from img2table.document import PDF, Image
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
run_original_ocr = False

# 
# Test the classical pipeline with the internal vision ocr
#
if run_original_ocr:
    ocr = VisionOCR()
    doc = PDF(src, pdf_text_extraction=False)
    extracted_tables = doc.extract_tables(
        ocr=ocr,
        borderless_tables=True,
        implicit_rows=False,
        min_confidence=0,
    )

    # Write output
    for page_nr, tables in extracted_tables.items():
        if len(tables) == 0:
            continue

        print(f"\n\n################ PAGE {page_nr+1}")
        for table in tables:
            print("\n\n# ", table.title or "", "\n", table.df)


#
# Custom implementation using the extended heuristic as well as the ocr_wrapper
#
imgs = convert_from_path(src)
scanner = GoogleOCR()
bboxes = [scanner.ocr(img) for img in imgs]
ocr = OCRWrapper()

for page, img in enumerate(imgs):
    # print("\n\n### Page {}".format(page+1))

    img_bytes = io.BytesIO()
    img.save(img_bytes, format=img.format)
    img_bytes = img_bytes.getvalue()

    doc = Image(img_bytes, bboxes=bboxes[page] if bboxes else None)
    extracted_tables = doc.extract_tables(
        ocr=ocr,
        borderless_tables=False,
        implicit_rows=True,
        min_confidence=50,)

    print(f"Detected {len(extracted_tables)} tables on page {page+1}.")

    for table in extracted_tables:
        print("\n\n")
        print("TITLE: " + str(table.title))
        print(table.df)
