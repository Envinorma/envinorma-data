import re
import requests
from copy import deepcopy
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass
from typing import Any, DefaultDict, Dict, List, Set, Optional
from collections import defaultdict
from scripts.AM_structure_extraction import EnrichedString, Link, StructuredArreteMinisteriel, StructuredText, Article

_AIDA_URL = 'https://aida.ineris.fr/consultation_document/{}'
_NOR_REGEXP = r'[A-Z]{4}[0-9]{7}[A-Z]'


def _extract_nor_from_text(text: str) -> str:
    match = re.search(_NOR_REGEXP, text)
    if not match:
        raise ValueError(f'NOR not found in {text}.')
    return text[match.start() : match.end()]


def extract_nor_from_html(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    for h5 in soup.find_all('h5'):
        if 'NOR' in h5.text:
            return _extract_nor_from_text(h5.text)
    raise ValueError('NOR not found!')


def download_html(document_id: str) -> str:
    response = requests.get(_AIDA_URL.format(document_id))
    if response.status_code != 200:
        raise ValueError(f'Request failed with status code {response.status_code}')
    return response.content.decode()


def scrap_nor(document_id: str) -> str:
    return extract_nor_from_html(download_html(document_id))


def extract_page_title(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    return soup.find('h1').text


def scrap_title(document_id: str) -> str:
    return extract_page_title(download_html(document_id))


@dataclass
class Hyperlink:
    content: str
    href: str


def get_aida_content_area(soup: BeautifulSoup) -> Tag:
    content_area = soup.find('div', {'id': 'content-area'})
    if not content_area:
        raise ValueError('Content area not found in this AIDA page!')
    return content_area


def extract_hyperlinks(html: str) -> List[Hyperlink]:
    soup = BeautifulSoup(html, 'html.parser')
    return [
        Hyperlink(tag.text, tag['href']) for tag in get_aida_content_area(soup).find_all('a') if 'href' in tag.attrs
    ]


_AIDA_PREFIXES_TO_REMOVE = [
    'http://gesreg03-bo.gesreg.fr/gesdoc_application/1/section/edit/',
    'http://gesreg03-bo.gesreg.fr/gesdoc_application/1/section/add/35358/',
    'http://',
]


def starts_with_hash(str_: str) -> bool:
    return bool(str_ and str_[0] == '#')


def cleanup_aida_href(str_: str, document_id: str) -> str:
    tmp_str = str_
    for prefix in _AIDA_PREFIXES_TO_REMOVE:
        tmp_str = tmp_str.replace(prefix, '')
    return _AIDA_URL.format(f'{document_id}{tmp_str}' if starts_with_hash(tmp_str) else tmp_str)


def cleanup_aida_link(link: Hyperlink, document_id: str) -> Hyperlink:
    return Hyperlink(href=cleanup_aida_href(link.href, document_id), content=link.content)


def keep_solid_aida_links(hyperlinks: List[Hyperlink]) -> List[Hyperlink]:
    content_to_targets: DefaultDict[str, List[str]] = defaultdict(list)
    for link in hyperlinks:
        content_to_targets[link.content].append(link.href)
    valid_contents = {
        content for content, targets in content_to_targets.items() if len(set(targets)) <= 1 and len(content) >= 4
    }
    return [link for link in hyperlinks if link.content in valid_contents]


def extract_all_urls_from_content_page(document_id: str) -> List[Hyperlink]:
    html = download_html(document_id)
    raw_links = extract_hyperlinks(html)
    return keep_solid_aida_links([cleanup_aida_link(link, document_id) for link in raw_links])


@dataclass
class Anchor:
    name: str
    anchored_text: str


def extract_anchor_if_present_in_tag(tag: Tag) -> Optional[Anchor]:
    a_tag = tag.find('a')
    if not a_tag:
        return None
    name = a_tag.attrs.get('name')
    if not name:
        return None
    anchored_text = tag.text.strip()
    return Anchor(name, anchored_text)


def extract_anchors_from_soup(content_area: Tag) -> List[Anchor]:
    candidates = [
        extract_anchor_if_present_in_tag(tag)
        for title_level in [f'h{i}' for i in range(1, 7)]
        for tag in content_area.find_all(title_level)
    ]

    return [anchor for anchor in candidates if anchor]


def extract_anchors(html: str) -> List[Anchor]:
    soup = BeautifulSoup(html)
    content_area = get_aida_content_area(soup)
    return extract_anchors_from_soup(content_area)


def keep_non_ambiguous_anchors(anchors: List[Anchor]) -> List[Anchor]:
    text_to_anchors: DefaultDict[str, Set[str]] = defaultdict(set)
    for anchor in anchors:
        text_to_anchors[anchor.anchored_text].add(anchor.name)
    return [
        Anchor(list(names)[0], anchored_text) for anchored_text, names in text_to_anchors.items() if len(names) == 1
    ]


def extract_all_anchors_from_aida(document_id: str) -> List[Anchor]:
    html = download_html(document_id)
    raw_anchors = extract_anchors(html)
    return keep_non_ambiguous_anchors(raw_anchors)


def add_links_in_article(article: Article, str_to_target: Dict[str, str]) -> Article:
    return Article(article.id, article.num, add_links_in_section(article.text, str_to_target))


def add_links_in_section(section: StructuredText, str_to_target: Dict[str, str]) -> StructuredText:
    return StructuredText(
        add_links_in_enriched_string(section.title, str_to_target),
        [add_links_in_enriched_string(alinea, str_to_target) for alinea in section.outer_alineas],
        [add_links_in_section(subsection, str_to_target) for subsection in section.sections],
    )


def generate_re_pattern_not_followed_by_alphanumeric(str_: str) -> str:
    return re.escape(str_) + r'(?![a-zA-Z0-9])'


def generate_found_links(str_to_parse: str, str_to_target: Dict[str, str]) -> List[Link]:
    return [
        (Link(target=target, position=match.span()[0], content_size=len(str_)))
        for str_, target in str_to_target.items()
        for match in re.finditer(generate_re_pattern_not_followed_by_alphanumeric(str_), str_to_parse)
    ]


def add_links_in_enriched_string(enriched_str: EnrichedString, str_to_target: Dict[str, str]) -> EnrichedString:
    new_enriched_str = deepcopy(enriched_str)
    new_enriched_str.links.extend(generate_found_links(enriched_str.text, str_to_target))
    return new_enriched_str


def add_aida_links(text: StructuredArreteMinisteriel, new_hyperlinks: List[Hyperlink]) -> StructuredArreteMinisteriel:
    str_to_target = {link.content: link.href for link in new_hyperlinks}
    return StructuredArreteMinisteriel(
        title=text.title,
        articles=[add_links_in_article(article, str_to_target) for article in text.articles],
        sections=[add_links_in_section(section, str_to_target) for section in text.sections],
        visa=[add_links_in_enriched_string(str_, str_to_target) for str_ in text.visa],
    )


def transform_aida_links_to_github_markdown_links(aida_links: List[Hyperlink], aida_anchors: List[Anchors]):
    pass


def scrap_all_anchors() -> None:
    import json
    from tqdm import tqdm
    from dataclasses import asdict

    arretes_ministeriels = json.load(open('data/AM/arretes_ministeriels.json'))
    page_ids = [am['aida_page'] for am in arretes_ministeriels]
    page_id_to_anchors_json: Dict[str, List[Dict[str, Any]]] = {}
    for page_id in tqdm(page_ids):
        try:
            page_id_to_anchors_json[page_id] = [asdict(anchor) for anchor in extract_all_anchors_from_aida(page_id)]
        except Exception as exc:  # pylint: disable=broad-except
            print(exc)
    json.dump(page_id_to_anchors_json, open('data/aida/hyperlinks/page_id_to_anchors.json', 'w'), ensure_ascii=False)


def generate_1510_markdown() -> None:
    import json
    from scripts.AM_structure_extraction import am_to_markdown, transform_arrete_ministeriel

    page_id_to_links = json.load(open('data/aida/hyperlinks/page_id_to_links.json'))
    arretes_ministeriels = json.load(open('data/AM/arretes_ministeriels.json'))
    magic_nor = 'DEVP1706393A'
    nor_to_page_id = {
        doc['nor']: doc['aida_page'] for doc in arretes_ministeriels if 'nor' in doc and 'aida_page' in doc
    }
    aida_page = nor_to_page_id[magic_nor]
    links = [Hyperlink(**link_doc) for link_doc in page_id_to_links[aida_page]]
    open(f'data/AM/markdown_texts/{magic_nor}.md', 'w').write(
        am_to_markdown(
            add_aida_links(
                transform_arrete_ministeriel(json.load(open(f'data/AM/legifrance_texts/{magic_nor}.json'))), links
            ),
            with_links=True,
        )
    )


# if __name__ == '__main__':
# DOC_ID = '39061'
# print(scrap_nor(DOC_ID))

