from abc import ABC

from prometheus_client import Gauge, REGISTRY


class TransceiverBase(ABC):
    gauges = {}
