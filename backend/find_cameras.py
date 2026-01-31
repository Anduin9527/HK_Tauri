import socket
import threading
import ipaddress
import netifaces
from queue import Queue

# Common RTSP Ports for Hikvision
TARGET_PORTS = [554, 8000]


def get_local_ip_and_subnet():
    """Find the likely local network interface (en0/wlan0)"""
    interfaces = netifaces.interfaces()
    for iface in interfaces:
        if iface == "lo":
            continue
        addrs = netifaces.ifaddresses(iface)
        if netifaces.AF_INET in addrs:
            for addr in addrs[netifaces.AF_INET]:
                ip = addr["addr"]
                if ip.startswith("127."):
                    continue
                if ip.startswith("169.254."):
                    continue
                mask = addr["netmask"]
                return ip, mask
    return None, None


def check_port(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    result = sock.connect_ex((ip, port))
    sock.close()
    return result == 0


def worker(queue, found_devices):
    while True:
        ip = queue.get()
        if ip is None:
            break

        # Check RTSP port
        if check_port(str(ip), 554):
            try:
                hostname = socket.gethostbyaddr(str(ip))[0]
            except:
                hostname = "Unknown"
            print(f"[FOUND] RTSP Device at {ip} ({hostname})")
            found_devices.append(str(ip))
        elif check_port(str(ip), 8000):  # Hikvision Service Port
            print(f"[FOUND] Hikvision Service at {ip}")
            found_devices.append(str(ip))

        queue.task_done()


def scan_network():
    print("Analyzing local network...")
    ip, mask = get_local_ip_and_subnet()
    if not ip:
        print("Could not determine local IP.")
        return

    print(f"Local IP: {ip}, Netmask: {mask}")
    network = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)

    print(f"Scanning {network.num_addresses} addresses for RTSP devices (Port 554)...")

    queue = Queue()
    found = []
    threads = []

    # Start threads
    for _ in range(50):
        t = threading.Thread(target=worker, args=(queue, found))
        t.start()
        threads.append(t)

    # Add jobs
    for ip in network.hosts():
        queue.put(ip)

    # Wait
    queue.join()

    # Stop threads
    for _ in range(50):
        queue.put(None)
    for t in threads:
        t.join()

    print("\nSearch Complete.")
    if found:
        print("Potentially compatible cameras found:")
        for device in set(found):
            print(f" - {device}")
            print(
                f"   Recommended URL: rtsp://admin:password@{device}:554/Streaming/Channels/101"
            )
    else:
        print(
            "No RTSP devices found. Ensure camera is powered on and connected to the same network."
        )


if __name__ == "__main__":
    scan_network()
