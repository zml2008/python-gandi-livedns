import asyncio
import re
import socket
from typing import Optional
from .api import LiveDNSApi, RecordType, Record

async def read_string(host, port):
    reader, writer = await asyncio.open_connection(host, port,
                                                        loop=asyncio.get_event_loop())

    data = await reader.readline()

    writer.close()
    return data.decode()


PATT_IP_RESPONSE = re.compile(r'Your public address appears to be ([a-zA-z0-9.:]+)\n')
class DynDNSUpdater:
    def __init__(self, cache: str, api_key: str):
        self.__cache = cache
        self.__api = LiveDNSApi(api_key)

    def get_internal_ip(self):
        interfaces = socket.if_nameindex()  
        # TODO: How do I do this?
        pass

    async def get_external_ipv4(self) -> Optional[str]:
        try:
            line = await read_string('ipv4.test-ipv6.com', 79)
            match = PATT_IP_RESPONSE.match(line)
            if match:
                return match.group(1)
        except:
            pass
        return None

    async def get_external_ipv6(self) -> Optional[str]:
        try:
            line = await read_string('ipv6.test-ivp6.com', 79)
            match = PATT_IP_RESPONSE.match(line)
            if match:
                return match.group(1)
        except:
            pass
        return None

    async def update_record(self, zone: UUID, record: str, ttl: int = 15 * 60) -> bool:
        """
        Update the `record` in the given `zone` with this machine's current IP address
        The default `ttl` is 15 minutes
        """
        ipv4 = await self.get_external_ipv4()
        ipv6 = await self.get_external_ipv6()

        records_add = []
        if ipv4:
            records_add.append(Record(name=record, rec_type=RecordType.A, ttl=ttl, values={ipv4}))
        if ipv6:
            records_add.append(Record(name=record, rec_type=RecordType.AAA, ttl=ttl, values={ipv6}))
        if records_add:
            zone_obj = await self.__api.get_zone(zone)
            await zone_obj.update_records(records_add, {})

async def print_ips(fetcher):
    ipv4 = await fetcher.get_external_ipv4()
    ipv6 = await fetcher.get_external_ipv6()
    print(f"IPv4: {ipv4}")
    print(f"IPv6: {ipv6}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    fetcher = IPFetcher(None, None)
    loop.run_until_complete(print_ips(fetcher))
    loop.close()

