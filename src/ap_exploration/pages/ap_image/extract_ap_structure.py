import os
import string
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple, TypeVar, Union

from ap_exploration.pages.ap_image.process import load_pages_and_tables
from ap_exploration.pages.ap_image.table_extraction import LocatedTable, group_by_proximity
from envinorma.config import config
from envinorma.io.alto import AltoPage, AltoString, AltoTextLine, extract_lines
from scipy.spatial import Rectangle
from textdistance import levenshtein
from tqdm import tqdm
from unidecode import unidecode


def _load_pages_and_tables(folder: str) -> Tuple[List[AltoPage], List[LocatedTable]]:
    return load_pages_and_tables(folder + '.pdf')


def _ensure_str(str_: Union[str, bytes]) -> str:
    if isinstance(str_, bytes):
        return str_.decode()
    return str_


_ALPHANUMERIC = set(string.ascii_lowercase + string.digits)


def _keep_alphanumeric(str_: str) -> str:
    return ''.join([x for x in str_ if x in str_ if x in _ALPHANUMERIC])


def _line_in_upper_third(line: AltoTextLine, page_height: float) -> bool:
    bottom = line.vpos + line.height
    return bottom <= page_height / 3


def _is_in_the_center(line: AltoTextLine, page_width: float) -> bool:
    return line.hpos >= 0.25 * page_width and line.hpos + line.width <= 0.75 * page_width


def _is_arrete_line(line: AltoTextLine, page_rank: int, page_height: float, page_width: float) -> bool:
    if not _is_in_the_center(line, page_width):
        return False
    strings = _extract_strings(line)
    clean_words = _keep_alphanumeric(_lower_unicode(''.join(strings)))
    if clean_words == 'arrete':
        if page_rank != 0:
            return True
        return not _line_in_upper_third(line, page_height)  # in this case, it is probably the doc title
    return False


def find_arrete_word(pages: List[AltoPage]) -> List[AltoTextLine]:
    return [
        line
        for page_rank, page in enumerate(pages[:4])
        for line in extract_lines(page)
        if _is_arrete_line(line, page_rank, page.height, page.width)
    ]


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


def _extract_strings(line: AltoTextLine) -> List[str]:
    return [x.content for x in line.strings if isinstance(x, AltoString)]


def _is_levenshtein_close(word: str, distance: int, target_words: List[str]) -> bool:
    word = _lower_unicode(word)
    for cd in target_words:
        if levenshtein(word, cd) <= distance:
            return True
    return False


_ENVIRONMENT_STRS = ['environnement', 'l\'environnement']


def _is_environnement(str_: str) -> bool:
    return _is_levenshtein_close(str_, 2, _ENVIRONMENT_STRS)


def _is_first_visa_line(line: AltoTextLine) -> bool:
    strings = _extract_strings(line)
    before_environment = _keep_before_match(strings, _is_environnement)
    if before_environment is None:
        return False
    merged = _lower_unicode(''.join(before_environment))
    return levenshtein(_keep_alphanumeric(merged), 'vulecodedelenvironnement') <= 4


def _is_ordre(str_: str) -> bool:
    return _is_levenshtein_close(str_, 2, ['ordre', 'l\'ordre'])


def _is_last_intro_line(line: AltoTextLine) -> bool:
    strings = _extract_strings(line)
    after_ordre = _keep_after_match(strings, _is_ordre)
    if after_ordre is None:
        return False
    merged = _lower_unicode(''.join(after_ordre))
    return levenshtein(_keep_alphanumeric(merged), 'ordrenationaldumerite') <= 4


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
    str_ = _lower_unicode(' '.join(group))
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


def _lower_unicode(str_: str) -> str:
    return _ensure_str(unidecode(str_).lower())


def _is_bureau(group: List[str]) -> bool:
    str_ = _lower_unicode(' '.join(group))
    return any([word in str_ for word in _BUREAU_WORDS])


_MARIANNE_WORDS = ['liberte', 'egalite', 'fraternite', 'republique', 'francaise']


def _is_marianne(group: List[str]) -> bool:
    return sum([_is_levenshtein_close(word, 2, _MARIANNE_WORDS) for word in group]) >= 2


_PREFET_WORDS = ['prefet de', 'prefete de', 'prefecture de', 'le prefet', 'la prefete']


def _is_prefet(group: List[str]) -> bool:
    sentence = _lower_unicode(' '.join(group))
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
    sentence = _lower_unicode(' '.join(group))
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


def _find_main_title(pages: List[AltoPage]) -> Tuple[AltoPage, List[Box], APIntro]:
    if not pages:
        raise ValueError('Expecting at least one page.')
    intro_lines = _extract_intro_lines(pages[0])
    groups = _merge_strings_by_proximity(
        [str_ for line in intro_lines for str_ in line.strings if isinstance(str_, AltoString)]
    )
    bounding_boxes = [_bounding_box(group) for group in groups]
    # sentences = [_extract_sentence(group) for group in groups]
    return pages[0], bounding_boxes, _classify(groups)
    # return '\n'.join([' '.join(_extract_strings(line)) for line in intro_lines])


if __name__ == '__main__':
    import pickle
    import random

    _PDF_AP_FOLDER = config.storage.ap_data_folder
    _DOC_IDS = [os.path.join(_PDF_AP_FOLDER, x) for x in os.listdir(_PDF_AP_FOLDER) if x.endswith('.pdf')][:110]

    file_ = 'tmp.pickle'
    if not os.path.exists(file_):
        pages_and_tables = [_load_pages_and_tables(filename[:-4]) for filename in tqdm(_DOC_IDS)]
        pickle.dump(pages_and_tables, open(file_, 'wb'))
    else:
        pages_and_tables = pickle.load(open(file_, 'rb'))

    res = [_find_main_title(pages) for pages, _ in tqdm(pages_and_tables)]
    all_str = [(doc_id.split('/')[-1], strs) for doc_id, strs in zip(_DOC_IDS, res)]
    filename, (_, _, intro) = random.choice(all_str)
    for _, _, intro in res:
        print('\n\t'.join(intro.other))
    print('TITLE\n\t', '\n\t'.join(intro.title))
    print('MARIANNE\n\t', '\n\t'.join(intro.marianne))
    print('PREFET\n\t', '\n\t'.join(intro.prefet))
    print('BUREAU\n\t', '\n\t'.join(intro.bureau))
    print('VISA\n\t', '\n\t'.join(intro.visa))
    print('OTHER\n\t', '\n\t'.join(intro.other))
