import os
import frappe
from frappe import _
from ury.ury_pos.api import getBranch
from datetime import datetime

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


@frappe.whitelist()
def network_printing_override(
    doctype,
    name,
    printer_setting,
    print_format=None,
    doc=None,
    no_letterhead=0,
    file_path=None,
):
    try:
        print_settings = frappe.get_doc("Network Printer Settings", printer_setting)

        try:
            import cups
        except ImportError:
            return "Failed to import cups"

        try:
            cups.setServer(print_settings.server_ip)
            cups.setPort(print_settings.port)
            conn = cups.Connection()
            print("conn", conn)
        except Exception as e:
            print("error", e)
            return f"Failed to connect to the printer: {str(e)}"
        pdf_options = {
            "page-width": "80mm",
            "page-height": "auto", # Use a large height or 'auto' for receipts
            "page-size": "Custom"   # Important: Set to Custom to use width/height
            }

        try:
            # output = PdfWriter()
            output = frappe.get_print(
                doctype,
                name,
                print_format,
                doc=doc,
                # no_letterhead=no_letterhead,
                as_pdf=True,
                pdf_options=pdf_options,
            )
            if not file_path:
                file_path = os.path.join("/", "tmp", f"frappe-pdf-{frappe.generate_hash()}.pdf")

            # 'output' should be the PDF *bytes* returned by frappe.get_print
            with open(file_path, "wb") as f:
                f.write(output)

            # Then call the print function
            conn.printFile(print_settings.printer_name, file_path, name, {})

            restaurant_table, invoice_printed, name = frappe.db.get_value(
                "POS Invoice", name, ["restaurant_table", "invoice_printed", "name"]
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

            return "Success"
        except Exception as e:
            return f"Failed to print: {str(e)}"
    except Exception as e:
        import traceback

        traceback.print_exc()  # Print the full traceback for debugging
        return f"An error occurred: {str(e)}"

