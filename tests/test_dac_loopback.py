import copy
import json
import pytest
from benchmate import dac_loopback as loopback
from benchmate.records import read_events


def responses():
    state = {'protocol': loopback.PROTOCOL, 'nominal_supply_mv': 4900,
             'calibrated': False, 'adc_bits': 14, 'dac_bits': 12,
             'dac_enabled': True, 'dac_code': 501, 'nominal_level_mv': 600}
    return [{**state, 'type': 'pong', 'dac_enabled': False, 'dac_code': 0, 'nominal_level_mv': 0},
            {**state, 'type': 'holding'},
            {**state, 'type': 'capture', 'source': 'hardware_uncalibrated',
             'channels': ['A1', 'A2', 'A3', 'A4'],
             'timestamp_semantics': 'analogRead_completion_us',
             'samples': [{'t_us': [i*640+c*28 for c in range(4)], 'raw': [2010, 2012, 2009, 2011]}
                         for i in range(64)]}]


class Board:
    def __init__(self, packets):
        self.packets = packets
        self.writes = []
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def reset_input_buffer(self): pass
    def write(self, data): self.writes.append(data)
    def readline(self): return json.dumps(self.packets.pop(0)).encode() + b'\n'
    def read_until(self, *args, **kwargs): return self.readline()


def attach(monkeypatch, packets):
    board = Board(packets)
    monkeypatch.setattr(loopback.serial, 'Serial', lambda *a, **kw: board)
    monkeypatch.setattr(loopback.time, 'sleep', lambda _: None)
    return board


def test_one_point_records_raw_counts_and_leaves_dmm_voltage_unmeasured(monkeypatch, tmp_path):
    board = attach(monkeypatch, responses())
    path, result = loopback.acquire_point('test', 600, output=tmp_path)
    assert board.writes == [b'PING\n', b'HOLD 600\n', b'CAPTURE\n']
    assert result['output_remains_driven'] is True
    assert result['dmm_reading_v'] is None and result['calibration_performed'] is False
    assert result['raw_counts_by_channel']['A1']['mean'] == 2010
    assert read_events(path)[-1]['kind'] == 'run_completed'


def test_wrong_firmware_cannot_start_dac(monkeypatch, tmp_path):
    packets = responses()
    packets[0]['protocol'] = 'benchmate-bringup-v1'
    board = attach(monkeypatch, packets)
    with pytest.raises(RuntimeError): loopback.acquire_point('test', 600, output=tmp_path)
    assert board.writes == [b'PING\n']


def test_wrong_hold_ack_prevents_capture(monkeypatch, tmp_path):
    packets = responses()
    packets[1]['dac_code'] = 1337
    board = attach(monkeypatch, packets)
    with pytest.raises(RuntimeError): loopback.acquire_point('test', 600, output=tmp_path)
    assert board.writes == [b'PING\n', b'HOLD 600\n']


def test_rejected_raw_block_is_retained(monkeypatch, tmp_path):
    packets = responses()
    packets[2]['dac_code'] = 1337
    attach(monkeypatch, packets)
    with pytest.raises(RuntimeError): loopback.acquire_point('test', 600, output=tmp_path)
    events = read_events(next(tmp_path.iterdir()))
    assert events[-2]['kind'] == 'raw_capture'
    assert events[-2]['payload']['dac_code'] == 1337
    assert events[-1]['kind'] == 'run_failed'


@pytest.mark.parametrize('level', [0, 599, 601, 3300, True, 600.0])
def test_invalid_level_never_opens_serial(monkeypatch, tmp_path, level):
    def fail(*args, **kwargs): pytest.fail('Serial must not open for invalid levels')
    monkeypatch.setattr(loopback.serial, 'Serial', fail)
    with pytest.raises(ValueError): loopback.acquire_point('test', level, output=tmp_path)


@pytest.mark.parametrize('fault', ['short', 'timestamp', 'calibrated', 'source', 'dac_disabled'])
def test_loopback_rejects_incomplete_or_mislabeled_measurements(fault):
    packet = copy.deepcopy(responses()[2])
    if fault == 'short': packet['samples'].pop()
    if fault == 'timestamp': packet['samples'][1]['t_us'][0] = 0
    if fault == 'calibrated': packet['calibrated'] = True
    if fault == 'source': packet['source'] = 'synthetic'
    if fault == 'dac_disabled': packet['dac_enabled'] = False
    with pytest.raises(ValueError): loopback.validate_loopback_capture(packet, 600)
