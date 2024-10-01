# WifiScanner

## Descripción

**WifiScanner** es una herramienta simple y eficiente para escanear redes Wi-Fi disponibles en tu entorno utilizando Python. Esta aplicación permite obtener información detallada sobre las redes cercanas, como el nombre (SSID), la dirección MAC (BSSID), el canal, la intensidad de la señal, y más.

Este proyecto está diseñado tanto para propósitos educativos como prácticos, permitiendo a los usuarios analizar el entorno de redes inalámbricas y comprender mejor la disposición de las señales Wi-Fi en su área.

## Características

- Escaneo de redes Wi-Fi disponibles en tu área.
- Muestra información detallada sobre cada red, incluyendo:
  - Dispositivos conectados
  - IP
  - Dirección MAC de los dispositivos conectados
  - SSID (nombre de la red) *PROXIMAMENTE
  - BSSID (dirección MAC del punto de acceso) *PROXIMAMENTE
  - Intensidad de la señal *PROXIMAMENTE
  - Canal *PROXIMAMENTE
  - Seguridad (si está disponible) *PROXIMAMENTE
- Fácil de usar y personalizar.
- Basado en Python y de código abierto. 

## Requisitos Previos

Antes de ejecutar el proyecto, asegúrate de tener instalado lo siguiente:

- **Python 3.6**
- **Paquetes adicionales**: `scapy`, `subprocess`, y otros que el proyecto pueda requerir (ver `requirements.txt`).

Puedes instalar las dependencias ejecutando:

```bash
pip install scapy
