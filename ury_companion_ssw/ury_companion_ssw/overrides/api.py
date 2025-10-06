import os
from stat import FILE_ATTRIBUTE_OFFLINE
import frappe
from frappe import _
from ury.ury_pos.api import getBranch
from datetime import datetime
import subprocess
import imgkit # Requires wkhtmltoimage system package
from frappe.www.printview import  get_rendered_raw_commands
import io
from base64 import b64encode
from pyqrcode import create as qr_create
from frappe.utils.data import add_to_date, get_time, getdate

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

def generate_zatca_qr_data_and_image(doc):
    """
    Generates the ZATCA Phase 1 (TLV encoded) Base64 string and the QR code image data.

    Args:
        doc (frappe.model.document.Document): The invoice/sales document object 
            containing required fields (e.g., posting_date, base_grand_total).

    Returns:
        tuple: (base64_string, qr_image_bytes)
            - base64_string (str): The ZATCA-compliant TLV data encoded in Base64.
            - qr_image_bytes (bytes): The raw PNG data of the generated QR code image.
    """
    # --- 1. Data Retrieval and Validation (Simplified) ---
    # Retrieve Seller Name
    seller_name = frappe.db.get_value("Company", doc.company, "company_name_in_arabic")
    if not seller_name:
        frappe.throw(f"Arabic name missing for {doc.company} in the Company document")

    # Retrieve VAT Number
    tax_id = frappe.db.get_value("Company", doc.company, "tax_id")
    if not tax_id:
        frappe.throw(f"Tax ID missing for {doc.company} in the Company document")

    # Calculate Time Stamp in required format (YYYY-MM-DDThh:mm:ssZ)
    posting_date = getdate(doc.posting_date)
    time = get_time(doc.posting_time)
    seconds = time.hour * 60 * 60 + time.minute * 60 + time.second
    time_stamp = add_to_date(posting_date, seconds=seconds)
    time_stamp = time_stamp.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Invoice Amount and VAT Amount
    invoice_amount = str(doc.grand_total)
    vat_amount = str(doc.total_taxes_and_charges)

    # --- 2. TLV Encoding Function ---
    def encode_tlv(tag_number, value):
        tag = bytes([tag_number]).hex()
        # Encode value to UTF-8 to correctly handle Arabic characters (Seller Name)
        encoded_value = value.encode("utf-8")
        length = bytes([len(encoded_value)]).hex()
        value_hex = encoded_value.hex()
        return "".join([tag, length, value_hex])

    # --- 3. Construct TLV Array and Buffer ---
    tlv_array = []
    
    # 1. Seller's Name (Tag 1)
    tlv_array.append(encode_tlv(1, seller_name))
    
    # 2. VAT Number (Tag 2)
    tlv_array.append(encode_tlv(2, tax_id))
    
    # 3. Time Stamp (Tag 3)
    tlv_array.append(encode_tlv(3, time_stamp))
    
    # 4. Invoice Amount (Tag 4)
    tlv_array.append(encode_tlv(4, invoice_amount))
    
    # 5. VAT Amount (Tag 5)
    tlv_array.append(encode_tlv(5, vat_amount))

    # Joining hex parts into one TLV buffer string
    tlv_buff = "".join(tlv_array)

    # Base64 conversion
    base64_string = b64encode(bytes.fromhex(tlv_buff)).decode()

    # --- 4. QR Code Image Generation ---
    qr_image = io.BytesIO()
    # Create QR code from the Base64 string
    url = qr_create(base64_string, error="L")
    # Generate PNG data into the in-memory buffer
    url.png(qr_image, scale=8, quiet_zone=1)
    
    qr_image_bytes = qr_image.getvalue()

    return base64_string, qr_image_bytes


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
        # get the printer settings ( printer name )
        print_settings = frappe.get_doc("Network Printer Settings", printer_setting)
        
        # get the data to be printed ( doctype )
        if not doc:
            data = frappe.get_doc(doctype, name)
        else:
            data = doc

        try:            
            # generate the raw data ( applying the jinja template )
            result = get_rendered_raw_commands(doc=data, print_format=print_format)
            print("result", result["raw_commands"])

        except Exception as e:
            
            frappe.log_error(f"Error generating raw commands: {str(e)}", "Network Print Error")
            print("e", e)
            return f"Failed to generate raw commands for printing: {str(e)}"

        # save the raw data to a .bin file
        temp_dir = os.path.join(frappe.get_site_path(), "public", "files", "temp_prints")
        frappe.create_folder(temp_dir)
        bin_path = os.path.join(temp_dir, f"print-{data.name}.bin")
        abs_path = os.path.abspath(bin_path)
        with open(abs_path, "w") as f:
            f.write(result["raw_commands"])
        
        try:
            subprocess.run(
                        [
                            "lp",
                            "-d", print_settings.custom_custom_printer_name or print_settings.printer_name,
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
        #     os.remove(bin_path)
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
        
        return "Success: Document printed via CUPS (BIN method)."

    except Exception as e:
        frappe.log_error(str(e), "General Network Print Error")
        return f"An error occurred: {str(e)}"