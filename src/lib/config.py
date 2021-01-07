import os


def _get_var(varname: str) -> str:
    if varname in os.environ:
        return os.environ[varname]
    try:
        import lib.secrets

        return getattr(lib.secrets, varname)
    except (ImportError, AttributeError):
        raise ValueError(f'Variable {varname} must either be defined in lib.secrets or in environment.')


AIDA_URL = _get_var('AIDA_URL')
LEGIFRANCE_CLIENT_SECRET = _get_var('LEGIFRANCE_CLIENT_SECRET')
AM_DATA_FOLDER = _get_var('AM_DATA_FOLDER')
STORAGE = _get_var('STORAGE')
