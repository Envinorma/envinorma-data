import pytest
import json
from dataclasses import asdict

from lib.data import load_arrete_ministeriel
from lib.am_structure_extraction import Link, EnrichedString
from lib.aida import (
    extract_hyperlinks,
    _GITHUB_BASE_LOC,
    add_links_in_enriched_string,
    Hyperlink,
    add_links_to_am,
    extract_anchors,
    aida_link_to_github_link,
    AIDA_URL,
)


def test_hyperlinks_extraction():
    input_ = '<div id="content-area"><a href="A">PipA</a> Bonjour <a href="B">PipB</a> <a>No HREF here</a></div>'
    tags = extract_hyperlinks(input_)
    assert len(tags) == 2
    assert any([tag.href == 'A' for tag in tags])
    assert any([tag.href == 'B' for tag in tags])
    assert any([tag.content == 'PipA' for tag in tags])


def test_link_addition():
    input_str = EnrichedString('This cat is called Pipa. Yes this cat.', [Link('example.com', 0, 4)])
    new_str = add_links_in_enriched_string(input_str, {'cat': 'example.com/cat', 'Pipa.': 'example.com/pipa'})
    assert len(new_str.links) == 4
    assert sum([link.content_size == 3 for link in new_str.links]) == 2
    assert sum([link.content_size == 4 for link in new_str.links]) == 1
    assert sum([link.content_size == 5 for link in new_str.links]) == 1
    assert sum([link.target == 'example.com' for link in new_str.links]) == 1
    assert sum([link.target == 'example.com/cat' for link in new_str.links]) == 2
    assert sum([link.target == 'example.com/pipa' for link in new_str.links]) == 1


_SAMPLE_AM_NOR = ['DEVP1706393A', 'ATEP9760292A', 'DEVP1235896A', 'DEVP1329353A', 'TREP1900331A', 'TREP2013116A']


@pytest.mark.filterwarnings('ignore')
def test_no_fail_in_aida_links_addition():
    for nor in _SAMPLE_AM_NOR:
        links_json = json.load(open(f'data/aida/hyperlinks/{nor}.json'))
        links = [Hyperlink(**link_doc) for link_doc in links_json]
        add_links_to_am(load_arrete_ministeriel(json.load(open(f'data/AM/structured_texts/{nor}.json'))), links)


def test_extract_anchors():
    html = '''
        <div id="content-area">
            <h1>Bonjour</h1>

            <p><a name="nope"></a>Je m'appelle Pipa.</p>

            <h2><a name="et-toi"></a>Et toi ?</h2>

            <h3><a href="example.com">Bye.</a></h3>
        </div>
    '''
    anchors = extract_anchors(html)
    assert len(anchors) == 1
    assert anchors[0].anchored_text == 'Et toi ?'
    assert anchors[0].name == 'et-toi'


def test_aida_link_to_github_link():
    pairs = [
        (
            aida_link_to_github_link(Hyperlink('Bonjour', AIDA_URL + '1234'), {}, 'NOR2', {'1234': 'NOR1'}),
            asdict(Hyperlink(content='Bonjour', href=f'{_GITHUB_BASE_LOC}/NOR1.md')),
        ),
        (aida_link_to_github_link(Hyperlink('Bonjour', AIDA_URL + '1234'), {}, 'NOR1', {'1234': 'NOR1'}), None),
        (aida_link_to_github_link(Hyperlink('Bonjour', AIDA_URL + '1234#1'), {}, 'NOR1', {'1234': 'NOR1'}), None),
        (
            aida_link_to_github_link(
                Hyperlink('Bonjour', AIDA_URL + '1234#1'), {'1': 'annexe-1'}, 'NOR1', {'1234': 'NOR1'}
            ),
            asdict(Hyperlink(content='Bonjour', href='#annexe-1')),
        ),
        (
            aida_link_to_github_link(
                Hyperlink('Bonjour', AIDA_URL + '1234#1'), {'1': 'annexe-1'}, 'NOR2', {'1234': 'NOR1'}
            ),
            asdict(Hyperlink(content='Bonjour', href=f'{_GITHUB_BASE_LOC}/NOR1.md#annexe-1')),
        ),
        (
            aida_link_to_github_link(
                Hyperlink('Bonjour', AIDA_URL + '1234#2'), {'1': 'annexe-1'}, 'NOR2', {'1234': 'NOR1'}
            ),
            None,
        ),
    ]
    for computed, expected in pairs:
        assert (asdict(computed) if computed else None) == expected
