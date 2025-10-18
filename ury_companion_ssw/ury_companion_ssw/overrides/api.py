import os
from stat import FILE_ATTRIBUTE_OFFLINE
import frappe
from frappe import _
from ury.ury_pos.api import getBranch
from datetime import datetime
import json
import io
from base64 import b64encode
from pyqrcode import create as qr_create
from frappe.utils.data import add_to_date, get_time, getdate
from ury.ury.doctype.ury_order.ury_order import kot_execute, get_order_invoice

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
    seller_name = frappe.db.get_value("Company", doc.company, "name") #TODO: need to change this
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
        print("PRINTING DOCUMENT", doctype)
        if(print_settings.custom_use_python_escpos):
            if(doctype == "POS Invoice"):
                res = print_pos_invoice(data, print_settings)
            elif(doctype == "URY KOT"):
                res = print_kot_order(data, print_settings)
            else:   
                pass
        else:
            pass
        
        # if the document is a POS Invoice and the script printed successfully, set the invoice_printed flag to 1
        if doctype == "POS Invoice" and res:
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

from escpos.printer import Network,Dummy # Import your printer class
from escpos.constants import QR_ECLEVEL_L # Needed for the full receipt function

def print_pos_invoice(doc, print_settings):
    print("Printing POS Invoice")
    company = frappe.get_doc("Company", doc.company)
    tax_id = frappe.db.get_value("Company", doc.company, "tax_id")
    
    # This list is no longer needed since we print inside the loop
    # print_items_list = [] 
    
    d = Dummy()
    d.profile.profile_data["media"]["width"]["pixels"] = 576
    d.set(font='b')
    if(company.company_logo):
        abs_path = os.path.abspath(os.path.join(frappe.get_site_path('public'), company.company_logo.lstrip('/')))
        d.image(abs_path, center=True)
    d.ln(1)
    d.set(bold=True,align='center',double_height=True, )
    d.textln(company.name.upper())
    d.set(double_height=False)
    d.textln(f"VAT/Tax No: {tax_id}")
    d.set(bold=False)
    if(doc.custom_zatca_code):
         d.qr(doc.custom_zatca_code, ec=QR_ECLEVEL_L, size=5, center=True)
    d.set(align='left')

