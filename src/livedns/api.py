import requests
import enum
from typing import NamedTuple, List, Set, Tuple, overload
from uuid import UUID

class RecordType(enum.Enum):
    """
    One of several possible types of records
    """
    A = enum.auto()
    AAAA = enum.auto()
    CAA = enum.auto()
    CDS = enum.auto()
    CNAME = enum.auto()
    DNAME = enum.auto()
    DS = enum.auto()
    LOC = enum.auto()
    MX = enum.auto()
    NS = enum.auto()
    PTR = enum.auto()
    SPF = enum.auto()
    SRV = enum.auto()
    SSHFP = enum.auto()
    TLSA = enum.auto()
    TXT = enum.auto()
    WKS = enum.auto()

class _Record(NamedTuple):
    name: str
    ttl: int
    #rec_class: str = 'IN'
    rec_type: RecordType
    values: Set[str]

class Record(_Record):
    @classmethod
    def from_json(cls, json: dict):
        return cls(name=json['rrset_name'], ttl=json['rrset_ttl'], rec_type=RecordType[json['rrset_type']], values=set(json['rrset_values']))

    def to_json(self):
        return {"rrset_name": self.name,
                  "rrset_type": self.rec_type.name,
                  "rrset_ttl": self.ttl,
                  "rrset_values": list(self.values)}

class Domain(NamedTuple):
    fqdn: str
    zone: str


class Snapshot(NamedTuple):
    date_created: str
    uuid: UUID
    zone_uuid: UUID
    zone_data: List[Record]

class _Zone(NamedTuple):
    email: str
    expire: int
    minimum: int
    name: str
    primary_ns: str
    refresh: int
    retry: int
    serial: int
    sharing_id: UUID
    uuid: UUID

