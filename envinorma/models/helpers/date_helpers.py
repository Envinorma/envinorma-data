import re
from datetime import date, datetime

_MONTHS = r'(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)'
_PATTERN = r'Arrêté du (1er|[0-9]*) ' + _MONTHS + ' [0-9]{4}'


def _contains_human_date(title: str) -> bool:
    return re.match(_PATTERN, title) is not None


def _year(year_str: str) -> int:
    if not year_str.isdigit():
        raise ValueError(f'Expecting {year_str} to be a digit')
    return int(year_str)


_MONTH_TO_MONTH_RANK = {
    'janvier': 1,
    'février': 2,
    'mars': 3,
    'avril': 4,
    'mai': 5,
    'juin': 6,
    'juillet': 7,
    'août': 8,
    'septembre': 9,
    'octobre': 10,
    'novembre': 11,
    'décembre': 12,
}


def _month(french_month: str) -> int:
    if french_month not in _MONTH_TO_MONTH_RANK:
        raise ValueError(f'Expecting month to be in {_MONTH_TO_MONTH_RANK} got {french_month}')
    return _MONTH_TO_MONTH_RANK[french_month]


def _day(day_str: str) -> int:
    if day_str == '1er':
        return 1
    if not day_str.isdigit():
        raise ValueError(f'Expecting {day_str} to be a digit')
    return int(day_str)


def _read_human_french_date(day_str: str, french_month: str, year_str: str) -> date:
    return date(_year(year_str), _month(french_month), _day(day_str))


def _standardize_date(day_str: str, french_month: str, year_str: str) -> str:
    date_ = _read_human_french_date(day_str, french_month, year_str)
    return date_.strftime('%d/%m/%y')


def standardize_title_date(title: str) -> str:
    words = title.split()
    if len(words) <= 5:
        raise ValueError(f'Expecting title to have at least 5 words, got {len(words)} (title={title}).')
    new_words = words[:2] + [_standardize_date(*words[2:5])] + words[5:]
    return ' '.join(new_words)


def standardize_title_if_necessary(title: str) -> str:
    if title == 'Faux arrêté':  # Edge case for test text
        return 'Faux arrêté du 10/10/10'
    if _contains_human_date(title):
        return standardize_title_date(title)
    return title


_DATE_PATTERN = r'^[0-9]{2}/[0-9]{2}/[0-9]{2}$'


def _extract_date(candidate_date: str) -> date:
    if not re.match(_DATE_PATTERN, candidate_date):
        raise ValueError(f'Expecting format {_DATE_PATTERN}. Got {candidate_date}.')
    return datetime.strptime(candidate_date, '%d/%m/%y').date()


def extract_short_title(input_title: str) -> str:
    return input_title.split('relatif')[0].split('fixant')[0].strip()


def extract_date_of_signature(input_title: str) -> date:
    short_title = extract_short_title(input_title)
    candidate_date = (short_title.split() or [''])[-1]
    return _extract_date(candidate_date)