# --- New Transaction Details Section ---
    d.textln(f"Invoice No.: {doc.name}")
    if doc.order_type:
        d.textln(f"Order Type : {doc.order_type}")
    if doc.no_of_pax:
        d.textln(f"Table/Pax : {doc.no_of_pax}") # Added table/pax info
    d.textln(f"Date/Time : {doc.get_formatted('posting_date')} {doc.get_formatted('posting_time')[:8]}")
    if doc.cashier:
        d.textln(f"Cashier : {doc.cashier}")
    TOTAL_WIDTH = 48
    
    # Item Name (19) | Qty (4)  | Rate (8) | Amount (9) -> Total 40 (Adjusted widths for total 42 if needed)
    COLUMN_WIDTHS = [24,5,6,13] 
    COLUMN_ALIGNMENT = ['left', 'left', 'right', 'right']

    # CRITICAL FIX 1: Align header names with the data order below (Qty, Item Name, Rate, Amount)
    header_list = ["ITEM", "QTY", "RATE", "AMOUNT"]
    d.textln("-" * sum(COLUMN_WIDTHS))

    # --- 1. Print the Header Row ---
    try:
        # Print the Header
        d.set(bold=True)
        d.software_columns(header_list, COLUMN_WIDTHS, COLUMN_ALIGNMENT)
        d.set(bold=False)
    except Exception as e:
        print(f"Error printing header: {e}")
        return "Error: Failed to print header"

    d.textln("-" * sum(COLUMN_WIDTHS)) # Print separator line
    
    # --- 2. Print Each Item Row in a Loop ---
    for item in doc.items:
        # 1. Extract and format the data for the columns
        item = item.as_dict()
        try:
            # Data preparation must be in the same order as the header_list: QTY, ITEM, RATE, AMOUNT
            item_name_str = item.get('item_name', '')[:COLUMN_WIDTHS[0]] 
            qty_str = str(int(item.get('qty', 0)))
            # Truncate item name to fit column width
            rate_str = f"{item.get('rate', 0.0):.2f}"
            amount_str = f"{item.get('amount', 0.0):.2f}"
        except Exception as e:
            print(f"Error processing item: {e}")
            continue # Skip to the next item

        # 2. Create the list of strings for the current row
        text_list = [
            item_name_str,
            qty_str,
            rate_str,
            amount_str
        ]
        
        # 3. CRITICAL FIX 2: Call software_columns for EACH ROW (text_list)
        try:
            d.software_columns(text_list, COLUMN_WIDTHS, COLUMN_ALIGNMENT)
        except Exception as e:
            # If printing fails mid-receipt, log the error but allow the function to finish
            print(f"Error printing item row: {e}")

    d.textln("-" * sum(COLUMN_WIDTHS)) # Print final separator line
    
    # The rest of the invoice content goes here...
    # Format the values (assuming doc.total, doc.total_taxes_and_charges, doc.grand_total are available)
    subtotal_str = f"{doc.total:.2f}"
    tax_str = f"{doc.total_taxes_and_charges:.2f}"
    grand_total_str = f"{doc.grand_total:.2f}"
    
    # Switch to Right Alignment
    d.set(align='right')
    
    # Print Subtotal
    # Format the entire line to span the TOTALS_WIDTH, with the label on the left and value on the right
    subtotal_line = f"SUBTOTAL: {subtotal_str}"
    d.textln(f"{subtotal_line:>{TOTAL_WIDTH}}")

    # Print Tax
    tax_line = f"TOTAL TAX: {tax_str}"
    d.textln(f"{tax_line:>{TOTAL_WIDTH}}")
    
    # Separator before Grand Total
    d.textln("=" * TOTAL_WIDTH) 

    # Print Grand Total
    d.set(bold=True) # Optional: Emphasize the grand total
    grand_total_line = f"GRAND TOTAL: {grand_total_str}"
    d.textln(f"{grand_total_line:>{TOTAL_WIDTH}}")
    d.set(bold=False)
    
    # CRITICAL: Reset alignment back to left for any subsequent text
    d.set(align='left')
    d.set(bold=True, align='center')
    d.ln(2)
    d.textln("THANK YOU FOR VISITING!")
    d.set(bold=False)
    d.ln(1)

    # CRITICAL: Reset alignment back to left for any subsequent text
    d.set(align='left')
    d.cut(mode='PART', feed=False)
    print("OUTPUT", d.output)
    p = Network(print_settings.server_ip, port=print_settings.port, profile='TM-T88III')
    p.hw('INIT')
    p._raw(d.output)
    p.close()
    # Placeholder for demonstration (remove in actual ESC/POS code)
    # The final print of text_list here only shows the LAST item's data, which is fine for debugging
    return "Success: Receipt printed via CUPS (BIN method)."

