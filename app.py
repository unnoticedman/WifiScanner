import ctypes
import sys
import threading
import time
import webbrowser
from flask import Flask, render_template, jsonify, request

from scanner.wifi import scan_networks, get_channel_analysis, get_current_connection
from scanner.devices import scan_devices
from scanner.mac import get_mac_info, change_mac, restore_mac, generate_random_mac
from scanner import wlanapi

app = Flask(__name__)


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


@app.route('/')
def index():
    return render_template('index.html', admin=is_admin())


@app.route('/api/status')
def status():
    return jsonify({'admin': is_admin()})


@app.route('/api/connection')
def connection():
    try:
        return jsonify({'ok': True, 'data': get_current_connection()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/networks')
def networks():
    try:
        return jsonify({'ok': True, 'data': scan_networks()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/channels')
def channels():
    try:
        return jsonify({'ok': True, 'data': get_channel_analysis()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/devices')
def devices():
    try:
        return jsonify({'ok': True, 'data': scan_devices()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/mac')
def mac():
    try:
        return jsonify({'ok': True, 'data': get_mac_info()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/mac/randomize', methods=['POST'])
def mac_randomize():
    try:
        result = change_mac()
        return jsonify({'ok': True, 'data': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/mac/restore', methods=['POST'])
def mac_restore():
    try:
        result = restore_mac()
        return jsonify({'ok': True, 'data': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/mac/preview')
def mac_preview():
    return jsonify({'ok': True, 'data': {'mac': generate_random_mac()}})


@app.route('/api/debug')
def debug():
    import subprocess
    checks = {'admin': is_admin()}

    # netsh raw output
    r = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    checks['netsh_interfaces'] = {'rc': r.returncode, 'out': r.stdout[:1000]}

    r2 = subprocess.run(['netsh', 'wlan', 'show', 'networks', 'mode=bssid'],
                        capture_output=True, text=True, encoding='utf-8', errors='replace')
    checks['netsh_networks'] = {'rc': r2.returncode, 'out': r2.stdout[:1000]}

    # WlanAPI availability and struct sizes
    checks['wlanapi_available'] = wlanapi.is_available()
    if wlanapi.is_available():
        checks['wlanapi_struct_sizes'] = wlanapi.get_struct_sizes()
        try:
            results = wlanapi.scan()
            checks['wlanapi_scan_count'] = len(results)
            checks['wlanapi_first'] = results[0] if results else None
        except Exception as e:
            checks['wlanapi_scan_error'] = str(e)

    return jsonify(checks)


def _open_browser():
    time.sleep(1.2)
    webbrowser.open('http://localhost:5000')


if __name__ == '__main__':
    if not is_admin():
        print('\n[!] Algunas funciones requieren privilegios de Administrador.')
        print('    Para MAC spoofing, ejecuta como Administrador.\n')

    threading.Thread(target=_open_browser, daemon=True).start()
    app.run(host='127.0.0.1', port=5000, debug=False)
