"""
Windows WLAN API scanner via ctypes.
Works correctly even when ejecutado como Administrador (a diferencia de netsh).
"""
import ctypes
import ctypes.wintypes as wt
import sys

if sys.platform != 'win32':
    _wlan = None
else:
    try:
        _wlan = ctypes.WinDLL('wlanapi')
    except OSError:
        _wlan = None

WLAN_MAX_NAME_LENGTH = 256
DOT11_SSID_MAX_LENGTH = 32
WLAN_MAX_PHY_TYPE_NUMBER = 8
DOT11_RATE_SET_MAX_LENGTH = 126
ERROR_SUCCESS = 0


# ── Structures ──────────────────────────────────────────────────────────────

class GUID(ctypes.Structure):
    _fields_ = [
        ('Data1', wt.DWORD),
        ('Data2', wt.WORD),
        ('Data3', wt.WORD),
        ('Data4', ctypes.c_ubyte * 8),
    ]


class DOT11_SSID(ctypes.Structure):
    _fields_ = [
        ('uSSIDLength', wt.DWORD),
        ('ucSSID', ctypes.c_ubyte * DOT11_SSID_MAX_LENGTH),
    ]

    def to_str(self):
        try:
            return bytes(self.ucSSID[:self.uSSIDLength]).decode('utf-8', errors='replace').strip('\x00')
        except Exception:
            return ''


class WLAN_INTERFACE_INFO(ctypes.Structure):
    _fields_ = [
        ('InterfaceGuid', GUID),
        ('strInterfaceDescription', ctypes.c_wchar * WLAN_MAX_NAME_LENGTH),
        ('isState', wt.DWORD),
    ]


class WLAN_INTERFACE_INFO_LIST(ctypes.Structure):
    _fields_ = [
        ('dwNumberOfItems', wt.DWORD),
        ('dwIndex', wt.DWORD),
        ('InterfaceInfo', WLAN_INTERFACE_INFO * 1),
    ]


class WLAN_AVAILABLE_NETWORK(ctypes.Structure):
    _fields_ = [
        ('strProfileName', ctypes.c_wchar * WLAN_MAX_NAME_LENGTH),
        ('dot11Ssid', DOT11_SSID),
        ('dot11BssType', wt.DWORD),
        ('uNumberOfBssidsFound', wt.DWORD),
        ('uNumberOfPhyTypesFound', wt.DWORD),
        ('dot11PhyTypes', wt.DWORD * WLAN_MAX_PHY_TYPE_NUMBER),
        ('bMorePhyTypesAvailable', wt.BOOL),
        ('wlanSignalQuality', wt.DWORD),
        ('bSecurityEnabled', wt.BOOL),
        ('dot11DefaultAuthAlgorithm', wt.DWORD),
        ('dot11DefaultCipherAlgorithm', wt.DWORD),
        ('dwFlags', wt.DWORD),
        ('dwReserved', wt.DWORD),
    ]


class WLAN_AVAILABLE_NETWORK_LIST(ctypes.Structure):
    _fields_ = [
        ('dwNumberOfItems', wt.DWORD),
        ('dwIndex', wt.DWORD),
        ('Network', WLAN_AVAILABLE_NETWORK * 1),
    ]


class WLAN_RATE_SET(ctypes.Structure):
    _fields_ = [
        ('uRateSetLength', wt.DWORD),
        ('usRateSet', wt.WORD * DOT11_RATE_SET_MAX_LENGTH),
    ]


# WLAN_BSS_ENTRY layout (ctypes adds natural alignment padding automatically):
#   offset  0: DOT11_SSID          (36)
#   offset 36: uPhyId DWORD        ( 4)
#   offset 40: dot11Bssid UCHAR[6] ( 6)
#   [+2 pad]
#   offset 48: dot11BssType DWORD  ( 4)
#   offset 52: dot11BssPhyType     ( 4)
#   offset 56: lRssi LONG          ( 4)
#   offset 60: uLinkQuality DWORD  ( 4)
#   offset 64: bInRegDomain BYTE   ( 1)
#   [+1 pad]
#   offset 66: usBeaconPeriod WORD ( 2)
#   [+4 pad – align UINT64 to 8]
#   offset 72: ullTimestamp        ( 8)
#   offset 80: ullHostTimestamp    ( 8)
#   offset 88: usCapabilityInfo    ( 2)
#   [+2 pad]
#   offset 92: uChCenterFrequency  ( 4)  ← channel from here
#   offset 96: wlanRateSet         (256)
#   offset352: ulIeOffset          ( 4)
#   offset356: ulIeSize            ( 4)
#   sizeof  = 360
class WLAN_BSS_ENTRY(ctypes.Structure):
    _fields_ = [
        ('dot11Ssid',              DOT11_SSID),
        ('uPhyId',                 wt.DWORD),
        ('dot11Bssid',             ctypes.c_ubyte * 6),
        ('dot11BssType',           wt.DWORD),         # +2 pad auto
        ('dot11BssPhyType',        wt.DWORD),
        ('lRssi',                  wt.LONG),
        ('uLinkQuality',           wt.DWORD),
        ('bInRegDomain',           ctypes.c_ubyte),
        ('usBeaconPeriod',         wt.WORD),           # +1 pad auto
        ('ullTimestamp',           ctypes.c_uint64),   # +4 pad auto (align to 8)
        ('ullHostTimestamp',       ctypes.c_uint64),
        ('usCapabilityInformation',wt.WORD),
        ('uChCenterFrequency',     wt.DWORD),          # +2 pad auto
        ('wlanRateSet',            WLAN_RATE_SET),
        ('ulIeOffset',             wt.DWORD),
        ('ulIeSize',               wt.DWORD),
    ]


