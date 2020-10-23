import json
from scripts.AM_structure_extraction import Link, EnrichedString, transform_arrete_ministeriel
from scripts.aida import extract_hyperlinks, add_links_in_enriched_string, Hyperlink, add_aida_links, extract_anchors


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


_SAMPLE_AM_NOR = ['DEVP1706393A', 'TREP1815737A', 'ATEP9870263A', 'DEVP1519168A', 'DEVP1430916A', 'DEVP1001990A']


def test_no_fail_in_aida_links_addition():
    page_id_to_links = json.load(open('data/aida/hyperlinks/page_id_to_links.json'))
    arretes_ministeriels = json.load(open('data/AM/arretes_ministeriels.json'))
    nor_to_page_id = {
        doc['nor']: doc['aida_page'] for doc in arretes_ministeriels if 'nor' in doc and 'aida_page' in doc
    }
    for nor in _SAMPLE_AM_NOR:
        aida_page = nor_to_page_id[nor]
        links = [Hyperlink(**link_doc) for link_doc in page_id_to_links[aida_page]]
        add_aida_links(transform_arrete_ministeriel(json.load(open(f'data/AM/legifrance_texts/{nor}.json'))), links)


def text_extract_anchors():
    html = '''
        <h1>Bonjour<h1>

        <p><a name='nope'></a>Je m'appelle Pipa.</p>

        <h2><a name='et-toi'></a>Et toi ?</h2>
        
        <h3><a href='example.com'>Bye.</a></h2>

    '''
    anchors = extract_anchors(html)
    assert len(anchors) == 1
    assert anchors[0].anchored_text == 'Et toi ?'
    assert anchors[0].name == 'et-toi'
