import os
import frappe
from frappe import _
from ury.ury_pos.api import getBranch
from datetime import datetime
import subprocess
import imgkit # Requires wkhtmltoimage system package
from frappe.www.printview import get_html_and_style


@frappe.whitelist()
def get_restaurant_menu_override(pos_profile, room=None, order_type=None):
    menu_items = []
    menu_items_with_image = []

    user_role = frappe.get_roles()

    pos_profile = frappe.get_doc("POS Profile", pos_profile)

    cashier = any(
        role.role in user_role for role in pos_profile.role_allowed_for_billing
    )
    branch_name = getBranch()
    restaurant = frappe.db.get_value("URY Restaurant", {"branch": branch_name}, "name")
    
    if cashier and order_type:
        order_type_wise_menu = frappe.db.get_value(
            "URY Restaurant", restaurant, "order_type_wise_menu"
        )
    
        if order_type_wise_menu:
            menu = frappe.db.get_value(
                "Order Type Menu",
                {"parent": restaurant, "order_type": order_type},
                "menu"
            )
            if not menu:
                 menu = frappe.db.get_value("URY Restaurant", restaurant, "active_menu")
    
        else:
            menu = frappe.db.get_value("URY Restaurant", restaurant, "active_menu")
    
    elif room:
    
        room_wise_menu = frappe.db.get_value(
            "URY Restaurant", restaurant, "room_wise_menu"
        )
        
        if room_wise_menu:
            menu = frappe.db.get_value(
                "Menu for Room",
                {"parent": restaurant, "room": room},
                "menu"
            )
            if not menu:
                 menu = frappe.db.get_value("URY Restaurant", restaurant, "active_menu")
        else:
            menu = frappe.db.get_value("URY Restaurant", restaurant, "active_menu")
    
    # Default menu if nothing is selected
    else:
        menu = frappe.db.get_value("URY Restaurant", restaurant, "active_menu")
    
    if not menu:
        frappe.throw(_("Please set an active menu for Restaurant {0}").format(restaurant))
    
    
    # Get menu items (your existing code)
    menu_items = frappe.get_all(
        "URY Menu Item",
        filters={"parent": menu, "disabled": 0},
        fields=["item", "item_name", "rate", "special_dish", "disabled", "course","custom_main_category","custom_sub_category"],
        order_by="item_name asc"
    )
    
    menu_items_with_image = [
        {
            "item": item.item,
            "item_name": item.item_name,
            "rate": item.rate,
            "special_dish": item.special_dish,
            "disabled": item.disabled,
            "item_image": frappe.db.get_value("Item", item.item, "image"),
            "course": item.course,
            "main_category": item.custom_main_category,
            "sub_category": item.custom_sub_category,
        }
        for item in menu_items
    ]
    modified = frappe.db.get_value("URY Menu", menu, "modified")
    
    
    return {
        "items": menu_items_with_image,
        "modified_time": modified,
        "name": menu
    }


@frappe.whitelist()
def get_default_customer_override():
    customer = frappe.db.get_value("Customer", {"custom_is_default_customer": 1},["name","customer_name","mobile_number"], as_dict=True)
    return {
        "id": customer.name,
        "name": customer.customer_name,
        "phone": customer.mobile_number,
    }

@frappe.whitelist()
def generate_zatca_qrcode(total_amount, tax_amount, invoice_time):
    from qrzatca import create_zatca_qr

    if not frappe.get_doc("URY Companion Settings").zatca_enabled:
        frappe.throw(_("Zatca is not enabled"))
    else:
        qr_image = create_zatca_qr(
            seller_name=frappe.get_doc("URY Companion Settings").seller_name,
            tax_number=frappe.get_doc("URY Companion Settings").vat_registration_number,
            invoice_time=invoice_time,
            total_amount=total_amount,
            tax_amount=tax_amount
            )
        return qr_image


# @frappe.whitelist()
# def network_printing_override(
#     doctype,
#     name,
#     printer_setting,
#     print_format=None,
#     doc=None,
#     no_letterhead=0,
#     file_path=None, # Hardcoded for testing with escpos 'File' backend
# ):
#     """
#     Overrides Frappe's default print to use the python-escpos library
#     for direct printing to a device node (like /dev/usb/lp0).
#     Only prints the document name and cuts the paper.
#     """
#     print("network_printing_override", doctype, name, printer_setting, print_format, doc, no_letterhead, file_path)
#     from escpos.printer import File

#     printer_driver_path = "/dev/usb/lp0"
#     try:    
#         # 1. Get the document object if not passed
#         if not doc:
#             doc = frappe.get_doc(doctype, name)
        
#         doc_name_to_print = doc.name
#         print("doc_name_to_print", doc_name_to_print)
#         # 2. Initialize the ESC/POS printer using the File backend
#         # This acts like the 'print_test.py' in the documentation.
#         try:
#             # Initialize the printer connection to the device node
#             p = File(printer_driver_path)
            
#             # Print the document name followed by a couple of newlines
#             p.text(f"--- Document Print Test ---\n")
#             p.text(f"Document Name: {doc_name_to_print}\n\n")
            
