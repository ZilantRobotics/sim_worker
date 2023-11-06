from enum import auto

from strenum import StrEnum


class ConfigVars(StrEnum):
    SIM_WSS_REMOTE_HOST = auto()
    SIM_WSS_REMOTE_PORT = auto()
    SIM_CA_CERT = auto()
    SIM_CA_KEY = auto()
    SIM_WSS_LOCAL_PORT = auto()
    SIM_WSS_LOCAL_HOST = auto()
    SIM_WORKER_NAME = auto()
    SIM_WORKER_UUID = auto()
    SIM_3D_SIM_LOCATION = auto()
    SIM_HITL_SIM_LOCATION = auto()


class Commands(StrEnum):
    WSS = 'wss'
    CLI = 'cli'
    NEW = 'new'
