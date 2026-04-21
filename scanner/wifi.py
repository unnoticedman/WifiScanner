import subprocess
import re
from scanner import wlanapi


def _run(cmd):
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding='utf-8', errors='replace'
    )


# ── netsh parsing (fallback when not Admin or wlanapi fails) ─────────────────

def _parse_netsh_networks(output):
    networks = []
    current_net = None
    current_bssid = None

    for raw in output.split('\n'):
        line = raw.strip()
        if not line:
            continue

        m = re.match(r'^SSID\s+\d+\s*:\s*(.*)$', line, re.I)
        if m:
            current_net = {'ssid': m.group(1).strip() or '<Hidden>', 'auth': '', 'encryption': '', 'bssids': []}
            current_bssid = None
            networks.append(current_net)
            continue

        if current_net is None:
            continue

        m = re.match(r'^BSSID\s+\d+\s*:\s*(.+)$', line, re.I)
        if m:
            current_bssid = {'mac': m.group(1).strip(), 'signal': 0, 'channel': 0, 'radio_type': ''}
            current_net['bssids'].append(current_bssid)
            continue

        if re.search(r'Authentication|Autenticaci', line, re.I):
            current_net['auth'] = line.split(':', 1)[-1].strip()
        elif re.search(r'Encryption|Cifrado', line, re.I):
            current_net['encryption'] = line.split(':', 1)[-1].strip()

        if current_bssid is not None:
            if '%' in line:
                m = re.search(r'(\d+)%', line)
                if m:
                    current_bssid['signal'] = int(m.group(1))
            elif re.search(r'Radio\s+type|Tipo\s+de\s+radio', line, re.I):
                current_bssid['radio_type'] = line.split(':', 1)[-1].strip()
            elif re.search(r'^Channel\b|^Canal\b', line, re.I):
                m = re.search(r':\s*(\d+)', line)
                if m:
                    current_bssid['channel'] = int(m.group(1))

    return networks


def _security_level(auth, enc):
    a, e = auth.lower(), enc.lower()
    if not a or 'open' in a or a in ('none', 'abierta'):
        return 'danger'
    if 'wep' in a or 'wep' in e:
        return 'warning'
    if 'wpa3' in a:
        return 'safe'
    if 'wpa2' in a:
        return 'safe'
    if 'wpa' in a:
        return 'moderate'
    return 'unknown'


def _scan_netsh():
    result = _run(['netsh', 'wlan', 'show', 'networks', 'mode=bssid'])
    output = (result.stdout or '').strip()
    if not output:
        return []
    parsed = _parse_netsh_networks(output)
    flat = []
    for net in parsed:
        for b in net['bssids']:
            ch = b['channel']
            flat.append({
                'ssid':       net['ssid'],
                'bssid':      b['mac'],
                'signal':     b['signal'],
                'channel':    ch,
                'radio_type': b['radio_type'],
                'auth':       net['auth'],
                'encryption': net['encryption'],
                'security':   _security_level(net['auth'], net['encryption']),
                'band':       '5 GHz' if ch > 14 else '2.4 GHz',
            })
    return sorted(flat, key=lambda x: x['signal'], reverse=True)


# ── Public API ───────────────────────────────────────────────────────────────

def scan_networks():
    """Try WlanAPI first (works as admin), fall back to netsh."""
    last_error = None

    if wlanapi.is_available():
        try:
            results = wlanapi.scan()
            if results:
                return results
            # WlanAPI returned 0 networks — fall through to netsh
        except Exception as e:
            last_error = str(e)

    # Fallback: netsh
    try:
        results = _scan_netsh()
        if results:
            return results
    except Exception as e:
        last_error = str(e)

    if last_error:
        raise RuntimeError(
            f'No se encontraron redes WiFi. '
            f'Verifica que el adaptador esté activo y conectado. ({last_error})'
        )
    return []


def get_channel_analysis():
    networks = scan_networks()
    counts = {}
    for n in networks:
        ch = n['channel']
        if ch > 0:
            counts[ch] = counts.get(ch, 0) + 1

    preferred_24 = [1, 6, 11]
    preferred_5  = [36, 40, 44, 48, 149, 153, 157, 161]

    def best_in(candidates):
        return min(candidates, key=lambda c: counts.get(c, 0))

    return {
        'distribution':  counts,
        'most_congested': max(counts, key=counts.get) if counts else None,
        'best_24ghz':    best_in(preferred_24),
        'best_5ghz':     best_in(preferred_5),
        'total_networks': len(networks),
    }


_IFACE_PATTERNS = [
    ('ssid',       r'^\s*SSID\s*(?!.*BSSID)\s*:\s*(.+)'),
    ('bssid',      r'^\s*BSSID\s*:\s*(.+)'),
    ('signal',     r'^\s*(?:Signal|Se.al)\s*:\s*(\d+)%'),
    ('channel',    r'^\s*(?:Channel|Canal)\s*:\s*(\d+)'),
    ('radio_type', r'^\s*(?:Radio type|Tipo de radio)\s*:\s*(.+)'),
    ('auth',       r'^\s*(?:Authentication|Autenticaci\w+)\s*:\s*(.+)'),
    ('state',      r'^\s*(?:State|Estado)\s*:\s*(.+)'),
    ('rx_rate',    r'^\s*(?:Receive rate|Tasa de recepci\w+)\s*[^:]*:\s*(.+)'),
    ('tx_rate',    r'^\s*(?:Transmit rate|Tasa de transmisi\w+)\s*[^:]*:\s*(.+)'),
]


def get_current_connection():
    result = _run(['netsh', 'wlan', 'show', 'interfaces'])
    info = {}
    for line in result.stdout.split('\n'):
        for key, pattern in _IFACE_PATTERNS:
            if key in info:
                continue
            m = re.match(pattern, line, re.I)
            if m:
                info[key] = m.group(1).strip()
    return info
