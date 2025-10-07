from frappe.printing.doctype.network_printer_settings.network_printer_settings import NetworkPrinterSettings
import frappe
from frappe import _
class NetworkPrinterSettingsOverride(NetworkPrinterSettings):
    @frappe.whitelist()
    def get_printers_list(self, ip="localhost", port="631"):
        if not self.custom_use_python_escpos:
            print("not using python escpos")
            return super().get_printers_list(ip, port)
        else:
            return self.get_python_escpos_printers_list(ip, port)

    def get_python_escpos_printers_list(self, ip="localhost", port="631"):   
        return [{"value": "NETWORK", "label": "Network ESCPOS"}]