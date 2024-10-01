import time
from scapy.all import *
from scapy.layers.l2 import ARP, Ether, srp

def scan_wifi():
    print("Escanear dispositivos en la red WiFi...")
    local_ip = get_if_addr(conf.iface)
    network_ip = ".".join(local_ip.split(".")[:-1]) + ".0/24"
    arp = ARP(pdst=network_ip)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether/arp
    result = srp(packet, timeout=3, verbose=0)[0]
    
    devices = []
    for sent, received in result:
        devices.append({'ip': received.psrc, 'mac': received.hwsrc})
    
    return devices

def print_devices(devices):
    print("\nDispositivos conectados:")
    print("IP\t\t\tMAC")
    print("-" * 40)
    for device in devices:
        print(f"{device['ip']}\t\t{device['mac']}")

def main():
    try:
        while True:
            devices = scan_wifi()
            print_devices(devices)
            time.sleep(5)  # Espera 5 segundos antes de escanear nuevamente
    except KeyboardInterrupt:
        print("\nDeteniendo el programa...")

if __name__ == "__main__":
    main()