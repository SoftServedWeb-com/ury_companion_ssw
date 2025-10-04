import frappe
from frappe.utils.file_manager import save_file
from ury_companion_ssw.ury_companion_ssw.overrides.api import generate_zatca_qrcode
from datetime import datetime
import base64
from io import BytesIO

def validate(doc, method):
    print("validate", doc, method)
    if not frappe.get_doc("URY Companion Settings").zatca_enabled:
            return

    # Assuming 'doc' is the POS Invoice document object in your hook
    arrived_time = datetime.strptime(f"{doc.posting_date} {doc.posting_time}", "%Y-%m-%d %H:%M:%S.%f")
    zatca_timestamp_str = arrived_time.strftime("%Y-%m-%dT%H:%M:%S")

    qr_image = generate_zatca_qrcode(doc.grand_total, doc.total_taxes_and_charges, zatca_timestamp_str)
    
    # 1. Save the QR image to a BytesIO buffer as PNG
    buffered = BytesIO()
    qr_image.save(buffered, format="PNG")
    
    # 2. Base64 encode the binary PNG data
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    # 3. Save the file. 'decode=True' tells Frappe to decode the base64 string
    #    back into binary data (the PNG file) before saving.
    file_doc = save_file(
        f"Zatca QR {doc.name}.png",
        img_str, 
        doc.doctype, 
        doc.name, 
        decode=True,
        is_private=0, 
    )
    
    doc.custom_zatca_qr_preview = file_doc.name
    doc.custom_zatca_qr = file_doc.file_url