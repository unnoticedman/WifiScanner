# Importa las bibliotecas necesarias
import time
from scapy.all import *
from scapy.layers.l2 import ARP, Ether, srp

# Define una función para escanear la red WiFi y obtener información sobre los dispositivos conectados
def scan_wifi():
    # Imprime un mensaje indicando que se está escaneando la red WiFi
    print("Escanear dispositivos en la red WiFi...")
    
    # Obtiene la dirección IP local de la interfaz de red
    local_ip = get_if_addr(conf.iface)
    
    # Calcula la dirección IP de la red local
    network_ip = ".".join(local_ip.split(".")[:-1]) + ".0/24"
    
    # Crea un objeto ARP (Address Resolution Protocol) con la dirección IP de la red local
    arp = ARP(pdst=network_ip)
    
    # Crea un objeto Ether con una dirección MAC de difusión (ff:ff:ff:ff:ff:ff)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    
    # Combina el objeto ARP y el objeto Ether en un paquete
    packet = ether/arp
    
    # Envía el paquete y recibe las respuestas
    result = srp(packet, timeout=3, verbose=0)[0]
    
    # Inicializa una lista para almacenar la información de los dispositivos conectados
    devices = []
    
    # Itera a través de las respuestas recibidas
    for sent, received in result:
        # Agrega la dirección IP y la dirección MAC del dispositivo a la lista de dispositivos
        devices.append({'ip': received.psrc, 'mac': received.hwsrc})
    
    # Devuelve la lista de dispositivos
    return devices

# Define una función para imprimir la información de los dispositivos conectados
def print_devices(devices):
    # Imprime un encabezado con el título "Dispositivos conectados"
    print("\nDispositivos conectados:")
    
    # Imprime un encabezado con las columnas "IP" y "MAC"
    print("IP\t\t\tMAC")
    
    # Imprime una línea de separación
    print("-" * 40)
    
    # Itera a través de la lista de dispositivos
    for device in devices:
        # Imprime la dirección IP y la dirección MAC del dispositivo
        print(f"{device['ip']}\t\t{device['mac']}")

# Define la función principal del programa
def main():
    # Intenta ejecutar el código dentro del bloque try
    try:
        # Mientras sea verdadero (es decir, siempre)
        while True:
            # Obtiene la información de los dispositivos conectados
            devices = scan_wifi()
            
            # Imprime la información de los dispositivos conectados
            print_devices(devices)
            
            # Espera 5 segundos antes de escanear nuevamente
            time.sleep(5)
    # Si se produce una excepción KeyboardInterrupt (es decir, si el usuario presiona Ctrl+C para detener el programa)
    except KeyboardInterrupt:
        # Imprime un mensaje indicando que se está deteniendo el programa
        print("\nDeteniendo el programa...")

# Verifica si el archivo se está ejecutando como el programa principal (es decir, no se está importando como un módulo)
if __name__ == "__main__":
    # Ejecuta la función principal del programa
    main()