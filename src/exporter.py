import json
import os
import time
from pathlib import Path

import requests
from prometheus_client import generate_latest, Summary, Gauge, CollectorRegistry, REGISTRY
from prometheus_client import start_http_server, Summary
from requests.exceptions import RequestException

import transceiver


class Exporter:
    gauges = {}

    def __init__(self):
        prefix = 'transceiver_'
        labels = {'device_ip': 'Device IP', 'device_name': 'Device name',
                  # 'device_type': 'Device type',
                  'transceiver_type': 'Transceiver type', 'interface': 'Interface', }

        self.gauges['RX_POWER'] = Gauge(prefix + 'rx_power', 'Transceiver Rx Power', labels, registry=REGISTRY)
        self.gauges['TX_POWER'] = Gauge(prefix + 'tx_power', 'Transceiver Tx Power', labels, registry=REGISTRY)
        self.gauges['TEMPERATURE'] = Gauge(prefix + 'temperature', 'Transceiver Temperature', labels, registry=REGISTRY)


if __name__ == '__main__':
    # Start up the server to expose the metrics.
    start_http_server(8000)
    response = requests.get(os.getenv('SWITCHINFO_URL'))
    response.raise_for_status()
    exporter = Exporter()
    devices = []
    login_file = Path(os.environ.get('LOGIN_FILE', 'logins.json'))
    if login_file.exists():
        with open(login_file) as fp:
            logins = json.load(fp)
    else:
        logins = {}

    for switch in response.json():
        print(switch['name'])
        if switch['type'] == 'Aruba CX':
            try:
                if switch['name'] not in logins:
                    device = transceiver.ArubaCXTransceiver(exporter.gauges, switch['ip'], os.getenv('USER_NAME'),
                                                            os.getenv('PASSWORD'),
                                                            switch['name'], switch['software'])
                else:
                    print(f'Login override {switch["name"]}')
                    username, password = logins.get(switch['name'], [None, None])
                    device = transceiver.ArubaCXTransceiver(exporter.gauges, switch['ip'], username,
                                                            password, switch['name'], switch['software'])
                device.get_data()
                devices.append(device)
            except ValueError as e:
                print(e)
                continue
            except RequestException as e:
                print(e)
                continue

    while True:
        for device in devices:
            try:
                device.get_data()
            except Exception:
                continue
        time.sleep(60 * 5)
