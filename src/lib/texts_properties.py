from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Any, Dict, Tuple, Union, List

from lib.am_structure_extraction import (
    ArreteMinisteriel,
    StructuredText,
    LegifranceText,
    LegifranceSection,
    LegifranceArticle,
)


@dataclass
class LegifranceTextProperties:
    structure: str
    nb_articles: int
    nb_non_numerotated_articles: int


def _count_articles(text: Union[LegifranceText, LegifranceSection]) -> int:
    return len(text.articles) + sum([_count_articles(section) for section in text.sections])


def _count_non_numerotated_articles(text: Union[LegifranceText, LegifranceSection]) -> int:
    tmp = len([article for article in text.articles if article.num is not None])
    return tmp + sum([_count_articles(section) for section in text.sections])


def _extract_text_structure(text: Union[LegifranceText, LegifranceSection], prefix: str = '') -> List[str]:
    raw_elts: List[Union[LegifranceArticle, LegifranceSection]] = [*text.articles, *text.sections]
    elts = sorted(raw_elts, key=lambda x: x.intOrdre)
    res: List[str] = []
    for elt in elts:
        if isinstance(elt, LegifranceArticle):
            res += [f'{prefix}Article {elt.num}']
        elif isinstance(elt, LegifranceSection):
            res += [(f'{prefix}Section {elt.title}')] + _extract_text_structure(elt, f'|--{prefix}')
        else:
            raise ValueError('')
    return res


def _extract_article_nums(text: Union[LegifranceText, LegifranceSection]) -> List[str]:
    raw_elts: List[Union[LegifranceArticle, LegifranceSection]] = [*text.articles, *text.sections]
    elts = sorted(raw_elts, key=lambda x: x.intOrdre)
    res: List[str] = []
    for elt in elts:
        if isinstance(elt, LegifranceArticle):
            res.append(str(elt.num))
        elif isinstance(elt, LegifranceSection):
            res.extend(['|'] + _extract_article_nums(elt) + ['|'])
    return res


def _extract_sorted_articles(text: Union[LegifranceText, LegifranceSection]) -> List[LegifranceArticle]:
    raw_elts: List[Union[LegifranceArticle, LegifranceSection]] = [*text.articles, *text.sections]
    elts = sorted(raw_elts, key=lambda x: x.intOrdre)
    res: List[LegifranceArticle] = []
    for elt in elts:
        if isinstance(elt, LegifranceArticle):
            res.append(elt)
        elif isinstance(elt, LegifranceSection):
            res.extend(_extract_sorted_articles(elt))
    return res


def _extract_article_num_list(text: LegifranceText) -> str:
    articles = _extract_sorted_articles(text)
    return '\n'.join([str(article.num) for article in articles])


def _compute_properties(text: LegifranceText) -> LegifranceTextProperties:
    return LegifranceTextProperties(
        '\n'.join(_extract_text_structure(text)), _count_articles(text), _count_non_numerotated_articles(text)
    )


def _html_to_str(html: str) -> str:
    return BeautifulSoup(html, 'html.parser').text


def _get_consecutive_with_one_none(articles: List[LegifranceArticle]) -> List[Tuple[str, str]]:
    previous_is_not_none = False
    pairs: List[Tuple[str, str]] = []
    for i, article in enumerate(articles):
        if article.num is not None:
            previous_is_not_none = True
        else:
            if previous_is_not_none:
                pairs.append((_html_to_str(articles[i - 1].content), _html_to_str(article.content)))
            previous_is_not_none = False
    return pairs


@dataclass
class AMProperties:
    structure: str


def _extract_am_structure(am: Union[ArreteMinisteriel, StructuredText], prefix: str = '') -> List[str]:
    res: List[str] = []
    for section in am.sections:
        res += [(f'{prefix}{section.title.text}')] + _extract_am_structure(section, f'|--{prefix}')
    return res


def _compute_am_properties(am: ArreteMinisteriel) -> AMProperties:
    return AMProperties('\n'.join(_extract_am_structure(am)))

