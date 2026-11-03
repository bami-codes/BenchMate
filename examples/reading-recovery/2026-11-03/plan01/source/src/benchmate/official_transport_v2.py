"""Larger bounded transport; preserve opaque reasoning and the original executor."""
import json

from .official_passive import OfficialModel as OriginalOfficialModel

VERSION = 'official-transport-v2'
MAX_PAYLOAD_BYTES = 512000


class _ConfigurationLog:
    def __init__(self, log):
        self.log = log

    def add(self, kind, payload):
        if kind == 'provider_configuration':
            payload = {**payload, 'max_payload_bytes': MAX_PAYLOAD_BYTES,
                       'transport_version': VERSION}
        self.log.add(kind, payload)


class OfficialModel(OriginalOfficialModel):
    """Only the payload bound changes; request/output limits and history stay intact.

    The preserved constructor accepts its existing 128 kB option. This version
    explicitly raises that attribute after construction and records the effective
    512 kB limit. No conversation trimming, retries or hidden-reasoning logging.
    """
    def __init__(self, *, log, **kwargs):
        if 'max_payload_bytes' in kwargs:
            raise ValueError('This version has one fixed payload bound.')
        super().__init__(log=_ConfigurationLog(log), max_payload_bytes=128000, **kwargs)
        self.log = log
        self.max_payload_bytes = MAX_PAYLOAD_BYTES

    def next_call(self):
        size = len(json.dumps({**self.base, 'input': self.history}).encode())
        self.log.add('provider_payload_size', {
            'transport_version': VERSION, 'next_request_ordinal': self.requests + 1,
            'bytes': size, 'max_payload_bytes': self.max_payload_bytes,
            'within_bound': size <= self.max_payload_bytes,
            'payload_or_hidden_reasoning_logged': False})
        return super().next_call()

    def metadata(self):
        return {**super().metadata(), 'transport_version': VERSION,
                'max_payload_bytes': self.max_payload_bytes}