def print_kot_order(doc, print_settings):
    print("Printing KOT Order")
    # KOT printouts are typically narrow (e.g., 42 chars)
    TOTAL_WIDTH = 42

    # Column Structure: Qty (4) | Flag (3) | Item Name (35) -> Total 42
    # Flag: 'M' (Make/New) or 'C' (Cancel)
    COLUMN_WIDTHS = [30,6,6]
    COLUMN_ALIGNMENT = ['left', 'right', 'right']

    # Header for the KOT
    header_list = ["ITEMS","QTY","RATE"]

    d = Dummy()
    d.profile.profile_data["media"]["width"]["pixels"] = 576
    # ======================== HEADER SECTION ========================
    d.set(bold=True, align='center', double_height=True)
    d.textln("--- KITCHEN ORDER TICKET ---")
    d.set(double_height=False, bold=False)
    
    # Print the KOT ID, Date, and Time
    d.textln(f"KOT ID: {doc.name}")
    d.textln(f"DATE: {doc.get_formatted('date')} TIME: {doc.get_formatted('time')}")

    # Order Details
    if doc.customer_name:
        d.textln(f"Customer: {doc.customer_name}")
    if doc.restaurant_table:
        d.textln(f"Table: {doc.restaurant_table}")
    if doc.branch:
        d.textln(f"Branch: {doc.branch}")
    
    d.ln(1)
    
    # ======================== ITEMS SECTION ========================
    d.set(bold=True)
    d.textln("=" * TOTAL_WIDTH)
    
    # Print the Header Row
    try:
        d.software_columns(header_list, COLUMN_WIDTHS, COLUMN_ALIGNMENT)
    except Exception as e:
        print(f"Error printing header: {e}")
        return "Error: Failed to print header"

    d.textln("-" * TOTAL_WIDTH)
    d.set(bold=False)
    
    # Track if any items were printed
    
    # Get invoice items for rate information
    invoice_doc = frappe.get_doc("POS Invoice", doc.invoice)
    invoice_items = invoice_doc.items
    
    # Get KOT items for comment information
    kot_items = doc.kot_items
    
    # Create a mapping of KOT items by item_code for easy lookup
    kot_items_map = {}
    for kot_item in kot_items:
        kot_item_dict = kot_item.as_dict()
        kot_items_map[kot_item_dict.get('item', '')] = kot_item_dict

    for item in invoice_items:
        # 1. Extract and format the data for the columns
        item = item.as_dict()
        try:
            # Get the base item name
            item_name_str = item.get('item_name', '')[:COLUMN_WIDTHS[0]] 
            
            # Get comment from KOT items if available
            item_code = item.get('item_code', '')
            kot_item = kot_items_map.get(item_code, {})
            comment = kot_item.get('comments', '') or kot_item.get('comment', '')
            
            # Append comment to item name if it exists
            if comment:
                item_name_str = item_name_str + " (" + comment + ")"
            
            qty_str = str(int(item.get('qty', 0)))
            # Truncate item name to fit column width
            rate_str = f"{item.get('rate', 0.0):.2f}"
        except Exception as e:
            print(f"Error processing item: {e}")
            continue # Skip to the next item

        # 2. Create the list of strings for the current row
        text_list = [
            item_name_str,
            qty_str,
            rate_str,
        ]
        
        # 3. CRITICAL FIX 2: Call software_columns for EACH ROW (text_list)
        try:
            d.software_columns(text_list, COLUMN_WIDTHS, COLUMN_ALIGNMENT)
            items_printed = True
        except Exception as e:
            # If printing fails mid-receipt, log the error but allow the function to finish
            print(f"Error printing item row: {e}")
    # Print Each Item Row
    # for item in doc.kot_items:
    #     item = item.as_dict()
    #     item_name = item.get('item_name', '')
        
    #     # Determine quantities for 'Make' and 'Cancel'
    #     # 'quantity' from the doc is the NEW/MAKE quantity
    #     qty_make = float(item.get('quantity', 0) or 0)
    #     # 'cancelled_qty' is the CANCELLED quantity
    #     qty_cancel = float(item.get('cancelled_qty', 0) or 0)
        
    #     # --- Handle NEW/MAKE Items ---
    #     if qty_make > 0:
    #         items_printed = True
            
    #         # Format quantity and item string
    #         qty_str = str(int(qty_make))
    #         item_comment_str = item_name
    #         if item.get('comments'):
    #             item_comment_str += f" ({item['comments']})"
            
    #         text_list = [
    #             item_comment_str[:COLUMN_WIDTHS[0]], # Truncate to fit
    #             "M", # Flag for MAKE / NEW
    #             qty_str,
                
    #         ]
            
    #         # Print the MAKE item row (typically bold for attention)
    #         d.set(bold=True)
    #         d.software_columns(text_list, COLUMN_WIDTHS, COLUMN_ALIGNMENT)
    #         d.set(bold=False)

    # # --- Handle CANCELLED Items ---
    # if qty_cancel > 0:
    #     items_printed = True
            
    #     # Use negative sign or 'Cancelled' text for clarity
    #     qty_str = f"-{int(qty_cancel)}"
    #     item_comment_str = item_name
            
    #     text_list = [
    #         item_comment_str[:COLUMN_WIDTHS[2]], # Truncate to fit
    #         "C", # Flag for CANCEL
    #         qty_str,
    #     ]
            
    #     # Print the CANCEL item row (use underlining or italics if supported by printer profile)
    #     d.set(bold=True, underline=True)
    #     d.software_columns(text_list, COLUMN_WIDTHS, COLUMN_ALIGNMENT)
    #     d.set(bold=False, underline=False)

    # Final Separator
    d.textln("=" * TOTAL_WIDTH)
    
    # Print message if the KOT was empty (e.g., if neither quantity nor cancelled_qty was > 0 for any item)
    # if not items_printed:
    #     d.set(align='center', bold=True)
    #     d.textln("NO ITEMS TO PRINT ON THIS KOT")
    #     d.set(align='left', bold=False)

    d.ln(1)
    d.set(double_width=True, align='center')
    d.textln(f"ORDER NO: {doc.order_no}")
    d.set(double_width=False, align='left')
    # ======================== FOOTER & PRINTING ========================
    d.cut(mode='PART', feed=False)
    # Actual printing logic
    p = Network(print_settings.server_ip, port=print_settings.port, profile='TM-T88III')
    p.hw('INIT')
    p._raw(d.output)

    p.close()
    
    return "Success: KOT printed."