class WLAN_BSS_LIST(ctypes.Structure):
    _fields_ = [
        ('dwTotalSize',      wt.DWORD),
        ('dwNumberOfItems',  wt.DWORD),
        ('wlanBssEntries',   WLAN_BSS_ENTRY * 1),
    ]


# ── Lookups ─────────────────────────────────────────────────────────────────

_AUTH = {
    1: 'Open',
    2: 'WEP-Shared',
    3: 'WPA-Enterprise',
    4: 'WPA-Personal',
    5: 'WPA-None',
    6: 'WPA2-Enterprise',
    7: 'WPA2-Personal',
    8: 'WPA3-Enterprise',
    9: 'WPA3-Personal',
}

_CIPHER = {
    0: 'None', 1: 'WEP-40', 2: 'TKIP', 4: 'WEP-104',
    5: 'BIP', 256: 'WEP', 258: 'WPA2', 259: 'CCMP', 260: 'GCMP',
}

_PHY = {
    4: '802.11a', 5: '802.11b', 6: '802.11g',
    7: '802.11n', 8: '802.11ac', 10: '802.11ax', 11: '802.11be',
}


def _sec_level(sec_enabled, auth, cipher):
    if not sec_enabled or auth == 1:
        return 'danger'
    if auth == 2 or cipher in (1, 4, 256):
        return 'warning'
    if auth in (3, 4):
        return 'moderate'
    if auth in (6, 7, 8, 9):
        return 'safe'
    return 'unknown'


def _freq_to_channel(freq_khz):
    mhz = freq_khz // 1000
    if 2412 <= mhz <= 2484:
        return 14 if mhz == 2484 else (mhz - 2412) // 5 + 1
    if 5160 <= mhz <= 5885:
        return (mhz - 5000) // 5
    if 5955 <= mhz <= 7115:   # 6 GHz band
        return (mhz - 5950) // 5 + 1
    return 0


def _mac_str(mac_bytes):
    return ':'.join(f'{b:02X}' for b in mac_bytes)


# ── Public API ───────────────────────────────────────────────────────────────

def is_available():
    return _wlan is not None


def scan():
    """Scan WiFi networks. Works as Administrator. Returns same format as wifi.scan_networks()."""
    if not _wlan:
        raise RuntimeError('wlanapi.dll no disponible en este sistema')

    h = wt.HANDLE()
    ver = wt.DWORD()
    ret = _wlan.WlanOpenHandle(2, None, ctypes.byref(ver), ctypes.byref(h))
    if ret != ERROR_SUCCESS:
        raise RuntimeError(f'WlanOpenHandle falló (código {ret})')
    try:
        return _do_scan(h)
    finally:
        _wlan.WlanCloseHandle(h, None)


def _do_scan(h):
    # Enumerate interfaces
    p_ifaces = ctypes.POINTER(WLAN_INTERFACE_INFO_LIST)()
    ret = _wlan.WlanEnumInterfaces(h, None, ctypes.byref(p_ifaces))
    if ret != ERROR_SUCCESS or not p_ifaces:
        raise RuntimeError(f'WlanEnumInterfaces falló (código {ret})')

    iface_list = p_ifaces.contents
    if iface_list.dwNumberOfItems == 0:
        _wlan.WlanFreeMemory(p_ifaces)
        raise RuntimeError('No se detectaron interfaces WiFi inalámbricas')

    # Copy GUID of first interface
    iface = WLAN_INTERFACE_INFO.from_address(ctypes.addressof(iface_list.InterfaceInfo))
    guid = GUID()
    ctypes.memmove(ctypes.byref(guid), ctypes.byref(iface.InterfaceGuid), ctypes.sizeof(GUID))
    _wlan.WlanFreeMemory(p_ifaces)

    # Get per-BSSID info (channel, RSSI, radio type)
    bss_map = _get_bss_map(h, guid)

    # Get per-SSID info (auth, security)
    return _get_networks(h, guid, bss_map)


