from erpnext.accounts.doctype.pos_invoice.pos_invoice import (POSInvoice as POSInvoiceBase)
from frappe.utils.file_manager import save_file
import frappe
from ury_companion_ssw.ury_companion_ssw.overrides.api import generate_zatca_qrcode
class POSInvoice(POSInvoiceBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def before_save(self):
        super().before_save()
        if not frappe.get_doc("URY Companion Settings").zatca_enabled:
            return
        qr_image = generate_zatca_qrcode(self.total_amount, self.tax_amount, self.invoice_time)
        file_doc = save_file(f"Zatca QR {self.name}",qr_image, self.doctype, self.name, is_private=0,decode=False)
        self.custom_zatca_qr_preview = file_doc.file_url
        self.custom_zatca_qr = file_doc.name