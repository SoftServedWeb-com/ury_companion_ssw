import frappe
from frappe.utils.file_manager import save_file
# Assuming the extracted function is correctly named and imported:
from ury_companion_ssw.ury_companion_ssw.overrides.api import generate_zatca_qr_data_and_image
import base64
# from datetime import datetime # No longer needed for timestamp logic here
# from io import BytesIO # No longer needed for saving image

def validate(doc, method):
    # print("validate", doc, method) # Keep or remove for debugging

    # --- 1. ZATCA Check ---
    if not frappe.get_doc("URY Companion Settings").zatca_enabled:
        return

   
    zatca_code, qr_image_bytes = generate_zatca_qr_data_and_image(doc)
   
    img_str_b64 = base64.b64encode(qr_image_bytes).decode("utf-8")
    
    file_doc = save_file(
        f"Zatca QR {doc.name}.png",
        img_str_b64, 
        doc.doctype, 
        doc.name, 
        decode=True, # Critical: decodes the Base64 string back to binary PNG
        is_private=0, 
    )
    
    # --- 5. Update Document Fields ---
    doc.custom_zatca_qr_preview = file_doc.name
    doc.custom_zatca_qr = file_doc.file_url
    doc.custom_zatca_code = zatca_code
    