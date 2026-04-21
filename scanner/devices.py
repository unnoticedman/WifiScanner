import subprocess
import re
import socket
import concurrent.futures


def _run(cmd):
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding='utf-8', errors='replace'
    )


def _parse_arp(output):
    devices = []
    current_iface_ip = None

    for line in output.split('\n'):
        line = line.strip()
        # Interface header: "Interface: 192.168.1.100 --- 0x10"
        m = re.match(r'Interface[^:]*:\s*([\d.]+)', line, re.I)
        if m:
            current_iface_ip = m.group(1)
            continue

        # ARP entry: "192.168.1.1    aa-bb-cc-dd-ee-ff    dynamic"
        m = re.match(r'([\d.]+)\s+([\w-]{17})\s+(\w+)', line)
        if m:
            ip, mac, type_ = m.groups()
            if mac.lower() == 'ff-ff-ff-ff-ff-ff':
                continue
            devices.append({
                'ip': ip,
                'mac': mac.replace('-', ':').upper(),
                'type': type_,
                'gateway': False,
            })

    return devices


def _resolve_hostname(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return None


def _get_gateway():
    result = _run(['ipconfig'])
    for line in result.stdout.split('\n'):
        m = re.search(r'Default Gateway[^:]*:\s*([\d.]+)', line, re.I)
        if m:
            return m.group(1)
    return None


def scan_devices():
    result = _run(['arp', '-a'])
    devices = _parse_arp(result.stdout)

    gateway = _get_gateway()

    # Resolve hostnames in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(_resolve_hostname, d['ip']): d for d in devices}
        for fut, device in futures.items():
            try:
                hostname = fut.result(timeout=2)
                device['hostname'] = hostname or ''
            except Exception:
                device['hostname'] = ''

    for d in devices:
        if gateway and d['ip'] == gateway:
            d['gateway'] = True
            d['hostname'] = d['hostname'] or 'Gateway/Router'

    return sorted(devices, key=lambda x: list(map(int, x['ip'].split('.'))))
