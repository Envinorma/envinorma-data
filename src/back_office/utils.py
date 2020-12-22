from lib.data import load_am_data

_AM = load_am_data()
ID_TO_AM_MD = {am.cid: am for am in _AM.metadata}
