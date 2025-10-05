import frappe
# Import the original URYKOT class from the 'ury' app
from ury.ury.doctype.ury_kot.ury_kot import URYKOT

from ury_companion_ssw.ury_companion_ssw.overrides.api import network_printing_override

class CustomURYKOT(URYKOT):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_submit(self):
        print("on_submit")
        self.multi_print_kot()
        super().kotDisplayRealtime()

    def multi_print_kot(self):
        # Function for printing a KOT on a specified printer using a print format.
        def print_kot(printer, kot_print_format):
            try: 
                network_printing_override(self.doctype, self.name, printer, kot_print_format)
            except:
                pass

        
        pos_kot_printers = frappe.db.get_all(
            "URY Printer Settings",
            fields=["printer", "custom_kot_print_format","custom_kot_print"], 
            filters={"parent": self.pos_profile, "custom_kot_print": 1,"parenttype":"POS Profile"},
            order_by="idx"
        )
    
        pos_print_flag = True
        if self.production:
            production_unit_printers = frappe.get_all(
                "URY Printer Settings",
                fields=["printer", "custom_kot_print_format","custom_kot_print","custom_block_takeaway_kot"], 
                filters={"parent": self.production, "custom_kot_print": 1,"parenttype":"URY Production Unit"},
                order_by="idx"
            )

            # If production unit printer is specified, print KOT in production printer
            if production_unit_printers:
                for printer in production_unit_printers:
                    pos_print_flag = False
                    if printer.custom_block_takeaway_kot == 1 :
                        if self.restaurant_table and self.table_takeaway == 0:
                            print_kot(printer.printer, printer.custom_kot_print_format)
                    else:
                        print_kot(printer.printer, printer.custom_kot_print_format)

                # Check if restaurant table is specified and it's not a takeaway order
                if self.restaurant_table and self.table_takeaway == 0:
                    room = frappe.db.get_value(
                        "URY Table", self.restaurant_table, "restaurant_room"
                    )

                    room_kot_printers = frappe.get_all(
                        "URY Printer Settings",
                        fields=["printer", "custom_kot_print_format","custom_kot_print"],
                        filters={"parent": room, "custom_kot_print": 1,"parenttype":"URY Room"},
                        order_by="idx"
                    )
                    
                    # If room printer is specified, print KOT in room
                    if room_kot_printers:
                        for printer in room_kot_printers:
                            pos_print_flag = False
                            print_kot(printer.printer, printer.custom_kot_print_format)

                    if pos_print_flag == True:
                        if pos_kot_printers:
                            for printer in pos_kot_printers:
                                print_kot(printer.printer, printer.custom_kot_print_format)

                else:
                    if pos_kot_printers:
                        for printer in pos_kot_printers:
                            print_kot(printer.printer, printer.custom_kot_print_format)