def print_receipt_with_columns(doc):
    """
    Revised print function using p.software_columns() for table sections.
    """
    print("doc", doc.as_dict())
    doc = doc.as_dict()
    company = frappe.get_doc("Company", doc['company'])
    # Helper for formatting with fallback for zero taxes
    def get_tax_label(total_taxes):
        return "0.00" if total_taxes == 0.0 else "N/A"

    # --- Setup (Same as before) ---
    p = Network('192.168.1.52', port=9100, profile="TM-T88III")
    p.hw('INIT')
    p.ln(2)

    # 1. Company Header
    p.set(align='center', custom_size=True, width=2, height=2, bold=True)
    p.textln(company.company_name_in_arabic.upper())
    p.ln(2)
    p.set(custom_size=False, width=1, height=1, bold=False, align='left')

    # 2. Header Info
    p.set(bold=True)
    p.text('VAT/Tax No: ')
    p.set(bold=False)
    p.textln(company.tax_id)

    p.set(bold=True)
    p.text('Date: ')
    p.set(bold=False)
    p.textln(doc['posting_date'])

    p.set(bold=True)
    p.text('Time: ')
    p.set(bold=False)
    p.textln(doc['posting_time'])

    # 3. QR Code (Skipping detail for brevity, assuming doc['custom_zatca_code'])
    if doc.get('custom_zatca_code'):
         p.ln()
         p.qr(doc['custom_zatca_code'], ec=QR_ECLEVEL_L, size=3, center=True)
         p.ln(2)
         p.set(align='left')

    # 4. Horizontal Rule
    p.textln("-" * 42)

    # 5. Table Header
    p.set(bold=True)
    # Define widths for header using the software_columns format
    header_list = ["QTY", "ITEM", "RATE", "TAX", "TOTAL"]
    widths = [3, 20, 6, 5, 8]
    aligns = ['right', 'left', 'right', 'right', 'right']

    p.software_columns(
        text_list=header_list,
        widths=widths,
        align=aligns
    )
    p.set(bold=False)
    p.textln("-" * 42)
    
    # ------------------------------------------------------------------
    ## 6. Table Items (Loop) using `software_columns` 📜
    # ------------------------------------------------------------------

    # Reusing widths and aligns from the header for the data rows
    
    for item in doc.items:
        item_list = [
            str(int(item['qty'])), # QTY (Right)
            item['item_name'][:20].strip(), # ITEM (Left)
            item.get_formatted("rate"), # RATE (Right)
            get_tax_label(doc.total_taxes_and_charges), # TAX (Right)
            item.get_formatted("amount") # TOTAL (Right)
        ]
        
        p.software_columns(
            text_list=item_list,
            widths=widths,
            align=aligns
        )

    p.textln("-" * 42)

    # ------------------------------------------------------------------
    ## 7. Main Totals using `software_columns` 💰
    # ------------------------------------------------------------------

    # Total columns: [Label, Value]
    total_widths = [30, 12] # Total width is 42
    total_aligns = ['left', 'right']

    # SUBTOTAL
    p.software_columns(
        text_list=["SUBTOTAL:", doc.get_formatted("base_total")],
        widths=total_widths,
        align=total_aligns
    )
    
    # TAXES
    p.software_columns(
        text_list=["TAXES:", doc.get_formatted("total_taxes_and_charges")],
        widths=total_widths,
        align=total_aligns
    )
    p.ln()

    # NET TOTAL (Double-height & double-width, Bold)
    p.set(custom_size=True, width=2, height=2, bold=True)

    # Adjust widths for double-size font (it roughly uses half the character space)
    final_widths = [15, 6] # Approximate new column widths
    
    p.software_columns(
        text_list=["NET TOTAL:", doc.get_formatted("grand_total")],
        widths=final_widths,
        align=total_aligns # Alignment remains the same
    )

    p.ln(2)

    # --- Footer (Same as before) ---
    p.set(custom_size=False, width=1, height=1, bold=False)
    p.textln("-" * 42)
    p.set(align='center')
    p.textln("Thank you for your business!")
    p.ln()
    p.textln("-" * 42)
    
    # 9. Cut
    p.cut(mode='PART', feed=False)
    p.close()
    return "Success: Receipt printed via CUPS (BIN method)."


