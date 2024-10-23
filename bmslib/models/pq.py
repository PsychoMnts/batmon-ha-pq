import json
import asyncio
import logging
from request import Request
from bmslib.bms import BmsSample
from bmslib.bt import BtBms

class PowerQueenBt(BtBms):
    BMS_CHARACTERISTIC_ID = '0000FFE1-0000-1000-8000-00805F9B34FB'  # Bluetooth characteristic for BMS data
    pq_commands = {
        'GET_VERSION': bytes.fromhex('00 00 04 01 16 55 AA 1A'),
        'GET_BATTERY_INFO': bytes.fromhex('00 00 04 01 13 55 AA 17'),
    }

    def __init__(self, address, **kwargs):
        super().__init__(address, **kwargs)
        self.packVoltage = None
        self.voltage = None
        self.batteryPack = {}
        self.current = None
        self.remianAh = None
        self.factoryAh = None
        self.cellTemperature = None
        self.mosfetTemperature = None
        self.SOC = None
        self.SOH = None
        self.dischargesCount = None
        self.dischargesAHCount = None
        self._buffer = bytearray()

    def _notification_handler(self, sender, data):
        self._buffer += data
        if self._buffer.endswith(b'w'):
            self._buffer.clear()

    async def connect(self, **kwargs):
        await super().connect(**kwargs)
        await self.client.start_notify(self.BMS_CHARACTERISTIC_ID, self._notification_handler)

    async def fetch(self) -> BmsSample:
        data = await self.client.read_gatt_char(self.BMS_CHARACTERISTIC_ID)
        self.parse_battery_info(data)
        return BmsSample(voltage=self.voltage, current=self.current, charge=self.remianAh, capacity=self.factoryAh, soc=self.SOC)

    def parse_battery_info(self, data):
        self.packVoltage = int.from_bytes(data[8:12][::-1], byteorder='big')
        self.voltage = int.from_bytes(data[12:16][::-1], byteorder='big')
        batPack = data[16:48]
        cell = 1
        for key, dt in enumerate(batPack):
            if not dt or key % 2:
                continue
            cellVoltage = int.from_bytes([batPack[key + 1], dt], byteorder='big')
            self.batteryPack[cell] = cellVoltage / 1000
            cell += 1
        self.current = int.from_bytes(data[48:52][::-1], byteorder='big')
        self.remianAh = round(int.from_bytes(data[62:64][::-1], byteorder='big') / 100, 2)
        self.factoryAh = round(int.from_bytes(data[64:66][::-1], byteorder='big') / 100, 2)
        self.cellTemperature = int.from_bytes(data[52:54][::-1], byteorder='big')
        self.mosfetTemperature = int.from_bytes(data[54:56][::-1], byteorder='big')
        self.SOC = f"{int.from_bytes(data[90:92][::-1], byteorder='big')}%"
        self.SOH = f"{int.from_bytes(data[92:96][::-1], byteorder='big')}%"
        self.dischargesCount = int.from_bytes(data[96:100][::-1], byteorder='big')
        self.dischargesAHCount = int.from_bytes(data[100:104][::-1], byteorder='big')

async def main():
    mac_address = 'A4:C1:38:44:48:E7'
    bms = PowerQueenBt(mac_address)
    await bms.connect()
    sample = await bms.fetch()
    print(sample)
    await bms.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
