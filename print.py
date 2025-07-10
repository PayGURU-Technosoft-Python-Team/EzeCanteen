import socket
from datetime import datetime







def print_custom_slip(ip, port, header, cart_items, id, name, punchTime, specialMessage, footer):
    """
    Print a custom order slip to a thermal printer using socket communication

    Args:
        ip (str): Printer IP address
        port (int): Printer port number
        header (dict): Header with enable flag and text
        cart_items (dict): Dictionary of cart items {item_name: {quantity, price, total}}
        id (str): User ID
        name (str): User name
        punchTime (str): Date and time
        specialMessage (str): Special message to print (optional)
        footer (dict): Footer with enable flag and text
    """
    try:
        # Create a socket connection
        printer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        printer.connect((ip, port))

        # Define thermal printer commands
        INIT_PRINTER = b'\x1B\x40'
        CENTER_ALIGN = b'\x1B\x61\x01'
        LEFT_ALIGN = b'\x1B\x61\x00'
        RIGHT_ALIGN = b'\x1B\x61\x02'
        BOLD_ON = b'\x1B\x45\x01'
        BOLD_OFF = b'\x1B\x45\x00'
        DOUBLE_SIZE = b'\x1D\x21\x11'
        NORMAL_SIZE = b'\x1D\x21\x00'
        SMALL_FONT = b'\x1B\x4D\x01'
        NORMAL_FONT = b'\x1B\x4D\x00'
        UNDERLINE_ON = b'\x1B\x2D\x01'
        UNDERLINE_OFF = b'\x1B\x2D\x00'
        FEED_AND_CUT = b'\x1Bd\x02\x1Bd\x02\x1D\x56\x01'

        # Initialize printer
        printer.send(INIT_PRINTER)

        # Print header if enabled
        if header.get('enable', False):
            printer.send(CENTER_ALIGN)
            printer.send(BOLD_ON)
            printer.send(DOUBLE_SIZE)
            printer.send(f"{header['text']}\n".encode())
            printer.send(NORMAL_SIZE)
            printer.send(BOLD_OFF)
            printer.send(b"\n")

        # Print order title
        printer.send(CENTER_ALIGN)
        printer.send(BOLD_ON)
        printer.send(b"FOOD ORDER RECEIPT\n")
        printer.send(BOLD_OFF)
        printer.send(b"\n")

        # Print customer details
        printer.send(LEFT_ALIGN)
        printer.send(f"Customer: {name}\n".encode())
        printer.send(f"ID: {id}\n".encode())
        printer.send(f"Time: {punchTime}\n".encode())
        printer.send(b"\n")

        # Print separator line
        # printer.send(b"--------------------------------\n")

        # Print table header (centered)
        printer.send(CENTER_ALIGN)
        printer.send(BOLD_ON)
        printer.send(SMALL_FONT)

        header_text = f"{'ITEM':<16} {'QTY':>4} {'TOTAL':>8}"
        padding = (32 - len(header_text)) // 2
        printer.send((' ' * padding + header_text + '\n').encode())

        printer.send(BOLD_OFF)
        printer.send(b"--------------------------------\n")
        printer.send(NORMAL_FONT)

        grand_total = 0
        total_items = 0

        # Print each cart item (centered)
        for item_name, item_data in cart_items.items():
            quantity = item_data['quantity']
            total_price = item_data['total']
            grand_total += total_price
            total_items += quantity

            display_name = item_name[:16] if len(item_name) > 16 else item_name
            line_content = f"{display_name:<16} {quantity:>4} {total_price:>8.0f}"
            padding = (32 - len(line_content)) // 2
            printer.send((' ' * padding + line_content + '\n').encode())

        # Print separator
        printer.send(b"--------------------------------\n")

        # Print totals
        printer.send(BOLD_ON)

        total_line = f"{'TOTAL ITEMS:':<16} {total_items:>4}"
        padding = (32 - len(total_line)) // 2
        printer.send((' ' * padding + total_line + '\n').encode())

        grand_total_line = f"{'GRAND TOTAL:':<16} Rs.{grand_total:>6.0f}"
        padding = (32 - len(grand_total_line)) // 2
        printer.send((' ' * padding + grand_total_line + '\n').encode())

        printer.send(BOLD_OFF)
        printer.send(b"--------------------------------\n")
        printer.send(b"\n")

        # Print special message if provided
        if specialMessage and specialMessage.strip():
            printer.send(CENTER_ALIGN)
            printer.send(SMALL_FONT)
            printer.send(f"{specialMessage}\n".encode())
            printer.send(NORMAL_FONT)
            printer.send(b"\n")

        # Print order instructions
        printer.send(CENTER_ALIGN)
        printer.send(SMALL_FONT)
        printer.send(b"Please show this receipt\n")
        printer.send(b"when collecting your order\n")
        printer.send(NORMAL_FONT)
        printer.send(b"\n")

        # Print footer if enabled
        if footer.get('enable', False):
            printer.send(CENTER_ALIGN)
            printer.send(SMALL_FONT)
            printer.send(f"{footer['text']}\n".encode())
            printer.send(NORMAL_FONT)

        # Print timestamp
        printer.send(b"\n")
        printer.send(CENTER_ALIGN)
        printer.send(SMALL_FONT)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        printer.send(f"Printed: {current_time}\n".encode())
        printer.send(NORMAL_FONT)

        # Feed paper and cut
        printer.send(FEED_AND_CUT)

        # Close connection
        printer.close()
        print(f"Custom order receipt printed successfully for {name}")

    except Exception as e:
        print(f"Error printing custom slip: {e}")