#             # Send the paper cut command
#             p.cut()
            
#             # Important: Close the connection to flush the buffer and release the file handle
#             p.close()

#         except Exception as e:
#             # Handles errors during ESC/POS initialization or printing
#             return f"Failed to connect or print using python-escpos on {printer_driver_path}: {str(e)}. Check permissions or device path."
            
#         # 3. Update POS Invoice status (Kept the original logic for completeness)
#         if doctype == "POS Invoice":
#             restaurant_table, invoice_printed = frappe.db.get_value(
#                 "POS Invoice", name, ["restaurant_table", "invoice_printed"]
#             )

#             if restaurant_table and invoice_printed == 0:
#                 frappe.db.set_value("POS Invoice", name, "invoice_printed", 1)
#                 # Assuming "URY Table" is a custom DocType
#                 frappe.db.set_value(
#                     "URY Table",
#                     restaurant_table,
#                     {"occupied": 0, "latest_invoice_time": None},
#                 )
#             else:
#                 frappe.db.set_value("POS Invoice", name, "invoice_printed", 1)
        
#         return "Success: Document name printed using python-escpos."
            
#     except Exception as e:
#         # Handles errors getting the document
#         return f"An error occurred while running the print function: {str(e)}"


# Sample receipt data

@frappe.whitelist()
def network_printing_override(
    doctype,
    name,
    printer_setting,
    print_format=None,
    doc=None,
    no_letterhead=0,
    file_path=None, # Not strictly needed, but kept for signature
):
    try:
        print_settings = frappe.get_doc("Network Printer Settings", printer_setting)
        # printer_name = "ProPOS_PP9000EU"
        if not doc:
            data = frappe.get_doc(doctype, name)
        else:
            data = doc

        try:
            result = get_html_and_style(doc=data, print_format=print_format, no_letterhead=no_letterhead)
            final_html = f"<html><head><style>{result['style']}</style></head><body>{result['html']}</body></html>"
            print("final_html", final_html)
        except Exception as e:
            frappe.log_error(f"Error generating HTML and style: {str(e)}", "Network Print Error")
            print("e", e)
            return f"Failed to generate HTML and style for printing: {str(e)}"

        temp_dir = os.path.join(frappe.get_site_path(), "public", "files", "temp_prints")
        frappe.create_folder(temp_dir)
        png_path = os.path.join(temp_dir, f"print-{frappe.generate_hash()}.png")
        config = imgkit.config(wkhtmltoimage='/usr/bin/wkhtmltoimage') # Assumes wkhtmltoimage is in the system PATH
        abs_path = os.path.abspath(png_path)
        try:
            options = {
            'width': '576',  # ~80mm
            'quiet': '',
            'enable-local-file-access': '',  # ✅ CRUCIAL FIX
            'load-error-handling': 'ignore',  # optional: ignore missing resources
            'load-media-error-handling': 'ignore',
            'encoding': 'UTF-8',
            }
            imgkit.from_string(final_html, abs_path, config=config, options=options)
            print("imgkit succeeded")
        except Exception as e:
            frappe.log_error(f"imgkit failed: {str(e)}", "Network Print Error")
            print("e", e)
            return f"Failed to convert HTML to PNG: {str(e)}"

        # 5. Print the PNG using the 'lp' command (CUPS)
        print("printer_name : ", print_settings.custom_custom_printer_name or print_settings.printer_name)
        try:
            subprocess.run(
                        [
                            "lp",
                            "-d", print_settings.custom_custom_printer_name or print_settings.printer_name,
                            "-o", "orientation-requested=3",  # portrait
                            "-o", "fit-to-page",             # scale image to fill page
                            abs_path
                        ],
                        capture_output=True,
                        text=True,
                        check=True
                    )
            print("lp command succeeded")
        except subprocess.CalledProcessError as e:
            frappe.log_error(f"lp command failed: {e.stderr}", "Network Print Error")
            print("e.stderr", e.stderr)
            return f"Failed to send print job via lp: {e.stderr}"

        # 6. Cleanup (Optional, but good practice)
        # try:
        #     os.remove(png_path)
        # except Exception:
        #     pass # Ignore cleanup errors

        # 7. Update POS Invoice status (Kept original logic)
        if doctype == "POS Invoice":
            restaurant_table, invoice_printed = frappe.db.get_value(
                "POS Invoice", name, ["restaurant_table", "invoice_printed"]
            )

            if restaurant_table and invoice_printed == 0:
                frappe.db.set_value("POS Invoice", name, "invoice_printed", 1)
                frappe.db.set_value(
                    "URY Table",
                    restaurant_table,
                    {"occupied": 0, "latest_invoice_time": None},
                )
            else:
                frappe.db.set_value("POS Invoice", name, "invoice_printed", 1)
        
        return "Success: Document printed via CUPS (PNG method)."

    except Exception as e:
        frappe.log_error(str(e), "General Network Print Error")
        return f"An error occurred: {str(e)}"