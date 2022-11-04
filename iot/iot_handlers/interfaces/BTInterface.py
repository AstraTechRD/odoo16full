from gatt import DeviceManager as Gatt_DeviceManager
import logging
from threading import Thread

from odoo.addons.hw_drivers.interface import Interface
from odoo.addons.hw_drivers.main import iot_devices

bt_devices = {}

_logger = logging.getLogger(__name__)

class GattBtManager(Gatt_DeviceManager):
    def device_discovered(self, device):
        identifier = "bt_%s" % device.mac_address
        if identifier not in bt_devices:
            device.manager = self
            bt_devices[identifier] = device

class BtManager(Thread):
    def run(self):
        dm = GattBtManager(adapter_name='hci0')
        for device in [device_con for device_con in dm.devices() if device_con.is_connected()]:
            device.disconnect()
        dm.start_discovery()
        dm.run()

class BTInterface(Interface):
    connection_type = 'bluetooth'

    def get_devices(self):
        return bt_devices.copy()

bm = BtManager()
bm.daemon = True
bm.start()