def print_custom_slip_wide(ip, port, header, cart_items, id, name, punchTime, specialMessage, footer):
    """
    Print a custom order slip for wider thermal printers (48+ characters)
    
    Args:
        ip (str): Printer IP address
        port (int): Printer port number
        header (dict): Header with enable flag and text
        cart_items (dict): Dictionary of cart items {item_name: {quantity, price, total}}
        id (str): User ID
        name (str): User name
        punchTime (str): Date and time
        specialMessage (str): Special message to print (optional)
        footer (dict): Footer with enable flag and text
    """
    try:
        # Create a socket connection
        printer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        printer.connect((ip, port))
        
        # Define thermal printer commands
        INIT_PRINTER = b'\x1B\x40'
        CENTER_ALIGN = b'\x1B\x61\x01'
        LEFT_ALIGN = b'\x1B\x61\x00'
        RIGHT_ALIGN = b'\x1B\x61\x02'
        BOLD_ON = b'\x1B\x45\x01'
        BOLD_OFF = b'\x1B\x45\x00'
        DOUBLE_SIZE = b'\x1D\x21\x11'
        NORMAL_SIZE = b'\x1D\x21\x00'
        SMALL_FONT = b'\x1B\x4D\x01'
        NORMAL_FONT = b'\x1B\x4D\x00'
        FEED_AND_CUT = b'\x1Bd\x02\x1Bd\x02\x1D\x56\x01'

        # Initialize printer
        printer.send(INIT_PRINTER)
        
        # Print header if enabled
        if header.get('enable', False):
            printer.send(CENTER_ALIGN)
            printer.send(BOLD_ON)
            printer.send(DOUBLE_SIZE)
            printer.send(f"{header['text']}\n".encode())
            printer.send(NORMAL_SIZE)
            printer.send(BOLD_OFF)
            printer.send(b"\n")
        
        # Print order title
        printer.send(CENTER_ALIGN)
        printer.send(BOLD_ON)
        printer.send(b"FOOD ORDER RECEIPT\n")
        printer.send(BOLD_OFF)
        printer.send(b"\n")
        
        # Print customer details
        printer.send(LEFT_ALIGN)
        printer.send(f"Customer: {name:<20} ID: {id}\n".encode())
        printer.send(f"Date & Time: {punchTime}\n".encode())
        printer.send(b"\n")
        
        # Print separator line (48 characters wide)
        printer.send(b"================================================\n")
        
        # Print table header
        printer.send(BOLD_ON)
        header_line = f"{'ITEM':<25} {'QTY':>6} {'PRICE':>7} {'TOTAL':>8}\n"
        printer.send(header_line.encode())
        printer.send(BOLD_OFF)
        printer.send(b"================================================\n")
        
        # Calculate totals
        grand_total = 0
        total_items = 0
        
        # Print each cart item
        for item_name, item_data in cart_items.items():
            quantity = item_data['quantity']
            price = item_data['price']
            total_price = item_data['total']
            grand_total += total_price
            total_items += quantity
            
            # Truncate item name if too long
            display_name = item_name[:25] if len(item_name) > 25 else item_name
            
            # Format the line with proper spacing
            line = f"{display_name:<25} {quantity:>6} {price:>7.0f} {total_price:>8.0f}\n"
            printer.send(line.encode())
            printer.send((line + " ").encode())

        # Print separator
        printer.send(b"================================================\n")
        
        # Print totals
        printer.send(BOLD_ON)
        total_items_line = f"{'TOTAL ITEMS:':<32} {total_items:>6}\n"
        printer.send(total_items_line.encode())
        
        grand_total_line = f"{'GRAND TOTAL:':<32} Rs.{grand_total:>6.0f}\n"
        printer.send(grand_total_line.encode())
        printer.send(BOLD_OFF)
        
        printer.send(b"================================================\n")
        printer.send(b"\n")
        
        # Print special message if provided
        if specialMessage and specialMessage.strip():
            printer.send(CENTER_ALIGN)
            printer.send(f"{specialMessage}\n".encode())
            printer.send(b"\n")
        
        # Print order instructions
        printer.send(CENTER_ALIGN)
        printer.send(b"Please show this receipt when collecting your order\n")
        printer.send(b"\n")
        
        # Print footer if enabled
        if footer.get('enable', False):
            printer.send(CENTER_ALIGN)
            printer.send(f"{footer['text']}\n".encode())
        
        # Print timestamp
        printer.send(b"\n")
        printer.send(CENTER_ALIGN)
        printer.send(SMALL_FONT)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        printer.send(f"Printed: {current_time}\n".encode())
        printer.send(NORMAL_FONT)
        
        # Feed paper and cut
        printer.send(FEED_AND_CUT)
        
        # Close connection
        printer.close()
        print(f"Wide custom order receipt printed successfully for {name}")
        
    except Exception as e:
        print(f"Error printing wide custom slip: {e}")





