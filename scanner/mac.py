import subprocess
import re
import json
import random
import os
import datetime
import winreg

STATE_FILE = os.path.join(os.path.dirname(__file__), '..', '.mac_state.json')
ADAPTER_CLASS = r'SYSTEM\CurrentControlSet\Control\Class\{4D36E972-E325-11CE-BFC1-08002BE10318}'


def _ps(script):
    return subprocess.run(
        ['powershell', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', script],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )


def _load_state():
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def _get_wifi_adapter():
    script = (
        '$a = Get-NetAdapter | Where-Object {'
        '  $_.PhysicalMediaType -eq "Native 802.11" -or'
        '  $_.Name -like "*Wi-Fi*" -or $_.Name -like "*WiFi*" -or'
        '  $_.Name -like "*Wireless*" -or $_.Name -like "*WLAN*"'
        '} | Where-Object {$_.Status -ne "Not Present"} | Select-Object -First 1; '
        'if ($a) { $a | Select-Object Name, MacAddress, InterfaceDescription, Status,'
        '  @{N="InterfaceGuid";E={$_.InterfaceGuid.ToString()}} | ConvertTo-Json -Depth 2 }'
    )
    result = _ps(script)
    if result.returncode == 0 and result.stdout.strip():
        try:
            data = json.loads(result.stdout)
            if isinstance(data, list):
                data = data[0]
            return data
        except Exception:
            pass
    return None


def _find_registry_key_by_desc(adapter_desc):
    """Fallback: find registry key by driver description."""
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, ADAPTER_CLASS) as base:
            i = 0
            while True:
                try:
                    sub_name = winreg.EnumKey(base, i)
                    sub_path = f'{ADAPTER_CLASS}\\{sub_name}'
                    try:
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_path) as sub:
                            try:
                                val, _ = winreg.QueryValueEx(sub, 'DriverDesc')
                                if val.lower() == adapter_desc.lower():
                                    return sub_path
                            except FileNotFoundError:
                                pass
                    except Exception:
                        pass
                    i += 1
                except OSError:
                    break
    except Exception:
        pass
    return None


def _normalize_mac(mac):
    clean = re.sub(r'[^0-9a-fA-F]', '', mac)
    if len(clean) != 12:
        return None
    return ':'.join(clean[i:i+2].upper() for i in range(0, 12, 2))


def generate_random_mac():
    octets = [random.randint(0, 255) for _ in range(6)]
    # Locally administered, unicast
    octets[0] = (octets[0] & 0xFC) | 0x02
    return ':'.join(f'{b:02X}' for b in octets)


def _find_registry_key(interface_guid):
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, ADAPTER_CLASS) as base:
            i = 0
            while True:
                try:
                    sub_name = winreg.EnumKey(base, i)
                    sub_path = f'{ADAPTER_CLASS}\\{sub_name}'
                    try:
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_path) as sub:
                            try:
                                val, _ = winreg.QueryValueEx(sub, 'NetCfgInstanceId')
                                if val.strip('{}').lower() == interface_guid.strip('{}').lower():
                                    return sub_path
                            except FileNotFoundError:
                                pass
                    except Exception:
                        pass
                    i += 1
                except OSError:
                    break
    except Exception:
        pass
    return None


def _restart_adapter(adapter_name):
    _ps(
        f'Disable-NetAdapter -Name "{adapter_name}" -Confirm:$false; '
        f'Start-Sleep -Seconds 3; '
        f'Enable-NetAdapter -Name "{adapter_name}" -Confirm:$false'
    )


def _get_reg_path(interface_guid, adapter_desc=''):
    path = _find_registry_key(interface_guid)
    if not path and adapter_desc:
        path = _find_registry_key_by_desc(adapter_desc)
    return path


def _set_registry_mac(adapter_name, interface_guid, mac_no_sep, adapter_desc=''):
    reg_path = _get_reg_path(interface_guid, adapter_desc)
    if not reg_path:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, 'NetworkAddress', 0, winreg.REG_SZ, mac_no_sep)
        _restart_adapter(adapter_name)
        return True
    except Exception:
        return False


def _clear_registry_mac(adapter_name, interface_guid, adapter_desc=''):
    reg_path = _get_reg_path(interface_guid, adapter_desc)
    if not reg_path:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, 'NetworkAddress')
            except FileNotFoundError:
                pass
        _restart_adapter(adapter_name)
        return True
    except Exception:
        return False


