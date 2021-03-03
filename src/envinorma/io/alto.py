from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString

_Soup = Union[Tag, BeautifulSoup]


def _is_empty(child: Union[str, Tag]) -> bool:
    if isinstance(child, str) and not child.strip():
        return True
    return False


def assert_tag(tag: Union[str, Tag, None]) -> Tag:
    if not isinstance(tag, Tag):
        raise ValueError(f'Expecting tag, got {type(tag)}\n{tag}')
    return tag


def assert_str(candidate: Any) -> str:
    if not isinstance(candidate, str):
        raise ValueError(f'Expecting type str, got {type(candidate)}')
    return candidate


def assert_float(candidate: Any) -> float:
    if not isinstance(candidate, float):
        try:
            return float(candidate)
        except:
            raise ValueError(f'Expecting type float, got {type(candidate)}')
    return candidate


def assert_int(candidate: Any) -> int:
    if not isinstance(candidate, int):
        try:
            return int(candidate)
        except:
            raise ValueError(f'Expecting type int, got {type(candidate)}')
    return candidate


def _extract_unique_tag_name_to_tag(soup: _Soup) -> Dict[str, Tag]:
    res: Dict[str, Tag] = {}
    for child in soup.children:
        if isinstance(child, str) and not child.strip():
            continue
        child = assert_tag(child)
        if child.name in res:
            raise ValueError(f'Non unique child tag name: {child}')
        res[child.name] = child
    return res


def _assert_name_is(name: str, expected: str) -> None:
    if name != expected:
        raise ValueError(f'Expecting {expected}, got {name}')


@dataclass
class AltoTextStyle:
    id: str
    font_size: float

    @classmethod
    def from_soup(cls, soup: _Soup) -> 'AltoTextStyle':
        return cls(id=assert_str(soup.get('ID')), font_size=assert_float(soup.get('FONTSIZE')))


AltoStyle = Union[AltoTextStyle]


def _load_alto_style(soup: _Soup) -> AltoStyle:
    if soup.name == 'TextStyle':
        return AltoTextStyle.from_soup(soup)
    raise NotImplementedError(soup.name)


@dataclass
class AltoDescription:
    file_name: str

    @classmethod
    def from_soup(cls, soup: _Soup) -> 'AltoDescription':
        tag_name_to_tag = _extract_unique_tag_name_to_tag(soup)
        source = tag_name_to_tag['sourceImageInformation']
        return cls(str(_extract_unique_tag_name_to_tag(source)['fileName']))


@dataclass
class AltoAlternative:
    content: str

    @classmethod
    def from_soup(cls, soup: _Soup) -> 'AltoAlternative':
        return cls(content=assert_str(soup.children))


@dataclass
class AltoString:
    height: float
    width: float
    hpos: float
    vpos: float
    content: str
    confidence: float
    alternatives: List[AltoAlternative]

    @classmethod
    def from_soup(cls, soup: _Soup) -> 'AltoString':
        return cls(
            height=assert_float(soup.get('HEIGHT')),
            width=assert_float(soup.get('WIDTH')),
            hpos=assert_float(soup.get('HPOS')),
            vpos=assert_float(soup.get('VPOS')),
            content=assert_str(soup.get('CONTENT')),
            confidence=assert_float(soup.get('WC')),
            alternatives=[AltoAlternative.from_soup(child) for child in soup.children if not _is_empty(child)],
        )


@dataclass
class AltoSP:
    width: float
    hpos: float
    vpos: float

    @classmethod
    def from_soup(cls, soup: _Soup) -> 'AltoSP':
        return cls(
            width=assert_float(soup.get('WIDTH')),
            hpos=assert_float(soup.get('HPOS')),
            vpos=assert_float(soup.get('VPOS')),
        )


def _load_string_or_sp(child: _Soup) -> Union[AltoString, AltoSP]:
    if child.name == 'String':
        return AltoString.from_soup(child)
    if child.name == 'SP':
        return AltoSP.from_soup(child)
    raise NotImplementedError(child.name)


@dataclass
class AltoTextLine:
    height: float
    width: float
    hpos: float
    vpos: float
    strings: List[Union[AltoString, AltoSP]]

    @classmethod
    def from_soup(cls, soup: _Soup) -> 'AltoTextLine':
        _assert_name_is(soup.name, 'TextLine')
        return cls(
            height=assert_float(soup.get('HEIGHT')),
            width=assert_float(soup.get('WIDTH')),
            hpos=assert_float(soup.get('HPOS')),
            vpos=assert_float(soup.get('VPOS')),
            strings=[_load_string_or_sp(child) for child in soup.children if not _is_empty(child)],
        )

    def extract_strings(self) -> List[str]:
        return [str_.content for str_ in self.strings if isinstance(str_, AltoString)]


@dataclass
class AltoTextBlock:
    id: Optional[str]
    height: float
    width: float
    hpos: float
    vpos: float
    text_lines: List[AltoTextLine]

    @classmethod
    def from_soup(cls, soup: _Soup) -> 'AltoTextBlock':
        _assert_name_is(soup.name, 'TextBlock')
        return cls(
            id=assert_str(soup.get('id')) if soup.get('id') else None,
            height=assert_float(soup.get('HEIGHT')),
            width=assert_float(soup.get('WIDTH')),
            hpos=assert_float(soup.get('HPOS')),
            vpos=assert_float(soup.get('VPOS')),
            text_lines=[AltoTextLine.from_soup(child) for child in soup.children if not _is_empty(child)],
        )

    def extract_string_lines(self) -> List[str]:
        return [' '.join(line.extract_strings()) for line in self.text_lines]


