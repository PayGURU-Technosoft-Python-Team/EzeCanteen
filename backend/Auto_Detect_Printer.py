import socket
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_subnet():
    """Get current subnet automatically"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return '.'.join(ip.split('.')[:-1])
    except Exception as e:
        print(f"Error detecting subnet: {e}")
        return "192.168.1"  # Default fallback subnet

def check_printer(ip):
    """Check if IP is a printer by trying printer-specific ports"""
    try:
        # Only check printer-specific ports
        printer_ports = [9100, 515, 631]  # Raw, LPD, IPP
        for port in printer_ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            if sock.connect_ex((ip, port)) == 0:
                sock.close()
                print(f"✓ {ip} - Printer detected on port {port}")
                return ip
            sock.close()
    except Exception as e:
        print(f"Error checking {ip}: {str(e)}")
    return None

def scan(subnet=None):
    """Scan network for printers"""
    try:
        # Use provided subnet or auto-detect
        if not subnet:
            subnet = get_subnet()
        
        print(f"Scanning: {subnet}.0/24")
        print("This may take a few minutes...")
        
        # Generate IPs
        ips = [f"{subnet}.{i}" for i in range(1, 255)]
        found = []
        
        # Parallel scan with reduced workers to prevent overwhelming the network
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(check_printer, ip) for ip in ips]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    found.append(result)
        
        if found:
            print(f"\nFound {len(found)} printers:")
            for ip in found:
                print(f"- {ip}")
        else:
            print("\nNo printers found in the network.")
        
        return found
    except Exception as e:
        print(f"Error during scan: {str(e)}")
        return []

# Run with optional subnet argument
if __name__ == "__main__":
    try:
        subnet = sys.argv[1] if len(sys.argv) > 1 else None
        scan(subnet)
    except KeyboardInterrupt:
        print("\nScan interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
