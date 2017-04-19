from .api import LiveDNSApi, Record, RecordType
import asyncio
import pprint
import os.path
import sys
from uuid import UUID

# Currently contains some examples of ways to work with the LiveDNS API

async def print_zones(api: LiveDNSApi):
    zones = await api.get_zones()
    pprint.pprint(zones)
    records = await zones[0].get_records()
    text_records = await zones[0].as_text()
    pprint.pprint(records)

    print(text_records)
    return zones


async def add_caa_records(api, zone: UUID):
    zone = await api.get_zone(zone)
    print("Before changes")
    pprint.pprint(await zone.get_records())
    rec = await zone.add_record(Record('@', ttl=10800, rec_type=RecordType.CAA, values=['0 issue "letsencrypt.org"', '0 iodef "hostmaster@{domain}"'.format(domain=zone.name)]), replace=True)
    print(rec)
    print("After changes")
    pprint.pprint(await zone.get_records())

async def update_fastmail_records(api, zone: UUID, domain=None):
    zone = await api.get_zone(zone)
    if domain is None:
        domain = zone.name
    print(f"Updating fastmail records for {domain}")
    print("Before changes")
    snap_id = await zone.create_snapshot()
    print("Created snapshot: {id}".format(id=snap_id))
    pprint.pprint(await zone.get_records())
    new_records = await zone.update_records([
            Record(name='@', rec_type=RecordType.MX, ttl=10800, values={'10 in1-smtp.messagingengine.com.', '20 in2-smtp.messagingengine.com.'}),
            Record(name='*', rec_type=RecordType.MX, ttl=10800, values={'10 in1-smtp.messagingengine.com.', '20 in2-smtp.messagingengine.com.'}),
            Record(name='mail', rec_type=RecordType.MX, ttl=10800, values={'10 in1-smtp.messagingengine.com.', '20 in2-smtp.messagingengine.com.'}),
            Record(name='mail', rec_type=RecordType.CNAME, ttl=10800, values={'www.fastmail.com.'}),
            Record(name="_caldavs._tcp", rec_type=RecordType.SRV, ttl=10800, values={'0 1 443 caldav.messagingengine.com'}),
            Record(name="_carddavs._tcp", rec_type=RecordType.SRV, ttl=10800, values={'0 1 443 carddav.messagingengine.com'}),
            Record(name="_client._tcp", rec_type=RecordType.SRV, ttl=10800, values={'0 1 1 @'}),
            Record(name="_imaps._tcp", rec_type=RecordType.SRV, ttl=10800, values={'0 1 993 mail.messagingengine.com'}),
            Record(name="_pop3s._tcp", rec_type=RecordType.SRV, ttl=10800, values={'0 1 995 mail.messagingengine.com'}),
            Record(name="_submission._tcp", rec_type=RecordType.SRV, ttl=10800, values={'0 1 587 mail.messagingengine.com'}),
            Record(name="_caldav._tcp", rec_type=RecordType.SRV, ttl=10800, values={'0 1 0 .'}),
            Record(name="_carddav._tcp", rec_type=RecordType.SRV, ttl=10800, values={'0 1 0 .'}),
            Record(name="_imap._tcp", rec_type=RecordType.SRV, ttl=10800, values={'0 1 0 .'}),
            Record(name="_pop3._tcp", rec_type=RecordType.SRV, ttl=10800, values={'0 1 0 .'}),
            Record(name="fm1._domainkey", rec_type=RecordType.CNAME, ttl=10800, values={'fm1.{domain}.dkim.fmhosted.com.'.format(domain=domain)}),
            Record(name="fm2._domainkey", rec_type=RecordType.CNAME, ttl=10800, values={'fm2.{domain}.dkim.fmhosted.com.'.format(domain=domain)}),
            Record(name="fm3._domainkey", rec_type=RecordType.CNAME, ttl=10800, values={'fm3.{domain}.dkim.fmhosted.com.'.format(domain=domain)}),
        ], delete_if_necessary=set([
            ('mesmtp._domainkey', RecordType.TXT)
            ]))
    #print("New records would be:")
    #pprint.pprint(new_records)
    print("After changes")
    pprint.pprint(await zone.get_records())

async def import_zone(api, zone_name: str, zone_path: str):
    if not os.path.isfile(zone_path):
        print(f"Invalid file {zone_path}")

    zone = None
    for test in await api.get_zones():
        if test.name == zone_name:
            zone = test
            break
    if zone == None:
        zone = await api.create_zone(zone_name)

    with open(zone_path, 'rt') as f:
        contents = "\n".join(f.readlines()).replace(".leaping.ninja.", "").replace("leaping.ninja.", "@")
        await zone.set_records(contents)

def main():
    api = LiveDNSApi(api_key=sys.argv[0])
    loop = asyncio.get_event_loop()
    loop.run_until_complete(print_zones(api))
    loop.close()
