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
        HEAD_FOOT_SIZE = b''  # Set increased font size (you need to define this)
        BOLD_FONT_SIZE = b''  # Bold font size command (you need to define this)
        FONT_SIZE = b''  # Font size command (you need to define this)
        FEED_AND_CUT = b'\x1Bd\x02\x1Bd\x02\x1D\x56\x01'  # Feed paper and cut
        
        # Initialize printer
        printer.send(INIT_PRINTER)
        printer.send(HEAD_FOOT_SIZE)
        
        # Print token number if provided
        if CouponCount != 0:
            printer.send(f"Token No: {CouponCount}\n".encode())
        
        # Print header if enabled
        if header.get('enable', False):
            printer.send(f"{header['text']}\n".encode())
        
        # Print coupon type with bold font
        printer.send(BOLD_FONT_SIZE)
        printer.send(f"\n{CouponType}\n\n".encode())
        
        # Print user details
        printer.send(FONT_SIZE)
        printer.send(f"     User: {id}, {name}\n".encode())
        printer.send(f"     Date Time: {punchTime}\n".encode())
        
        # Print special message if provided
        if specialMessage.strip() != "":
            printer.send(b"\n")
            printer.send(HEAD_FOOT_SIZE)
            printer.send(f"{specialMessage}\n".encode())
        
        # Print footer
        printer.send(b"\n")
        printer.send(HEAD_FOOT_SIZE)
        
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
    user_name = "John Doe"
    punch_time = "2025-05-15 12:30:00"
    special_message = "Valid only for today"
    footer = {'enable': True, 'text': "Thank you!"}
    
    # Define printer commands according to your printer's specifications
    # These will vary depending on your printer model
    HEAD_FOOT_SIZE = b'\x1D\x21\x11'  # Example: double width, double height
    BOLD_FONT_SIZE = b'\x1B\x45\x01'  # Example: bold on
    FONT_SIZE = b'\x1B\x45\x00'  # Example: bold off
    
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