def get_mac_info():
    adapter = _get_wifi_adapter()
    if not adapter:
        raise RuntimeError(
            'No se encontró adaptador WiFi. '
            'Verifica que el adaptador esté habilitado y ejecuta como Administrador.'
        )

    name = adapter.get('Name', '')
    desc = adapter.get('InterfaceDescription', '')
    current_raw = adapter.get('MacAddress', '')
    current = _normalize_mac(current_raw.replace('-', '')) if current_raw else ''

    # Try to get permanent MAC via hardware info
    perm_result = _ps(
        f'try {{ (Get-NetAdapterHardwareInfo -Name "{name}" -ErrorAction Stop).PermanentMacAddress }} '
        f'catch {{ "" }}'
    )
    permanent = ''
    if perm_result.returncode == 0:
        raw_perm = perm_result.stdout.strip()
        if raw_perm:
            permanent = _normalize_mac(raw_perm.replace('-', '').replace(':', ''))

    state = _load_state()
    original = state.get('original_mac', permanent or current)

    # Save original on first run
    if 'original_mac' not in state:
        state['original_mac'] = original
        state['adapter_name'] = name
        state['history'] = []
        _save_state(state)

    guid_raw = adapter.get('InterfaceGuid', '')
    guid = guid_raw.strip('{}') if guid_raw else ''

    return {
        'adapter_name': name,
        'adapter_desc': desc,
        'current_mac': current,
        'original_mac': original,
        'permanent_mac': permanent,
        'is_spoofed': bool(current and original and current != original),
        'interface_guid': guid,
        'status': adapter.get('Status', ''),
        'history': state.get('history', []),
        'change_count': len(state.get('history', [])),
    }


def change_mac(new_mac=None):
    info = get_mac_info()
    name = info['adapter_name']
    guid = info['interface_guid']
    desc = info['adapter_desc']

    if new_mac is None:
        new_mac = generate_random_mac()

    normalized = _normalize_mac(new_mac.replace('-', '').replace(':', ''))
    if not normalized:
        raise ValueError('MAC address inválida')

    # Try PowerShell Set-NetAdapter first
    win_fmt = normalized.replace(':', '-')
    ps_result = _ps(
        f'try {{ Set-NetAdapter -Name "{name}" -MacAddress "{win_fmt}" -Confirm:$false -ErrorAction Stop; "ok" }} '
        f'catch {{ $_.Exception.Message }}'
    )
    success = ps_result.returncode == 0 and 'ok' in ps_result.stdout

    if not success:
        # Fallback: registry + adapter restart (most reliable)
        mac_no_sep = normalized.replace(':', '')
        success = _set_registry_mac(name, guid, mac_no_sep, desc)

    if not success:
        raise RuntimeError(
            'No se pudo cambiar la MAC. '
            'Asegúrate de ejecutar como Administrador y que tu driver soporte cambio de MAC.'
        )

    # Persist state
    state = _load_state()
    if 'history' not in state:
        state['history'] = []
    state['history'].append({
        'mac': normalized,
        'timestamp': datetime.datetime.now().isoformat(timespec='seconds'),
    })
    state['adapter_name'] = name
    _save_state(state)

    return {'new_mac': normalized, 'adapter': name}


def restore_mac():
    info = get_mac_info()
    name = info['adapter_name']
    guid = info['interface_guid']
    desc = info['adapter_desc']
    original = info['original_mac']

    success = _clear_registry_mac(name, guid, desc)

    if not success:
        # Try setting it directly
        win_fmt = original.replace(':', '-')
        ps_result = _ps(
            f'try {{ Set-NetAdapter -Name "{name}" -MacAddress "{win_fmt}" -Confirm:$false -ErrorAction Stop; "ok" }} '
            f'catch {{ $_.Exception.Message }}'
        )
        success = ps_result.returncode == 0 and 'ok' in ps_result.stdout

    if not success:
        raise RuntimeError(
            'No se pudo restaurar la MAC. Ejecuta como Administrador.'
        )

    state = _load_state()
    state['history'] = []
    _save_state(state)

    return {'restored_mac': original, 'adapter': name}
