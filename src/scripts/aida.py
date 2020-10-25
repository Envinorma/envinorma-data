import json
import re
import requests
from bs4 import BeautifulSoup, Tag
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any, DefaultDict, Dict, List, Set, Optional, Tuple
from collections import defaultdict
from scripts.AM_structure_extraction import EnrichedString, Link, StructuredArreteMinisteriel, StructuredText, Article

_AIDA_BASE_URL = 'https://aida.ineris.fr/consultation_document/'
_AIDA_URL = _AIDA_BASE_URL + '{}'
_NOR_REGEXP = r'[A-Z]{4}[0-9]{7}[A-Z]'


def _extract_nor_from_text(text: str) -> str:
    match = re.search(_NOR_REGEXP, text)
    if not match:
        raise ValueError(f'NOR not found in {text}.')
    return text[match.start() : match.end()]


def extract_nor_from_html(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup.find_all('h5'):
        if 'NOR' in tag.text:
            return _extract_nor_from_text(tag.text)
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


def add_links_to_am(text: StructuredArreteMinisteriel, new_hyperlinks: List[Hyperlink]) -> StructuredArreteMinisteriel:
    str_to_target = {link.content: link.href for link in new_hyperlinks}
    return StructuredArreteMinisteriel(
        title=text.title,
        articles=[add_links_in_article(article, str_to_target) for article in text.articles],
        sections=[add_links_in_section(section, str_to_target) for section in text.sections],
        visa=[add_links_in_enriched_string(str_, str_to_target) for str_ in text.visa],
    )


def extract_number_in_the_beginning(str_: str) -> Optional[str]:
    matches = re.findall(r'^[0-9]*', str_)
    if not matches:
        return None
    return matches[0]


def make_github_anchor(str_: str) -> str:
    github_anchor = str_.replace(' ', '-').replace('.', '').lower()
    particular_root = 'article-'
    if github_anchor[: len(particular_root)] != particular_root:  # AIDA adds things in title
        return github_anchor
    article_number = extract_number_in_the_beginning(github_anchor[len(particular_root) :])
    return f'{particular_root}{article_number}' if article_number else github_anchor


def extract_page_and_anchor_from_aida_href(href: str) -> Optional[Tuple[str, Optional[str]]]:
    clean_href = href.replace(_AIDA_BASE_URL, '')
    nb_hash = clean_href.count('#')
    if nb_hash == 0:
        return clean_href, None
    if nb_hash > 1:
        return None
    res = clean_href.split('#')
    return res[0], res[1]


def aida_anchor_to_github_anchor(anchor: Optional[str], aida_to_github_anchor_name: Dict[str, str]) -> Optional[str]:
    new_anchor = ''
    if anchor:
        github_anchor_name = aida_to_github_anchor_name.get(anchor)
        if not github_anchor_name:
            return None
        new_anchor = '#' + github_anchor_name
    return new_anchor


_GITHUB_BASE_LOC = '/src/data/AM/markdown_texts'
_GITHUB_BASE_LOC = ''


def aida_link_to_github_link(
    link: Hyperlink,
    aida_to_github_anchor_name: Dict[str, str],
    current_nor: str,
    aida_page_to_nor: Dict[str, str],
    keep_unknown_aida_links: bool = True,
) -> Optional[Hyperlink]:
    page_and_anchor = extract_page_and_anchor_from_aida_href(link.href)
    if not page_and_anchor:
        return None
    page, anchor = page_and_anchor
    nor = aida_page_to_nor.get(page)
    if not nor and keep_unknown_aida_links:
        return link
    github_page = f'{_GITHUB_BASE_LOC}/{nor}.md' if nor != current_nor else ''
    if not anchor:
        return Hyperlink(href=github_page, content=link.content) if github_page else None
    github_anchor = aida_anchor_to_github_anchor(anchor, aida_to_github_anchor_name)
    if not github_anchor:
        return None
    github_href = f'{github_page}{github_anchor}'
    return Hyperlink(href=github_href, content=link.content) if github_href else None


def transform_aida_links_to_github_markdown_links(
    aida_links: List[Hyperlink], aida_anchors: List[Anchor], current_nor: str, aida_page_to_nor: Dict[str, str]
) -> List[Hyperlink]:
    aida_to_github_anchor_name = {anchor.name: make_github_anchor(anchor.anchored_text) for anchor in aida_anchors}
    candidates = [
        aida_link_to_github_link(link, aida_to_github_anchor_name, current_nor, aida_page_to_nor) for link in aida_links
    ]
    return [link for link in candidates if link]


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


@dataclass
class AMData:
    content: List[Dict[str, Any]]
    nor_to_aida: Dict[str, str]
    aida_to_nor: Dict[str, str]


@dataclass
class AidaData:
    page_id_to_links: Dict[str, List[Hyperlink]]
    page_id_to_anchors: Dict[str, List[Anchor]]


@dataclass
class Data:
    aida: AidaData
    arretes_ministeriels: AMData


def load_am_data() -> AMData:
    arretes_ministeriels = json.load(open('data/AM/arretes_ministeriels.json'))
    nor_to_aida = {doc['nor']: doc['aida_page'] for doc in arretes_ministeriels if 'nor' in doc and 'aida_page' in doc}
    aida_to_nor = {doc['aida_page']: doc['nor'] for doc in arretes_ministeriels if 'nor' in doc and 'aida_page' in doc}
    return AMData(arretes_ministeriels, nor_to_aida, aida_to_nor)


def load_aida_data() -> AidaData:
    page_id_to_links = json.load(open('data/aida/hyperlinks/page_id_to_links.json'))
    page_id_to_anchors = json.load(open('data/aida/hyperlinks/page_id_to_anchors.json'))
    links = {
        aida_page: [Hyperlink(**link_doc) for link_doc in link_docs]
        for aida_page, link_docs in page_id_to_links.items()
    }
    anchors = {
        aida_page: [Anchor(**anchor_doc) for anchor_doc in anchor_docs]
        for aida_page, anchor_docs in page_id_to_anchors.items()
    }
    return AidaData(links, anchors)


def load_data() -> Data:
    return Data(load_aida_data(), load_am_data())


def classement_to_md(classements: List[Dict]) -> str:
    if not classements:
        return ''
    rows = [f"{clss['rubrique']} | {clss['regime']} | {clss.get('alinea') or ''}" for clss in classements]
    return '\n'.join(['Rubrique | Régime | Alinea', '---|---|---'] + rows)


def generate_text_md(text: Dict[str, Any]) -> str:
    nor = text.get('nor')
    page_name = text.get('page_name') or ''
    aida = text.get('aida_page')
    table = classement_to_md(text['classements'])
    return '\n\n'.join(
        [f'## [{nor}](/{nor}.md)', f'_{page_name.strip()}_', f'[sur AIDA]({_AIDA_URL.format(aida)})']
        + ([table] if table else [])
    )


def generate_index(am_data: AMData) -> str:
    return '\n\n---\n\n'.join(
        [generate_text_md(text) for text in sorted(am_data.content, key=lambda x: x.get('nor', 'zzzzz'))]
    )


def generate_nor_markdown(nor: str, data: Data, output_folder: str):
    import json
    from scripts.AM_structure_extraction import am_to_markdown, transform_arrete_ministeriel

    aida_page = data.arretes_ministeriels.nor_to_aida[nor]
    internal_links = transform_aida_links_to_github_markdown_links(
        data.aida.page_id_to_links[aida_page],
        data.aida.page_id_to_anchors[aida_page],
        nor,
        data.arretes_ministeriels.aida_to_nor,
    )
    open(f'{output_folder}/{nor}.md', 'w').write(
        am_to_markdown(
            add_links_to_am(
                transform_arrete_ministeriel(json.load(open(f'data/AM/legifrance_texts/{nor}.json'))), internal_links
            ),
            with_links=True,
        )
    )


def generate_1510_markdown() -> None:
    data = load_data()
    magic_nor = 'DEVP1706393A'
    generate_nor_markdown(magic_nor, data, 'data/AM/markdown_texts')


def generate_all_markdown(output_folder: str = '/Users/remidelbouys/EnviNorma/envinorma.github.io') -> None:
    from tqdm import tqdm

    data = load_data()
    open(f'{output_folder}/index.md', 'w').write(generate_index(data.arretes_ministeriels))

    nors = data.arretes_ministeriels.nor_to_aida.keys()
    for nor in tqdm(nors):
        try:
            generate_nor_markdown(nor, data, output_folder)
        except Exception as exc:
            print(nor, exc)
