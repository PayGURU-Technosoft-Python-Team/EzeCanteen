import socket

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
        print("Connected to printer")
        
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
    header = {'enable': True, 'text': "COMPANY NAME"}
    coupon_type = "LUNCH COUPON"
    user_id = "EMP001"
    user_name = ""
    punch_time = "2025-05-15 12:30:00"
    special_message = "Valid only for today"
    footer = {'enable': True, 'text': "Thank you!"}
    
    # Print the slip
    print_slip(
        printer_ip, 
        printer_port, 
        coupon_count, 
        header, 
        coupon_type, 
        user_id, 
        user_name, 
        punch_time, 
        special_message, 
        footer
    )