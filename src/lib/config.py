import os
from configparser import ConfigParser
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache


def _get_var(section: str, varname: str) -> str:
    env_key = f'{section}_{varname}'
    if env_key in os.environ:
        return os.environ[env_key]
    config = load_config()
    try:
        return config[section][varname]
    except KeyError:
        raise ValueError(f'Variable {varname} must either be defined in config.ini or in environment.')


@dataclass
class AidaConfig:
    base_url: str

    @classmethod
    def default_load(cls) -> 'AidaConfig':
        return cls(**{key: _get_var('aida', key) for key in cls.__annotations__})


@dataclass
class LegifranceConfig:
    client_secret: str

    @classmethod
    def default_load(cls) -> 'LegifranceConfig':
        return cls(**{key: _get_var('legifrance', key) for key in cls.__annotations__})


@dataclass
class StorageConfig:
    am_data_folder: str
    psql_dsn: str

    @classmethod
    def default_load(cls) -> 'StorageConfig':
        return cls(**{key: _get_var('storage', key) for key in cls.__annotations__})


@dataclass
class SlackConfig:
    enrichment_notification_url: str

    @classmethod
    def default_load(cls) -> 'SlackConfig':
        return cls(**{key: _get_var('slack', key) for key in cls.__annotations__})


class EnvironmentType(Enum):
    PROD = 'prod'
    DEV = 'dev'


@dataclass
class EnvironmentConfig:
    type: EnvironmentType

    @classmethod
    def default_load(cls) -> 'EnvironmentConfig':
        try:
            type_ = EnvironmentType(_get_var('environment', 'type'))
        except KeyError:
            type_ = EnvironmentType.PROD
        return EnvironmentConfig(type=type_)


@dataclass
class Config:
    aida: AidaConfig
    legifrance: LegifranceConfig
    storage: StorageConfig
    slack: SlackConfig
    environment: EnvironmentConfig

    @classmethod
    def default_load(cls) -> 'Config':
        return cls(
            aida=AidaConfig.default_load(),
            legifrance=LegifranceConfig.default_load(),
            storage=StorageConfig.default_load(),
            slack=SlackConfig.default_load(),
            environment=EnvironmentConfig.default_load(),
        )


@lru_cache
def load_config() -> ConfigParser:
    parser = ConfigParser()
    parser.read('config.ini')
    return parser


config = Config.default_load()

AIDA_URL = config.aida.base_url
LEGIFRANCE_CLIENT_SECRET = config.legifrance.client_secret
AM_DATA_FOLDER = config.storage.am_data_folder
