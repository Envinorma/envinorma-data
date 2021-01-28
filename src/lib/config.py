import os
from configparser import ConfigParser
from dataclasses import dataclass
from functools import lru_cache


def _get_var(section: str, varname: str) -> str:
    env_key = f'{section}_{varname}'
    if varname in os.environ:
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
class Config:
    aida: AidaConfig
    legifrance: LegifranceConfig
    storage: StorageConfig

    @classmethod
    def default_load(cls) -> 'Config':
        return cls(
            aida=AidaConfig.default_load(),
            legifrance=LegifranceConfig.default_load(),
            storage=StorageConfig.default_load(),
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
