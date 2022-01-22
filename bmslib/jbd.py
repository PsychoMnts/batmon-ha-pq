"""

https://github.com/Bangybug/esp32xiaoxiangble/blob/master/src/main.cpp

"""
import asyncio
from typing import Dict

from .bms import BmsSample
from .bt import BtBms


def _jbd_command(command: int):
    return bytes([0xDD, 0xA5, command, 0x00, 0xFF, 0xFF - (command - 1), 0x77])


class JbdBt(BtBms):
    UUID_RX = '0000ff01-0000-1000-8000-00805f9b34fb'
    UUID_TX = '0000ff02-0000-1000-8000-00805f9b34fb'
    TIMEOUT = 8

    def __init__(self, address, **kwargs):
        super().__init__(address, **kwargs)
        self._buffer = bytearray()
        self._fetch_futures: Dict[int, asyncio.Future] = {}

    def _notification_handler(self, sender, data):

        print("bms msg {0}: {1}".format(sender, data))
        self._buffer += data

        if self._buffer.endswith(b'w'):
            command = self._buffer[1]
            buf = self._buffer[:]
            self._buffer.clear()

            print(command, 'buffer endswith w', self._buffer)

            fut = self._fetch_futures.pop(command, None)
            if fut:
                fut.set_result(buf)

    async def connect(self):
        await super().connect()
        await self.client.start_notify(self.UUID_RX, self._notification_handler)

    async def _q(self, cmd):
        assert cmd not in self._fetch_futures, "%s already waiting" % cmd
        self._fetch_futures[cmd] = asyncio.Future()
        await self.client.write_gatt_char(self.UUID_TX, data=_jbd_command(cmd))
        res = await asyncio.wait_for(self._fetch_futures[cmd], self.TIMEOUT)
        print('cmd', cmd, 'result', res)
        return res

    async def fetch(self) -> BmsSample:
        # binary reading
        #  https://github.com/NeariX67/SmartBMSUtility/blob/main/Smart%20BMS%20Utility/Smart%20BMS%20Utility/BMSData.swift

        buf = await self._q(cmd=0x03)
        buf = buf[4:]

        num_cell = int.from_bytes(buf[21:22], 'big')
        num_temp = int.from_bytes(buf[22:23], 'big')

        sample = BmsSample(
            voltage=int.from_bytes(buf[0:2], byteorder='big', signed=True) / 100.0,
            current=int.from_bytes(buf[2:4], byteorder='big', signed=True) / 100.0,

            charge=int.from_bytes(buf[4:6], byteorder='big', signed=True) / 100.,
            charge_full=int.from_bytes(buf[6:8], byteorder='big', signed=True) / 100,

            num_cycles=int.from_bytes(buf[8:10], byteorder='big', signed=True),

            temperatures=[(int.from_bytes(buf[23 + i * 2:i * 2 + 25], 'big') - 2731) / 10 for i in range(num_temp)],

            # charge_enabled
            # discharge_enabled
        )

        print(dict(num_cell=num_cell, num_temp=num_temp))

        # self.rawdat['P']=round(self.rawdat['Vbat']*self.rawdat['Ibat'], 1)
        # self.rawdat['Bal'] = int.from_bytes(self.response[12:14], byteorder='big', signed=False)

        product_date = int.from_bytes(buf[10:12], byteorder='big', signed=True)
        # productDate = convertByteToUInt16(data1: data[14], data2: data[15])

        return sample

    async def fetch_voltages(self):
        buf = await self._q(cmd=0x04)
        num_cell = int(buf[3] / 2)
        voltages = [(int.from_bytes(buf[4 + i * 2:i * 2 + 6], 'big')) for i in range(num_cell)]
        return voltages


async def main():
    mac_address = 'A3161184-6D54-4B9E-8849-E755F10CEE12'
    # mac_address = 'A4:C1:38:44:48:E7'
    # serial_service = '0000ff00-0000-1000-8000-00805f9b34fb'

    bms = JbdBt(mac_address)
    await bms.connect()
    voltages = await bms.get_voltages()
    print(voltages)
    # sample = await bms.fetch()
    # print(sample)
    await bms.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
