import warnings

from .base import TransceiverBase
import requests.exceptions
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
    scheme = 'https'
    version = None

    def _build_uri(self, resource_path):
        """
        Build a URI representing a resource.

        :param resource_path: Resource path before adding version prefix.
        :return: String of the uri
        """
        if self.version:
            complete_path = '/rest/' + self.version + '/' + resource_path
        else:
            complete_path = resource_path
        uri = requests.utils.urlunparse(
            (self.scheme, self.ip, complete_path, "", "", "")
        )
        return uri

    def __init__(self, gauges: dict, ip: str, username: str, password: str, name: str = None, version=None):
        self.gauges = gauges
        self.ip = ip
        self.name = name
        self.session = requests.Session()
        self.session.verify = False
        response = self.session.get(self._build_uri('rest'))
        if response.status_code != 200:
            return
        versions = response.json()

        for version in ['v10.16', 'v10.13', 'v10.09', 'v10.08', 'v10.04']:
            if version in versions:
                self.version = version
                break
        if self.version is None:
            raise ValueError('Unable to find supported API version for %s' % name or ip)
        response_login = self.session.post(self._build_uri('login'),
                                           data={'username': username, 'password': password})
        response_login.raise_for_status()

    def get_data(self):
        # system = self.aos_session.request('GET', 'system').json()
        interfaces = self.session.get(
            self._build_uri('system/interfaces?attributes=l1_state,pm_info,pm_monitor,pm_state&depth=2')).json()
        for interface_name, interface in interfaces.items():
            if 'pm_info' in interface and interface['pm_info'] and interface['pm_info']['dom_supported']:
                labels = {
                    'device_ip': self.aos_session.ip,
                    'device_name': self.name,
                    'transceiver_type': interface['pm_info']['vendor_part_number'] or interface['pm_info']['xcvr_desc'],
                    'interface': interface_name,
                }
                if 'tx_power' in interface['pm_info']:
                    self.gauges['TX_POWER'].labels(**labels).set(mW2dBm(interface['pm_info'].get('tx_power', 0)))
                    self.gauges['RX_POWER'].labels(**labels).set(mW2dBm(interface['pm_info'].get('rx_power', 0)))
                elif labels['transceiver_type'].find('SFP-DAC') == -1:
                    print('No TX power found for %s interface %s SFP type %s' % (
                        self.name, interface_name, labels['transceiver_type']))
                if 'temperature' in interface['pm_info']:
                    self.gauges['TEMPERATURE'].labels(**labels).set(interface['pm_info']['temperature'])
            # elif not interface['pm_info']['dom_supported']:
            #     print('DDM not supported for %s interface %s' % (self.name, interface_name))
