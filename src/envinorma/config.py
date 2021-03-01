import os
from configparser import ConfigParser
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Tuple


class _ConfigError(Exception):
    pass


def _get_var(section: str, varname: str) -> str:
    env_key = f'{section}_{varname}'
    if env_key in os.environ:
        return os.environ[env_key]
    config = load_config()
    try:
        return config[section][varname]
    except KeyError:
        raise _ConfigError(f'Variable {varname} must either be defined in config.ini or in environment.')


@dataclass
class AidaConfig:
    base_url: str

    @classmethod
    def default_load(cls) -> 'AidaConfig':
        return cls(**{key: _get_var('aida', key) for key in cls.__annotations__})


@dataclass
class LegifranceConfig:
    client_secret: str
    client_id: str

    @classmethod
    def default_load(cls) -> 'LegifranceConfig':
        return cls(**{key: _get_var('legifrance', key) for key in cls.__annotations__})


@dataclass
class StorageConfig:
    am_data_folder: str
    psql_dsn: str
    ap_data_folder: str
    tessdata: str

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
        except _ConfigError:
            type_ = EnvironmentType.PROD
        return cls(type=type_)


@dataclass
class LoginConfig:
    username: str
    password: str
    secret_key: str

    @classmethod
    def default_load(cls) -> 'LoginConfig':
        return cls(**{key: _get_var('login', key) for key in cls.__annotations__})


@dataclass
class Config:
    aida: AidaConfig
    legifrance: LegifranceConfig
    storage: StorageConfig
    slack: SlackConfig
    environment: EnvironmentConfig
    login: LoginConfig

    @classmethod
    def default_load(cls) -> 'Config':
        return cls(
            aida=AidaConfig.default_load(),
            legifrance=LegifranceConfig.default_load(),
            storage=StorageConfig.default_load(),
            slack=SlackConfig.default_load(),
            environment=EnvironmentConfig.default_load(),
            login=LoginConfig.default_load(),
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


def get_parametric_ams_folder(am_id: str) -> str:
    return f'{AM_DATA_FOLDER}/parametric_texts/{am_id}'


def generate_parametric_descriptor(version_descriptor: Tuple[str, ...]) -> str:
    if not version_descriptor:
        return 'no_date_version'
    return '_AND_'.join(version_descriptor).replace(' ', '_')


def create_folder_and_generate_parametric_filename(am_id: str, version_descriptor: Tuple[str, ...]) -> str:
    folder_name = get_parametric_ams_folder(am_id)
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    return get_parametric_ams_folder(am_id) + '/' + generate_parametric_descriptor(version_descriptor) + '.json'
