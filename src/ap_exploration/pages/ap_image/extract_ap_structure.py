import string
from dataclasses import dataclass, replace
from typing import Callable, List, Optional, Set, Tuple, TypeVar, Union

from scipy.spatial import Rectangle
from textdistance import levenshtein
from unidecode import unidecode

from ap_exploration.pages.ap_image.table_extraction import group_by_proximity
from envinorma.io.alto import AltoComposedBlock, AltoPage, AltoString, AltoTextLine, extract_lines


def _ensure_str(str_: Union[str, bytes]) -> str:
    if isinstance(str_, bytes):
        return str_.decode()
    return str_


def lower_unicode(str_: str) -> str:
    return _ensure_str(unidecode(str_).lower())


_ALPHANUMERIC = set(string.ascii_lowercase + string.digits)


def keep_alphanumeric(str_: str) -> str:
    return ''.join([x for x in str_ if x in str_ if x in _ALPHANUMERIC])


def _is_in_margin(str_: AltoString, page_height: float, page_width: float) -> bool:
    return any(
        [
            str_.vpos <= page_height * 0.03,
            str_.vpos + str_.height >= page_height * 0.97,
            str_.hpos <= page_width * 0.03,
            str_.hpos + str_.width >= page_width * 0.97,
        ]
    )


def find_strings_in_margin(pages: List[AltoPage]) -> List[AltoString]:
    return [
        str_
        for page in pages
        for line in extract_lines(page)
        for str_ in line.strings
        if isinstance(str_, AltoString)
        if _is_in_margin(str_, page.height, page.width)
    ]


def _line_in_upper_half(line: AltoTextLine, page_height: float) -> bool:
    bottom = line.vpos + line.height
    return bottom <= page_height / 2


T = TypeVar('T')


def _keep_before_match(lines: List[T], criterion: Callable[[T], bool]) -> Optional[List[T]]:
    for i, line in enumerate(lines):
        if criterion(line):
            return lines[: i + 1]
    return None


def _keep_after_match(lines: List[T], criterion: Callable[[T], bool]) -> Optional[List[T]]:
    for i, line in enumerate(lines):
        if criterion(line):
            return lines[i:]
    return None


def _is_levenshtein_close(word: str, distance: int, target_words: List[str]) -> bool:
    word = lower_unicode(word)
    for cd in target_words:
        if levenshtein(word, cd) <= distance:
            return True
    return False


_ENVIRONMENT_STRS = ['environnement', 'l\'environnement']


def _is_environnement(str_: str) -> bool:
    return _is_levenshtein_close(str_, 2, _ENVIRONMENT_STRS)


def _is_first_visa_line(line: AltoTextLine) -> bool:
    before_environment = _keep_before_match(line.extract_strings(), _is_environnement)
    if before_environment is None:
        return False
    merged = lower_unicode(''.join(before_environment))
    return levenshtein(keep_alphanumeric(merged), 'vulecodedelenvironnement') <= 4


def _is_ordre(str_: str) -> bool:
    return _is_levenshtein_close(str_, 2, ['ordre', 'l\'ordre'])


def _is_last_intro_line(line: AltoTextLine) -> bool:
    after_ordre = _keep_after_match(line.extract_strings(), _is_ordre)
    if after_ordre is None:
        return False
    merged = lower_unicode(''.join(after_ordre))
    return levenshtein(keep_alphanumeric(merged), 'ordrenationaldumerite') <= 4


def _extract_intro_lines(page: AltoPage) -> List[AltoTextLine]:
    lines = [line for line in extract_lines(page) if _line_in_upper_half(line, page.height)]
    before_visa = (_keep_before_match(lines, _is_first_visa_line) or [])[:-1]
    before_last_intro_line = _keep_before_match(lines, _is_last_intro_line)
    return before_last_intro_line if before_last_intro_line else before_visa if before_visa else lines


_PAGE_PROXIMITY_THRESHOLD = 50
_PAGE_Y_DEFORMATION = 4


def _rectangle(str_: AltoString, y_deformation: float = _PAGE_Y_DEFORMATION) -> Rectangle:
    return Rectangle(
        mins=[str_.hpos, str_.vpos * y_deformation],
        maxes=[str_.hpos + str_.width, (str_.vpos + str_.height) * y_deformation],
    )


def _are_neighbor(str_1: AltoString, str_2: AltoString) -> bool:
    rect_1 = _rectangle(str_1)
    rect_2 = _rectangle(str_2)
    return rect_1.min_distance_rectangle(rect_2) <= _PAGE_PROXIMITY_THRESHOLD