def _get_bss_map(h, guid):
    """Returns {ssid: [{bssid, signal, channel, radio_type, band}]}"""
    p_bss = ctypes.POINTER(WLAN_BSS_LIST)()
    ret = _wlan.WlanGetNetworkBssList(
        h, ctypes.byref(guid), None, 3, False, None, ctypes.byref(p_bss)
    )
    if ret != ERROR_SUCCESS or not p_bss:
        return {}

    bss_list = p_bss.contents
    n = bss_list.dwNumberOfItems
    result = {}
    entry_base = ctypes.addressof(bss_list.wlanBssEntries)
    offset = 0

    for _ in range(n):
        try:
            entry = WLAN_BSS_ENTRY.from_address(entry_base + offset)
            ssid = entry.dot11Ssid.to_str()
            ch = _freq_to_channel(entry.uChCenterFrequency)
            result.setdefault(ssid, []).append({
                'bssid':      _mac_str(entry.dot11Bssid),
                'signal':     entry.uLinkQuality,
                'channel':    ch,
                'radio_type': _PHY.get(entry.dot11BssPhyType, ''),
                'band':       '5 GHz' if ch > 14 else '2.4 GHz',
            })
            # Each entry is followed by variable IE data; stride = ulIeOffset + ulIeSize
            stride = entry.ulIeOffset + entry.ulIeSize
            # Safety: never go backwards
            stride = max(stride, ctypes.sizeof(WLAN_BSS_ENTRY))
            offset += stride
        except Exception:
            break

    _wlan.WlanFreeMemory(p_bss)
    return result


def _get_networks(h, guid, bss_map):
    p_nets = ctypes.POINTER(WLAN_AVAILABLE_NETWORK_LIST)()
    ret = _wlan.WlanGetAvailableNetworkList(
        h, ctypes.byref(guid), 0, None, ctypes.byref(p_nets)
    )
    if ret != ERROR_SUCCESS or not p_nets:
        raise RuntimeError(f'WlanGetAvailableNetworkList falló (código {ret})')

    net_list = p_nets.contents
    n = net_list.dwNumberOfItems
    net_size = ctypes.sizeof(WLAN_AVAILABLE_NETWORK)
    base = ctypes.addressof(net_list.Network)

    networks = []
    seen = set()

    for i in range(n):
        net = WLAN_AVAILABLE_NETWORK.from_address(base + i * net_size)
        ssid = net.dot11Ssid.to_str() or '<Hidden>'
        auth = net.dot11DefaultAuthAlgorithm
        cipher = net.dot11DefaultCipherAlgorithm
        sec_enabled = bool(net.bSecurityEnabled)

        auth_str = _AUTH.get(auth, f'Auth-{auth}')
        cipher_str = _CIPHER.get(cipher, 'CCMP')
        sec = _sec_level(sec_enabled, auth, cipher)

        bss_entries = bss_map.get(ssid, [])
        if bss_entries:
            for bss in bss_entries:
                key = (ssid, bss['bssid'])
                if key not in seen:
                    seen.add(key)
                    networks.append({
                        'ssid':       ssid,
                        'bssid':      bss['bssid'],
                        'signal':     bss['signal'],
                        'channel':    bss['channel'],
                        'radio_type': bss['radio_type'],
                        'auth':       auth_str,
                        'encryption': cipher_str,
                        'security':   sec,
                        'band':       bss['band'],
                    })
        else:
            key = (ssid, '')
            if key not in seen:
                seen.add(key)
                networks.append({
                    'ssid':       ssid,
                    'bssid':      '',
                    'signal':     net.wlanSignalQuality,
                    'channel':    0,
                    'radio_type': '',
                    'auth':       auth_str,
                    'encryption': cipher_str,
                    'security':   sec,
                    'band':       '',
                })

    _wlan.WlanFreeMemory(p_nets)
    return sorted(networks, key=lambda x: x['signal'], reverse=True)


def get_struct_sizes():
    """Debug helper: returns ctypes sizeof values."""
    return {
        'WLAN_BSS_ENTRY': ctypes.sizeof(WLAN_BSS_ENTRY),
        'WLAN_AVAILABLE_NETWORK': ctypes.sizeof(WLAN_AVAILABLE_NETWORK),
        'DOT11_SSID': ctypes.sizeof(DOT11_SSID),
        'WLAN_RATE_SET': ctypes.sizeof(WLAN_RATE_SET),
        'expected_BSS_ENTRY': 360,
    }