class Zone(_Zone):
    """
    A DNS Zone in Gandi's LiveDNS. WARNING: Every function in this class is destructive. USE WITH CAUTION, MAKE SNAPSHOTS AND BACKUPS
    """

    @staticmethod
    def create(api, *args, **kwargs):
        if 'uuid' in kwargs and not isinstance(kwargs['uuid'], UUID):
            kwargs['uuid'] = UUID(kwargs['uuid'])
        if 'sharing_id' in kwargs and not isinstance(kwargs['sharing_id'], UUID):
            kwargs['sharing_id'] = UUID(kwargs['sharing_id'])
        inst = Zone(*args, **kwargs)
        inst.__api = api
        return inst

    async def get_domains(self) -> List[str]:
        """
        Get a list of all domains currently using this zone
        """
        resp = await self.__api._create_request('GET', 'zones/{uuid}/domains')
        data = resp.json()
        return [dom['fqdn'] for dom in data]

    async def add_domain(self, domain: str):
        """
        Attach this zone to the given `domain`
        """
        resp = await self.__api._create_request('POST', 'domains', json={'fqdn': domain,
            'zone_uuid': str(self.uuid)
            })
        data = resp.json()
        return data

    async def get_records(self) -> List[Record]:
        """
        Get the records associated with the zone of the given UUID
        """
        result = await self.__api._create_request('GET', 'zones/{uuid}/records'.format(uuid=self.uuid))
        data = result.json()
        try:
            return [Record.from_json(r) for r in data]
        except KeyError as e:
            raise LiveDNSException("Could not find expected key '{}' in record JSON!".format(e.args))

    async def add_record(self, record: Record, replace: bool = False):
        if replace:
                result = await self.__api._create_request('PUT', 'zones/{uuid}/records/{name}/{type}'.format(uuid=self.uuid, name=record.name, type=record.rec_type.name), json={'rrset_ttl': record.ttl, 'rrset_values': record.values})
        else:
            result = await self.__api._create_request('POST', 'zones/{uuid}/records'.format(uuid=self.uuid), json=record.to_json())
        return result.json()

    async def remove_record(self, record: Record):
        ret = await self.remove_record(record.name, record.rec_type)
        return ret.json()

    async def remove_record(self, name: str, rec_type: RecordType = None):
        """
        Remove all records of the given name and type from this zone. If the type is not specified, will remove all records with the provided name regardless of type
        """
        if rec_type is not None:
            endpoint = 'zones/{uuid}/records/{name}/{rec_type}'.format(uuid=self.uuid, name=name, rec_type=rec_type)
        else:
            endpoint = 'zones/{uuid}/records/{name}'.format(uuid=self.uuid, name=name)
        result = await self.__api._create_request('DELETE', endpoint)
        return result.json()

    async def remove_all_records(self):
        """
        Remove all records from this zone.
        """
        result = await self.__api._create_request('DELETE', 'zones/{uuid}/records'.format(uuid=self.uuid))
        return result.json()

    @overload
    async def set_records(self, records: List[Record]):
        pass

    @overload
    async def set_records(self, records: str):
        pass

    async def set_records(self, records):
        if isinstance(records, str): # text format records
            try:
                result = await self.__api._create_request('PUT', 'zones/{uuid}/records'.format(uuid=self.uuid), extra_headers={'Content-Type': 'text/plain'}, data=records.encode())
            except requests.HTTPError as e:
                ret = e.response.json()
                import pprint
                pprint.pprint(ret)
                return ret
        else:
            result = await self.__api._create_request('PUT', 'zones/{uuid}/records'.format(uuid=self.uuid), json={'items': [r.to_json() for r in records]})
        return result.json()
        

    async def update_records(self, add_if_necessary: List[Record], delete_if_necessary: Set[Tuple[str, RecordType]]):
        """
        Update the records in this zone to match the provided specifications, adding or updating records in the `add_if_necessary` list, and deleting records from the `delete_if_necessary` list.
        """
        new_records = await self.get_updated_records(add_if_necessary, delete_if_necessary)
        return await self.set_records(new_records)

    async def get_updated_records(self, add_if_necessary: List[Record], delete_if_necessary: Set[Tuple[str, RecordType]]) -> List[Record]:
        """
        Returns what the new value of records will be after performing the record update based on the given parameters
        """
        records = await self.get_records()
        new_records = []
        add_copied=dict([((r.name, r.rec_type), r) for r in add_if_necessary])
        for rec in records:
            rec_key = (rec.name, rec.rec_type)
            if rec_key in delete_if_necessary or (rec.name, None) in delete_if_necessary:
                continue
            if rec_key not in add_copied:
                new_records.append(rec)
        new_records.extend(add_if_necessary)

        return new_records


    async def as_text(self) -> str:
        req = await self.__api._create_request('GET', 'zones/{uuid}/records'.format(uuid=self.uuid), extra_headers={'Accept': 'text/plain'})
        return req.content.decode('utf-8')

    async def create_snapshot(self) -> UUID:
        req = await self.__api._create_request('POST', 'zones/{uuid}/snapshots'.format(uuid=self.uuid))
        data = req.json()
        if 'uuid' not in data:
            raise LiveDNSException("UUID was not provided in response data!")
        return UUID(data['uuid'])

    async def list_snapshots(self) -> List[Tuple[UUID, str]]:
        req = await self.__api._create_request('GET', 'zones/{uuid}/snapshots'.format(uuid=self.uuid))
        return [(UUID(s["uuid"]), s["date_created"]) for s in req.json()]

    async def get_snapshot(self, snap_uuid: UUID) -> Snapshot:
        req = await self.__api._create_request('GET', 'zones/{uuid}/snapshots/{snap_uuid}'.format(uuid=self.uuid, snap_uuid=snap_uuid))
        data = req.json()
        data["zone_data"] = [Record.from_json(r) for r in data["zone_data"]]
        return Snapshot(**data)

    async def restore_to_snapshot(self, snapshot: Snapshot):
        return await self.set_records(snapshot.zone_data)


class LiveDNSException(Exception):
    def __init__(self, message):
        super().__init__(message)

class LiveDNSApi:
    DEFAULT_API_HOST="https://dns.beta.gandi.net/api/v5"

    def __init__(self, api_key: str, api_host: str=DEFAULT_API_HOST):
        self.__api_key = api_key
        self.__api_host = api_host

    async def _create_request(self, method, endpoint, extra_headers={}, **kwargs):
        """
        Create a request with the given method and endpoint. Any additional keyword args will be passed to the request method.
        """
        headers = {
                'X-Api-Key': self.__api_key,
                'Content-Type': 'application/json'
                }
        headers.update(extra_headers)
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]

        url = "{root}/{endpoint}".format(root=self.__api_host, endpoint=endpoint)
        ret = requests.request(method, url, headers=headers, **kwargs)
        ret.raise_for_status()
        return ret

    async def get_zones(self) -> List[Zone]:
        result = await self._create_request('GET', 'zones')
        return [Zone.create(self, **z) for z in result.json()]

    async def get_zone(self, uid: UUID) -> Zone:
        result = await self._create_request('GET', 'zones/{uid}'.format(uid=uid))
        return Zone.create(self, **result.json())

    async def create_zone(self, name) -> Zone:
        """
        Creates a zone with the given name and returns the UUID
        """
        result = await self._create_request('POST', 'zones', json={'name': name})
        loc = result.headers['Location']
        if loc.startswith(self.__api_host + '/zones/'):
            uid= UUID(loc[-36:])
            return await self.get_zone(uid)
        else:
            raise LiveDNSException("Zone URL was not of expected format -- got {}".format(loc))

    async def get_domains(self) -> List[Domain]