def _merge_strings_by_proximity(strs: List[AltoString]) -> List[List[AltoString]]:
    return group_by_proximity(strs, _are_neighbor)


@dataclass
class Box:
    hpos: float
    vpos: float
    width: float
    height: float


def _bounding_box(strings: List[AltoString]) -> Box:
    hpos = min([str_.hpos for str_ in strings])
    vpos = min([str_.vpos for str_ in strings])
    return Box(
        hpos=hpos,
        vpos=vpos,
        width=max([str_.hpos + str_.width for str_ in strings]) - hpos,
        height=max([str_.vpos + str_.height for str_ in strings]) - vpos,
    )


def _extract_sentence(group: List[AltoString]) -> str:
    return ' '.join([x.content for x in group])


@dataclass
class APIntro:
    title: List[str]
    marianne: List[str]
    prefet: List[str]
    bureau: List[str]
    visa: List[str]
    other: List[str]


_TITLE_WORDS = [
    'arrete prefectoral',
    'prescriptions relatives',
    'autorisation d\'exploitation',
    'portant',
    'arrete complementaire',
    'prescriptions complementaires',
    'autorisant',
    'imposant des prescriptions',
    'modifiant le',
]


def _is_title(group: List[str]) -> bool:
    str_ = lower_unicode(' '.join(group))
    return any([word in str_ for word in _TITLE_WORDS])


_BUREAU_WORDS = [
    'direction regionale',
    'direction departementale',
    'direction des actions',
    'direction des collectivites',
    'service des procedures',
    'bureau de l\'urbanisme',
    'direction des libertes',
    'direction de la coordination',
    'bureau de l\'environnement',
    'bureau des politiques',
    'direction de l\'environnement',
    'direction de',
    'bureau de',
]


def _is_bureau(group: List[str]) -> bool:
    str_ = lower_unicode(' '.join(group))
    return any([word in str_ for word in _BUREAU_WORDS])


_MARIANNE_WORDS = ['liberte', 'egalite', 'fraternite', 'republique', 'francaise']


def _is_marianne(group: List[str]) -> bool:
    return sum([_is_levenshtein_close(word, 2, _MARIANNE_WORDS) for word in group]) >= 2


_PREFET_WORDS = ['prefet de', 'prefete de', 'prefecture de', 'le prefet', 'la prefete']


def _is_prefet(group: List[str]) -> bool:
    sentence = lower_unicode(' '.join(group))
    return any([sentence.startswith(word) for word in _PREFET_WORDS]) or _is_levenshtein_close(group[0], 2, ['prefet'])


_VISA_WORDS = [
    'la directive',
    'vu la directive',
    'vu les',
    'vu la',
    'vu',
    'l\'arrete ministeriel',
    'l\'instruction technique',
]


def _is_visa(group: List[str]) -> bool:
    sentence = lower_unicode(' '.join(group))
    return any([sentence.startswith(word) for word in _VISA_WORDS])


def _classify(groups: List[List[AltoString]]) -> APIntro:
    strings = [[x.content for x in xs] for xs in groups]
    res = APIntro([], [], [], [], [], [])
    for group in strings:
        sentence = ' '.join(group)
        if _is_title(group):
            res.title.append(sentence)
        elif _is_marianne(group):
            res.marianne.append(sentence)
        elif _is_prefet(group):
            res.prefet.append(sentence)
        elif _is_bureau(group):
            res.bureau.append(sentence)
        elif _is_visa(group):
            res.visa.append(sentence)
        else:
            res.other.append(sentence)
    return res


def _remove_lines_in_block(block: AltoComposedBlock, lines: Set[AltoTextLine]) -> AltoComposedBlock:
    text_blocks = [
        replace(tb, text_lines=[line for line in tb.text_lines if line not in lines]) for tb in block.text_blocks
    ]
    return replace(block, text_blocks=text_blocks)


def _remove_lines(page: AltoPage, lines: Set[AltoTextLine]) -> AltoPage:
    print_spaces = [
        replace(space, composed_blocks=[_remove_lines_in_block(bk, lines) for bk in space.composed_blocks])
        for space in page.print_spaces
    ]
    return replace(page, print_spaces=print_spaces)


def extract_ap_intro(first_page: AltoPage) -> Tuple[APIntro, AltoPage]:
    intro_lines = _extract_intro_lines(first_page)
    groups = _merge_strings_by_proximity(
        [str_ for line in intro_lines for str_ in line.strings if isinstance(str_, AltoString)]
    )
    return _classify(groups), _remove_lines(first_page, set(intro_lines))
