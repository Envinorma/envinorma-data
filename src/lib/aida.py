import json
import re
from collections import defaultdict
from typing import Any, DefaultDict, Dict, List, Set, Optional, Tuple

import requests
from bs4 import BeautifulSoup, Tag
from tqdm import tqdm

from lib.data import Hyperlink, Anchor
from lib.config import AIDA_URL, AM_DATA_FOLDER

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
    response = requests.get(AIDA_URL + document_id)
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
    url = AIDA_URL + '{}'
    return url.format(f'{document_id}{tmp_str}' if starts_with_hash(tmp_str) else tmp_str)


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
    soup = BeautifulSoup(html, 'html.parser')
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
    clean_href = href.replace(AIDA_URL, '')
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
    arretes_ministeriels = json.load(open(f'data/arretes_ministeriels.json'))
    page_ids = [am['aida_page'] for am in arretes_ministeriels]
    page_id_to_anchors_json: Dict[str, List[Dict[str, Any]]] = {}
    for page_id in tqdm(page_ids):
        try:
            page_id_to_anchors_json[page_id] = [anchor.to_dict() for anchor in extract_all_anchors_from_aida(page_id)]
        except Exception as exc:  # pylint: disable=broad-except
            print(exc)
    json.dump(page_id_to_anchors_json, open('data/aida/hyperlinks/page_id_to_anchors.json', 'w'), ensure_ascii=False)