@dataclass
class AltoComposedBlock:
    id: str
    height: float
    width: float
    hpos: float
    vpos: float
    text_blocks: List[AltoTextBlock]

    @classmethod
    def from_soup(cls, soup: _Soup) -> 'AltoComposedBlock':
        _assert_name_is(soup.name, 'ComposedBlock')
        return cls(
            height=assert_float(soup.get('HEIGHT')),
            width=assert_float(soup.get('WIDTH')),
            hpos=assert_float(soup.get('HPOS')),
            vpos=assert_float(soup.get('VPOS')),
            id=assert_str(soup.get('ID')),
            text_blocks=[AltoTextBlock.from_soup(child) for child in soup.children if not _is_empty(child)],
        )


@dataclass
class AltoPrintSpace:
    height: float
    width: float
    hpos: float
    vpos: float
    pc: Optional[float]
    composed_blocks: List[AltoComposedBlock]

    @classmethod
    def from_soup(cls, soup: _Soup) -> 'AltoPrintSpace':
        _assert_name_is(soup.name, 'PrintSpace')
        return cls(
            height=assert_float(soup.get('HEIGHT')),
            width=assert_float(soup.get('WIDTH')),
            hpos=assert_float(soup.get('HPOS')),
            vpos=assert_float(soup.get('VPOS')),
            pc=assert_float(soup.get('PC')) if soup.get('PC') else None,
            composed_blocks=[AltoComposedBlock.from_soup(child) for child in soup.children if not _is_empty(child)],
        )


@dataclass
class AltoPage:
    id: str
    height: float
    width: float
    physical_img_nr: int
    printed_img_nr: Optional[int]
    print_spaces: List[AltoPrintSpace]

    @classmethod
    def from_soup(cls, soup: _Soup) -> 'AltoPage':
        _assert_name_is(soup.name, 'Page')
        return cls(
            id=assert_str(soup.get('ID')),
            height=assert_float(soup.get('HEIGHT')),
            width=assert_float(soup.get('WIDTH')),
            physical_img_nr=assert_int(soup.get('PHYSICAL_IMG_NR')),
            printed_img_nr=assert_int(soup.get('PRINTED_IMG_NR')) if soup.get('PRINTED_IMG_NR') else None,
            print_spaces=[AltoPrintSpace.from_soup(child) for child in soup.children if not _is_empty(child)],
        )


@dataclass
class AltoLayout:
    pages: List[AltoPage]

    @classmethod
    def from_soup(cls, soup: _Soup) -> 'AltoLayout':
        return cls(pages=[AltoPage.from_soup(child) for child in soup.children if not _is_empty(child)])


@dataclass
class AltoStyles:
    styles: List[AltoStyle]

    @classmethod
    def from_soup(cls, soup: _Soup) -> 'AltoStyles':
        return cls(styles=[_load_alto_style(child) for child in soup.children if not _is_empty(child)])


@dataclass
class AltoFile:
    description: AltoDescription
    styles: Optional[AltoStyles]
    layout: AltoLayout

    @classmethod
    def from_soup(cls, soup: _Soup) -> 'AltoFile':
        tag_name_to_tag = _extract_unique_tag_name_to_tag(soup)
        return cls(
            description=AltoDescription.from_soup(tag_name_to_tag['Description']),
            styles=AltoStyles.from_soup(tag_name_to_tag['Styles']) if 'Styles' in tag_name_to_tag else None,
            layout=AltoLayout.from_soup(tag_name_to_tag['Layout']),
        )

    @classmethod
    def from_xml(cls, xml: Union[str, bytes]) -> 'AltoFile':
        soup = BeautifulSoup(xml, 'lxml-xml')
        return cls.from_soup(assert_tag(soup.find('alto')))


def _extract_attrs(soup: _Soup) -> List[Tuple[str, str]]:
    if isinstance(soup, NavigableString):
        return []
    return [(soup.name, attr) for attr in soup.attrs] + [
        tp
        for child in soup.children
        for tp in _extract_attrs(child)
        if (isinstance(child, Tag) and not isinstance(child, str))
    ]


def extract_words(alto: AltoFile) -> List[str]:
    return [
        string.content
        for page in alto.layout.pages
        for ps in page.print_spaces
        for block in ps.composed_blocks
        for tb in block.text_blocks
        for line in tb.text_lines
        for string in line.strings
        if isinstance(string, AltoString)
    ]


def extract_strings(page: AltoPage) -> List[AltoString]:
    return [
        string
        for ps in page.print_spaces
        for block in ps.composed_blocks
        for tb in block.text_blocks
        for line in tb.text_lines
        for string in line.strings
        if isinstance(string, AltoString)
    ]


def extract_lines(page: AltoPage) -> List[AltoTextLine]:
    return [
        line
        for ps in page.print_spaces
        for block in ps.composed_blocks
        for tb in block.text_blocks
        for line in tb.text_lines
    ]


def extract_text_blocks(page: AltoPage) -> List[AltoTextBlock]:
    return [tb for ps in page.print_spaces for block in ps.composed_blocks for tb in block.text_blocks]


def extract_blocks(page: AltoPage) -> List[AltoComposedBlock]:
    return [block for ps in page.print_spaces for block in ps.composed_blocks]
