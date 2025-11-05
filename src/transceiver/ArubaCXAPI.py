import warnings

from .base import TransceiverBase
import pyaoscx.session
import requests.exceptions
from pyaoscx.exceptions.login_error import LoginError
from urllib3.exceptions import InsecureRequestWarning
from math import log10

warnings.simplefilter("ignore", InsecureRequestWarning)


# https://github.com/yadox666/dBm2mW/blob/master/dBm2mW.py
# Function to convert from mW to dBm
def mW2dBm(mW):
    if mW == 0:
        return 0
    return 10. * log10(mW)


# Function to convert from dBm to mW
def dBm2mW(dBm):
    return 10 ** ((dBm) / 10.)


class ArubaCXTransceiver(TransceiverBase):
    def __init__(self, gauges: dict, ip: str, username: str, password: str, name: str = None, version=None):
        self.gauges = gauges
        self.name = name
        response = requests.get('https://%s/rest' % ip, verify=False)
        if response.status_code != 200:
            return
        versions = response.json()
        self.aos_session = None
        for version in ['v10.09', 'v10.08', 'v10.04']:
            if version in versions:
                self.aos_session = pyaoscx.session.Session(ip, version[1:])
                break
        if self.aos_session is None:
            raise ValueError('Unable to find supported API version for %s' % name or ip)
        self.aos_session.open(username, password)

    def get_data(self):
        # system = self.aos_session.request('GET', 'system').json()
        interfaces = self.aos_session.request('GET', 'system/interfaces?attributes=l1_state,pm_info&depth=2').json()
        for interface_name, interface in interfaces.items():
            if 'pm_info' in interface and interface['pm_info'] and interface['pm_info']['dom_supported']:
                labels = {
                    'device_ip': self.aos_session.ip,
                    'device_name': self.name,
                    'transceiver_type': interface['pm_info']['vendor_part_number'] or interface['pm_info']['xcvr_desc'],
                    'interface': interface_name,
                }
                if 'tx_power' in interface['pm_info']:
                    self.gauges['TX_POWER'].labels(**labels).set(mW2dBm(interface['pm_info']['tx_power']))
                    self.gauges['RX_POWER'].labels(**labels).set(mW2dBm(interface['pm_info']['rx_power']))
                elif labels['transceiver_type'].find('SFP-DAC') == -1:
                    print('No TX power found for %s interface %s SFP type %s' % (
                        self.name, interface_name, labels['transceiver_type']))
                if 'temperature' in interface['pm_info']:
                    self.gauges['TEMPERATURE'].labels(**labels).set(interface['pm_info']['temperature'])
            # elif not interface['pm_info']['dom_supported']:
            #     print('DDM not supported for %s interface %s' % (self.name, interface_name))