def print_slip(ip, port, CouponCount, header, CouponType, id, name, punchTime, specialMessage, footer):
    """
    Print a slip to a thermal printer using socket communication
    
    Args:
        ip (str): Printer IP address
        port (int): Printer port number
        CouponCount (int): Token number
        header (dict): Header with enable flag and text
        CouponType (str): Type of coupon
        id (str): User ID
        name (str): User name
        punchTime (str): Date and time
        specialMessage (str): Special message to print (optional)
        footer (dict): Footer with enable flag and text
    """
    try:
        # Create a socket connection
        printer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        printer.connect((ip, port))
        # print("Connected to printer")
        
        # Define commands
        INIT_PRINTER = b'\x1B\x40'  # Initialize printer
        CENTER_ALIGN = b'\x1B\x61\x01'  # Center alignment
        LEFT_ALIGN = b'\x1B\x61\x00'  # Left alignment
        BOLD_ON = b'\x1B\x45\x01'  # Bold on
        BOLD_OFF = b'\x1B\x45\x00'  # Bold off
        DOUBLE_SIZE = b'\x1D\x21\x11'  # Double width, double height
        NORMAL_SIZE = b'\x1D\x21\x00'  # Normal size
        FEED_AND_CUT = b'\x1Bd\x02\x1Bd\x02\x1D\x56\x01'  # Feed paper and cut
        
        # Initialize printer and set center alignment
        printer.send(INIT_PRINTER)
        printer.send(CENTER_ALIGN)
        
        # Print token number if provided - bold
        if CouponCount != 0:
            printer.send(BOLD_ON)
            printer.send(f"Token No: {CouponCount}\n".encode())
            printer.send(BOLD_OFF)
        
        # Print header if enabled - bold
        if header.get('enable', False):
            printer.send(BOLD_ON)
            printer.send(f"{header['text']}\n".encode())
            printer.send(BOLD_OFF)
        
        # Print coupon type with double size font
        printer.send(b"\n")
        printer.send(DOUBLE_SIZE)
        printer.send(f"{CouponType}\n".encode())
        printer.send(NORMAL_SIZE)
        printer.send(b"\n")
        
        # Print user details - centered
        printer.send(f"User: {id}, {name}\n".encode())
        printer.send(f"Date Time: {punchTime}\n".encode())
        
        # Print special message if provided
        if specialMessage.strip() != "":
            printer.send(b"\n")
            printer.send(f"{specialMessage}\n".encode())
        
        # Print footer
        printer.send(b"\n")
        
        if footer.get('enable', False):
            printer.send(f"{footer['text']}\n".encode())
        
        # Feed paper and cut
        printer.send(FEED_AND_CUT)
        
        # Close connection
        printer.close()
        
    except Exception as e:
        print(f"Error printing SLIP: {e}")

# Example usage:
if __name__ == "__main__":
    # Define parameters
    printer_ip = "192.168.0.251"  # Replace with your printer's IP
    printer_port = 9100  # Common port for printer communication
    
    # Example data
    coupon_count = 42
    header = {'enable': False, 'text': "COMPANY NAME"}
    coupon_type = "LUNCH COUPON"
    user_id = "EMP001"
    user_name = ""
    punch_time = "2025-05-15 12:30:00"
    special_message = "Valid only for today"
    footer = {'enable': True, 'text': "Thank you!"}
    
    # Print the slip
    # print_slip(
    #     printer_ip, 
    #     printer_port, 
    #     coupon_count, 
    #     header, 
    #     coupon_type, 
    #     user_id, 
    #     user_name, 
    #     punch_time, 
    #     special_message, 
    #     footer
    # )







    printer_ip = "192.168.0.251"
    printer_port = 9100
    
    header = {'enable': True, 'text': "EzeeCanteen"}
    
    # Sample cart items
    cart_items = {
        "Vegetable Curry": {
            "quantity": 2,
            "price": 45.0,
            "total": 90.0
        },
        "Basmati Rice": {
            "quantity": 1,
            "price": 25.0,
            "total": 25.0
        },
        "Fresh Roti": {
            "quantity": 3,
            "price": 8.0,
            "total": 24.0
        },
        "Masala Chai": {
            "quantity": 1,
            "price": 15.0,
            "total": 15.0
        }
    }
    
    user_id = "EMP001"
    user_name = "John Doe"
    punch_time = "2025-01-15 14:30:00"
    special_message = "Fresh and hot food!"
    footer = {'enable': True, 'text': "Thank you for your order!"}
    
    
    print("\nTesting wide printer...")
    try:
        print_custom_slip(
            printer_ip,
            printer_port,
            header,
            cart_items,
            user_id,
            user_name,
            punch_time,
            special_message,
            footer
        )
    except Exception as e:
        print(f"Wide print test failed: {e}")
