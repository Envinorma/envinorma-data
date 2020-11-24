from dataclasses import asdict

from lib.aida import (
    _GITHUB_BASE_LOC,
    AIDA_URL,
    Hyperlink,
    extract_hyperlinks,
    extract_anchors,
    aida_link_to_github_link,
)


def test_hyperlinks_extraction():
    input_ = '<div id="content-area"><a href="A">PipA</a> Bonjour <a href="B">PipB</a> <a>No HREF here</a></div>'
    tags = extract_hyperlinks(input_)
    assert len(tags) == 2
    assert any([tag.href == 'A' for tag in tags])
    assert any([tag.href == 'B' for tag in tags])
    assert any([tag.content == 'PipA' for tag in tags])


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