@frappe.whitelist()
def sync_order_override(
    items,
    cashier,
    owner,
    mode_of_payment,
    customer,
    no_of_pax,
    last_invoice,
    waiter,
    pos_profile,
    last_modified_time=None,
    table=None,
    invoice=None,
    comments=None,
    order_type=None,
    aggregator_id=None,
    room=None,
):
    
    user_role = frappe.get_roles()
    posprofile = frappe.get_doc("POS Profile", pos_profile)
    
    billing_user = any(
        role.role in user_role for role in posprofile.role_allowed_for_billing
    )

    # Check if the last invoice was already billed
    if (
        last_invoice
        and frappe.db.get_value("POS Invoice", last_invoice, "invoice_printed") == 1
        and (not billing_user)
    ):
        frappe.msgprint(
            title="Invoice Already Billed",
            indicator="red",
            msg=("This order has already been billed. Please reload the page."),
        )
        return {"status": "Failure"}

    invoice = get_order_invoice(table, invoice,order_type)

    if last_invoice and last_modified_time:
        lastModifiedTime = invoice.modified
        from datetime import datetime

        if isinstance(last_modified_time, str):
            try:
                last_modified_time = datetime.strptime(
                    last_modified_time, "%Y-%m-%d %H:%M:%S.%f"
                )
            except ValueError:
                last_modified_time = datetime.strptime(
                    last_modified_time, "%Y-%m-%d %H:%M:%S"
                )
        if isinstance(lastModifiedTime, str):
            try:
                lastModifiedTime = datetime.strptime(
                    lastModifiedTime, "%Y-%m-%d %H:%M:%S.%f"
                )
            except ValueError:
                lastModifiedTime = datetime.strptime(
                    lastModifiedTime, "%Y-%m-%d %H:%M:%S"
                )
        if lastModifiedTime != last_modified_time:
            frappe.msgprint(
                title="Order has been modified",
                indicator="red",
                msg=(
                    "This order has been modified. Please reload the page to retrieve the latest edits."
                ),
            )
            return {"status": "Failure"}
    else:
        if invoice.name and invoice.invoice_printed == 0 and not billing_user:
            frappe.msgprint(
                title="Table occupied ",
                indicator="red",
                msg=("{0} is already occupied . Please refresh the page.").format(
                    table
                ),
            )
            return {"status": "Failure"}

    if not customer:
        frappe.throw("Please enter valid customer details")
    else:
        invoice.customer = customer

    if order_type:
        invoice.order_type = order_type

    customerdoc = frappe.get_doc("Customer", customer)
    invoice.mobile_number = customerdoc.mobile_number
    if comments:
        invoice.custom_comments = comments
    invoice.no_of_pax = no_of_pax
    invoice.pos_profile = pos_profile
    invoice.cashier = cashier
    invoice.waiter = waiter
    invoice.custom_aggregator_id = aggregator_id
    invoice.custom_restaurant_room =room
    invoice.restaurant_table = table
    
    if order_type == "Aggregators":
        price_list = frappe.db.get_value("Aggregator Settings",{"customer": customer, "parent": invoice.branch, "parenttype": "Branch"},"price_list",)
        
        if not price_list:
            frappe.throw(f"Price list for customer {customer} in branch {invoice.branch} not found in Aggregator Settings.")
    else:
        price_list = invoice.selling_price_list

    # dummy payment
    if invoice.invoice_created == 0:
        invoice.append(
            "payments",
            dict(mode_of_payment=mode_of_payment, amount=invoice.grand_total),
        )
        invoice.invoice_created = 1

    past_item = []
    for item in invoice.items:
        previous_item = {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.qty,
            "comments": "",
        }
        past_item.append(previous_item)
        

    # Conditional checking for 'items' type:
    # - 'ury': JSON passed, hence using isinstance
    # - 'ury_pos': Already formatted list, hence using else
    if isinstance(items, str):
        items = json.loads(items)
    invoice.items = []
    
    menu = frappe.db.get_value("URY Menu", {"branch": invoice.branch}, "name")
   
    for d in items:
        
        course = frappe.db.get_value("URY Menu Item", {"item": d.get("item"),"parent":menu}, "course")
        
        item_prices = frappe.db.get_list(
            "Item Price",
            filters={"item_code": d.get("item"), "price_list": price_list},
            fields=["price_list_rate"],
        )
        print(f"Item {d.get('item')} Prices: {item_prices}")

        if not item_prices:
            frappe.throw(_("No item price found for Item: {0} in Price List: {1}. Please check the price list settings.").format(item.item_code, price_list))

        else:
            invoice.append(
                "items",
                dict(
                    item_code=d.get("item"),
                    item_name=d.get("item_name"),
                    qty=d.get("qty"),
                    **({"custom_course": course} if course else {}),
                    comment=d.get("comment"),
                    rate = d.get("rate") if d.get("rate") else item_prices[0].price_list_rate,
                    price_list_rate = item_prices[0].price_list_rate,
                    base_price_list_rate = item_prices[0].price_list_rate,
                    cost_center = frappe.db.get_value(
                        "POS Profile", pos_profile, "cost_center"
                        ),
                ),
            )

    try:
        invoice.save()
    except Exception as e:
        frappe.throw(f"Error while updating order: {e}")   


    try:
        kot_execute(invoice.name, customer, table, items, past_item, comments)

    except Exception as e:
        # If an exception occurs (e.g., "kot" app not found), it will be caught here without affect the code execution.
        error_msg = f"KOT Creation Failes {str(e)}"            
        frappe.log_error(error_msg, "KOT Error")

    # table status
    if invoice.invoice_printed == 0:
        frappe.db.set_value(
            "URY Table", table, {"occupied": 1, "latest_invoice_time": invoice.creation}
        )

    invoice.db_set("owner", owner)
    return invoice.as_dict()

