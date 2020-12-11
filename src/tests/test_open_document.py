import bs4
from lib.data import Table
from bs4 import BeautifulSoup
from lib.open_document import (
    ODFTitle,
    _extract_title,
    _extract_string_from_tag,
    _extract_cell,
    _extract_cells,
    _extract_rows,
    _extract_table,
    _extract_flattened_elements,
    _build_enriched_alineas,
    _extract_highest_title_level,
    _build_structured_text,
    _build_structured_text_from_soup,
    _extract_tag_from_soup,
    _remove_last_line_break,
    _merge_children,
)

_XML_PREFIX = '''<?xml version="1.0" encoding="utf-8"?>
<office:document-content office:version="1.2" xmlns:chart="urn:oasis:names:tc:opendocument:xmlns:chart:1.0" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dom="http://www.w3.org/2001/xml-events" xmlns:dr3d="urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:field="urn:openoffice:names:experimental:ooo-ms-interop:xmlns:field:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:form="urn:oasis:names:tc:opendocument:xmlns:form:1.0" xmlns:grddl="http://www.w3.org/2003/g/data-view#" xmlns:math="http://www.w3.org/1998/Math/MathML" xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" xmlns:number="urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0" xmlns:of="urn:oasis:names:tc:opendocument:xmlns:of:1.2" xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:ooo="http://openoffice.org/2004/office" xmlns:oooc="http://openoffice.org/2004/calc" xmlns:ooow="http://openoffice.org/2004/writer" xmlns:rpt="http://openoffice.org/2005/report" xmlns:script="urn:oasis:names:tc:opendocument:xmlns:script:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:tableooo="http://openoffice.org/2009/table" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:textooo="http://openoffice.org/2013/office" xmlns:xforms="http://www.w3.org/2002/xforms" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><office:scripts/><office:font-face-decls><style:font-face style:font-family-generic="roman" style:font-pitch="variable" style:name="Times New Roman" svg:font-family="'Times New Roman'"/><style:font-face style:font-family-generic="swiss" style:font-pitch="variable" style:name="Arial" svg:font-family="Arial"/><style:font-face style:font-family-generic="system" style:font-pitch="variable" style:name="Arial Unicode MS" svg:font-family="'Arial Unicode MS'"/></office:font-face-decls><office:automatic-styles><style:style style:family="table" style:name="Tableau1"><style:table-properties style:width="17cm" table:align="margins"/></style:style><style:style style:family="table-column" style:name="Tableau1.A"><style:table-column-properties style:column-width="4.251cm" style:rel-column-width="16383*"/></style:style><style:style style:family="table-cell" style:name="Tableau1.A1"><style:table-cell-properties fo:border-bottom="0.002cm solid #000000" fo:border-left="0.002cm solid #000000" fo:border-right="none" fo:border-top="0.002cm solid #000000" fo:padding="0.097cm"/></style:style><style:style style:family="table-cell" style:name="Tableau1.D1"><style:table-cell-properties fo:border="0.002cm solid #000000" fo:padding="0.097cm"/></style:style><style:style style:family="table-cell" style:name="Tableau1.A2"><style:table-cell-properties fo:border-bottom="0.002cm solid #000000" fo:border-left="0.002cm solid #000000" fo:border-right="none" fo:border-top="none" fo:padding="0.097cm"/></style:style><style:style style:family="table-cell" style:name="Tableau1.D2"><style:table-cell-properties fo:border-bottom="0.002cm solid #000000" fo:border-left="0.002cm solid #000000" fo:border-right="0.002cm solid #000000" fo:border-top="none" fo:padding="0.097cm"/></style:style></office:automatic-styles><office:body><office:text>'''
_XML_SUFFIX = '''</office:text></office:body></office:document-content>'''


def _add_prefix_and_suffix(xml: str) -> str:
    return f'{_XML_PREFIX}{xml}{_XML_SUFFIX}'


def _get_soup(xml: str) -> bs4.Tag:
    return list(BeautifulSoup(_add_prefix_and_suffix(xml), 'lxml-xml').find('office:text').children)[0]


def test_extract_title():
    xml = '''<text:h text:style-name="Heading_20_3" text:outline-level="3">
<text:bookmark text:name="1.2.2 plan du site"/>
<text:bookmark-start text:name="__RefHeading__4537_1039603210"/>
<text:s/>Situation de l’établissement<text:bookmark-end text:name="__RefHeading__4537_1039603210"/>
</text:h>'''
    soup = _get_soup(xml)
    title = _extract_title(soup)
    assert title.text == 'Situation de l’établissement'
    assert title.level == 3

    xml = '''<text:h text:style-name="Heading_20_1" text:outline-level="1">Test</text:h>'''
    soup = _get_soup(xml)
    title = _extract_title(soup)
    assert title.text == 'Test'
    assert title.level == 1


def test_extract_string_from_tag():
    xml = (
        '''<text:span><text:p text:style-name="P667">le bassin de réserve d’eaux incendie ;</text:p>'''
        '''<text:p text:style-name="P667">les aires de stationnement des engins pompes et de mise en station des moyens élévateurs aériens ;</text:p></text:span>'''
    )
    text = _extract_string_from_tag(_get_soup(xml))
    expected = '''le bassin de réserve d’eaux incendie ;
les aires de stationnement des engins pompes et de mise en station des moyens élévateurs aériens ;'''
    assert text == expected


def test_remove_last_line_break():
    assert _remove_last_line_break('test\n') == 'test'
    assert _remove_last_line_break('test') == 'test'
    assert _remove_last_line_break('') == ''


def test_extract_cell():
    xml = '''<table:table-cell table:style-name="Tableau1.A2" table:number-rows-spanned="2" office:value-type="string">
<text:p text:style-name="Table_20_Contents">Fusion in column</text:p>
</table:table-cell>
'''
    cell = _extract_cell(_get_soup(xml))
    assert cell
    assert cell.colspan == 1
    assert cell.rowspan == 2
    assert cell.content.text == 'Fusion in column'

    xml = '''<table:table-cell table:style-name="Tableau1.A2" table:number-rows-spanned="2" table:number-columns-spanned="2" office:value-type="string">
<text:p text:style-name="Table_20_Contents">Fusion in both</text:p><text:p> column and row</text:p>
</table:table-cell>
'''
    cell = _extract_cell(_get_soup(xml))
    assert cell
    assert cell.colspan == 2
    assert cell.rowspan == 2
    assert cell.content.text == 'Fusion in both\ncolumn and row'


def test_extract_cells():
    xml_0 = '''<table:table-cell table:style-name="Tableau1.A2" table:number-rows-spanned="2" table:number-columns-spanned="2" office:value-type="string">
<text:p text:style-name="Table_20_Contents">Fusion in both</text:p><text:p> column and row</text:p>
</table:table-cell>
'''
    xml_1 = '<table:covered-table-cell/>'
    cells = _extract_cells([_get_soup(xml_0), _get_soup(xml_1)])
    assert len(cells) == 1
    cell = cells[0]
    assert cell.colspan == 2
    assert cell.rowspan == 2
    assert cell.content.text == 'Fusion in both\ncolumn and row'


def test_extract_row():
    xml = (
        '<table:table-header-rows>'
        '<table:table-row>'
        '<table:table-cell table:style-name="Tableau1.A1" office:value-type="string">'
        '<text:p text:style-name="Table_20_Heading">A</text:p>'
        '</table:table-cell>'
        '<table:table-cell table:style-name="Tableau1.A1" office:value-type="string">'
        '<text:p text:style-name="Table_20_Heading">B</text:p>'
        '</table:table-cell>'
        '<table:table-cell table:style-name="Tableau1.A1" office:value-type="string">'
        '<text:p text:style-name="Table_20_Heading">C</text:p>'
        '</table:table-cell>'
        '<table:table-cell table:style-name="Tableau1.D1" office:value-type="string">'
        '<text:p text:style-name="Table_20_Heading">D</text:p>'
        '</table:table-cell>'
        '</table:table-row>'
        '</table:table-header-rows>'
    )
    rows = _extract_rows(_get_soup(xml))
    assert len(rows) == 1
    assert len(rows[0].cells) == 4
    assert rows[0].is_header


def test_extract_table():
    xml = (
        '<table:table table:name="Tableau1" table:style-name="Tableau1">'
        '<table:table-column table:style-name="Tableau1.A" table:number-columns-repeated="4"/>'
        '<table:table-header-rows>'
        '<table:table-row>'
        '<table:table-cell table:style-name="Tableau1.A1" office:value-type="string">'
        '<text:p text:style-name="Table_20_Heading">A</text:p>'
        '</table:table-cell>'
        '<table:table-cell table:style-name="Tableau1.A1" office:value-type="string">'
        '<text:p text:style-name="Table_20_Heading">B</text:p>'
        '</table:table-cell>'
        '</table:table-row>'
        '</table:table-header-rows>'
        '<table:table-row>'
        '<table:table-cell table:style-name="Tableau1.A2" table:number-rows-spanned="2" office:value-type="string">'
        '<text:p text:style-name="Table_20_Contents">Fusion in column</text:p>'
        '</table:table-cell>'
        '<table:table-cell table:style-name="Tableau1.A2" office:value-type="string">'
        '<text:p text:style-name="Table_20_Contents"/>'
        '</table:table-cell>'
        '</table:table-row>'
        '<table:table-row>'
        '<table:covered-table-cell/>'
        '<table:table-cell table:style-name="Tableau1.A2" office:value-type="string">'
        '<text:p text:style-name="Table_20_Contents"/>'
        '</table:table-cell>'
        '</table:table-row>'
        '</table:table>'
    )
    table = _extract_table(_get_soup(xml))
    assert len(table.rows) == 3
    assert table.rows[0].is_header
    assert not table.rows[1].is_header
    assert not table.rows[2].is_header
    assert len(table.rows[1].cells) == 2
    assert len(table.rows[2].cells) == 1
    assert table.rows[2].cells[0].content.text == ''


def test_extract_flattened_elements():
    xml = (
        '''<text:span>'''
        '''<text:p>'''
        '''<text:list>'''
        '''<text:list-item>'''
        '''<text:p text:style-name="P667">les différents dispositifs de lutte contre l’incendie (RIA…) ;</text:p>'''
        '''</text:list-item>'''
        '''<text:list-item>'''
        '''<text:p text:style-name="P668">les organes de coupure des installations électrique du site ;</text:p>'''
        '''</text:list-item>'''
        '''<text:list-item>'''
        '''<text:p text:style-name="P669">toutes informations complémentaires demandées par les services d’incendie et de secours.</text:p>'''
        '''</text:list-item>'''
        '''</text:list>'''
        '''<text:p text:style-name="P401"/>'''
        '''<text:h text:style-name="P688" text:outline-level="2">'''
        '''<text:bookmark-start text:name="__RefHeading__4845_1039603210"/>Dispositions constructives<text:bookmark-end text:name="__RefHeading__4845_1039603210"/>'''
        '''</text:h>'''
        '''<text:h text:style-name="P719" text:outline-level="3">'''
        '''<text:bookmark-start text:name="__RefHeading__4847_1039603210"/>'''
        '''<text:bookmark text:name="8.3.1 explosion"/>'''
        '''<text:s/>Comportement au feu<text:bookmark-end text:name="__RefHeading__4847_1039603210"/>'''
        '''</text:h>'''
        '''<text:p text:style-name="P67">Les bâtiments et locaux sont conçus et aménagés de façon à pouvoir détecter rapidement un départ d'incendie et s'opposer à la propagation d'un incendie.</text:p>'''
        '''<text:p text:style-name="P67"/>'''
        '''<text:p text:style-name="P209">Les bâtiments ou locaux susceptibles d’être l’objet d’une explosion sont suffisamment éloignés des autres bâtiments et unités de l’installation, ou protégés en conséquence. <text:span text:style-name="T90">L’installation de dépoussiérage est munie d’une surface anti-déflagrante, d’un dôme d’explosion, de ventilateurs anti-déflagrants et d’un système anti-étincelle</text:span>'''
        '''<text:span text:style-name="T467">. Avant broyage, une vérification visuelle de l’absence de déchets suspects (bouteille de gaz non vide…) est réalisée par le grutier ou une autre personne qui est formée en conséquence.</text:span>'''
        '''</text:p>'''
        '''</text:p>'''
        '''</text:span>'''
    )
    elements = _extract_flattened_elements(_get_soup(xml))
    assert len(elements) == 7
    assert isinstance(elements[0], str)
    assert elements[0] == '- les différents dispositifs de lutte contre l’incendie (RIA…) ;'


def test_extract_flattened_elements_2():
    xml = (
        '''<text:p text:style-name="P406">'''
        '''<text:span text:style-name="T301">A</text:span>'''
        '''<text:span text:style-name="T300">rrêté préfectoral d’autorisation </text:span>'''
        '''<text:span text:style-name="T301">relatif </text:span>'''
        '''</text:p>'''
    )
    elements = _extract_flattened_elements(_get_soup(xml))
    assert len(elements) == 1
    assert isinstance(elements[0], str)
    assert elements[0] == 'Arrêté préfectoral d’autorisation relatif '


def test_extract_flattened_elements_3():
    xml = (
        '''<text:p text:style-name="P584">'''
        '''Dans le présent arrêté, le terme VHU désigne un véhicule hors d’usage'''
        '''<text:span text:style-name="T279">'''
        '''que son détenteur remet à un tiers pour qu'il le détruise ou qu'il a l'obligation de détruire'''
        '''</text:span>'''
        '''<text:span text:style-name="T280">'''
        '''('''
        '''</text:span>'''
        '''<text:span text:style-name="T281">'''
        '''article'''
        '''</text:span>'''
        '''<text:span text:style-name="T280">'''
        '''R. 543-154 du CE).'''
        '''</text:span>'''
        '''<text:span text:style-name="T284">'''
        '''Le terme « VHU » couvre les voitures particulières, les camionnettes et les cyclomoteurs à trois roues et par extension, pour cet établissement, les poids lourds, les caravanes, les remorques et les cylomoteurs.'''
        '''</text:span>'''
        '''</text:p>'''
    )
    elements = _extract_flattened_elements(_get_soup(xml))
    assert len(elements) == 1
    assert isinstance(elements[0], str)

    xml = '''<text:p text:style-name="P584">Dans le présent arrêté, le terme VHU désigne un véhicule hors d’usage <text:span text:style-name="T279">que son détenteur remet à un tiers pour qu' il le détruise ou qu' il a l' obligation de détruire </text:span><text:span text:style-name="T280">(</text:span><text:span text:style-name="T281">article </text:span><text:span text:style-name="T280">R. 543-154 du CE). </text:span><text:span text:style-name="T284">Le terme « VHU » couvre les voitures particulières, les camionnettes et les cyclomoteurs à trois roues et par extension, pour cet établissement, les poids lourds, les caravanes, les remorques et les cylomoteurs.</text:span></text:p>'''
    elements = _extract_flattened_elements(_get_soup(xml))
    assert len(elements) == 1
    assert isinstance(elements[0], str)
    assert (
        elements[0]
        == '''Dans le présent arrêté, le terme VHU désigne un véhicule hors d’usage que son détenteur remet à un tiers pour qu' il le détruise ou qu' il a l' obligation de détruire (article R. 543-154 du CE). Le terme « VHU » couvre les voitures particulières, les camionnettes et les cyclomoteurs à trois roues et par extension, pour cet établissement, les poids lourds, les caravanes, les remorques et les cylomoteurs.'''
    )


def test_extract_flattened_elements_4():
    xml = '''<text:p><text:span text:style-name="T284">subi les opérations de dépollution figurant en </text:span><text:bookmark-start text:name="a"/><text:span text:style-name="T284">annexe II</text:span><text:bookmark-end text:name="a"/><text:span text:style-name="T284"> du présent arrêté</text:span></text:p>'''
    elements = _extract_flattened_elements(_get_soup(xml))
    assert len(elements) == 1
    assert isinstance(elements[0], str)
    assert elements[0] == 'subi les opérations de dépollution figurant en annexe II du présent arrêté'


def test_build_enriched_alineas():
    assert _build_enriched_alineas(['Hello'])[0][0].text == 'Hello'
    assert _build_enriched_alineas([Table([])])[0][0].table.rows == []


def test_extract_highest_title_level():
    assert _extract_highest_title_level([]) == -1
    assert _extract_highest_title_level([Table([])]) == -1
    assert _extract_highest_title_level([Table([]), ODFTitle('', 1)]) == 1


def test_build_structured_text():
    elements = [Table([]), ODFTitle('title', 1)]
    result = _build_structured_text('', elements)
    assert result.title.text == ''
    assert len(result.outer_alineas) == 1
    assert len(result.sections) == 1
    assert len(result.sections[0].outer_alineas) == 0
    assert len(result.sections[0].sections) == 0
    assert result.sections[0].title.text == 'title'


def test_build_structured_text_from_soup():
    xml = (
        '''<text:span>'''
        '''<text:p>'''
        '''<text:list>'''
        '''<text:list-item>'''
        '''<text:p text:style-name="P667">les différents dispositifs de lutte contre l’incendie (RIA…) ;</text:p>'''
        '''</text:list-item>'''
        '''<text:list-item>'''
        '''<text:p text:style-name="P668">les organes de coupure des installations électrique du site ;</text:p>'''
        '''</text:list-item>'''
        '''<text:list-item>'''
        '''<text:p text:style-name="P669">toutes informations complémentaires demandées par les services d’incendie et de secours.</text:p>'''
        '''</text:list-item>'''
        '''</text:list>'''
        '''<text:p text:style-name="P401"/>'''
        '''<text:h text:style-name="P688" text:outline-level="2">'''
        '''<text:bookmark-start text:name="__RefHeading__4845_1039603210"/>Dispositions constructives<text:bookmark-end text:name="__RefHeading__4845_1039603210"/>'''
        '''</text:h>'''
        '''<text:h text:style-name="P719" text:outline-level="3">'''
        '''<text:bookmark-start text:name="__RefHeading__4847_1039603210"/>'''
        '''<text:bookmark text:name="8.3.1 explosion"/>'''
        '''<text:s/>Comportement au feu<text:bookmark-end text:name="__RefHeading__4847_1039603210"/>'''
        '''</text:h>'''
        '''<text:p text:style-name="P67">Les bâtiments et locaux sont conçus et aménagés de façon à pouvoir détecter rapidement un départ d'incendie et s'opposer à la propagation d'un incendie.</text:p>'''
        '''<text:p text:style-name="P67"/>'''
        '''<text:p text:style-name="P209">Les bâtiments ou locaux susceptibles d’être l’objet d’une explosion sont suffisamment éloignés des autres bâtiments et unités de l’installation, ou protégés en conséquence. <text:span text:style-name="T90">L’installation de dépoussiérage est munie d’une surface anti-déflagrante, d’un dôme d’explosion, de ventilateurs anti-déflagrants et d’un système anti-étincelle</text:span>'''
        '''<text:span text:style-name="T467">. Avant broyage, une vérification visuelle de l’absence de déchets suspects (bouteille de gaz non vide…) est réalisée par le grutier ou une autre personne qui est formée en conséquence.</text:span>'''
        '''</text:p>'''
        '''</text:p>'''
        '''</text:span>'''
    )
    text = _build_structured_text_from_soup(_get_soup(xml))
    assert len(text.sections) == 1
    assert text.title.text == ''
    assert len(text.sections[0].sections) == 1
    assert text.sections[0].title.text == '1. Dispositions constructives'
    assert len(text.sections[0].sections[0].sections) == 0
    assert text.sections[0].sections[0].title.text == '1.1. Comportement au feu'


def test_build_structured_text_from_soup_2():
    xml = (
        '''<text:p text:style-name="P584">'''
        '''Dans le présent arrêté, le terme VHU désigne un véhicule hors d’usage '''
        '''<text:span text:style-name="T279">'''
        '''que son détenteur remet à un tiers pour qu'il le détruise ou qu'il a l'obligation de détruire '''
        '''</text:span>'''
        '''<text:span text:style-name="T280">'''
        '''('''
        '''</text:span>'''
        '''<text:span text:style-name="T281">'''
        '''article '''
        '''</text:span>'''
        '''<text:span text:style-name="T280">'''
        '''R. 543-154 du CE).'''
        '''</text:span>'''
        '''<text:span text:style-name="T284">'''
        ''' Le terme « VHU » couvre les voitures particulières, les camionnettes et les cyclomoteurs à trois roues et par extension, pour cet établissement, les poids lourds, les caravanes, les remorques et les cylomoteurs.'''
        '''</text:span>'''
        '''</text:p>'''
    )
    text = _build_structured_text_from_soup(_get_soup(xml))
    assert len(text.sections) == 0
    assert text.title.text == ''
    expected = '''Dans le présent arrêté, le terme VHU désigne un véhicule hors d’usage que son détenteur remet à un tiers pour qu'il le détruise ou qu'il a l'obligation de détruire (article R. 543-154 du CE). Le terme « VHU » couvre les voitures particulières, les camionnettes et les cyclomoteurs à trois roues et par extension, pour cet établissement, les poids lourds, les caravanes, les remorques et les cylomoteurs.'''
    assert len(text.outer_alineas) == 1
    assert text.outer_alineas[0].text == expected


def test_extract_tag_from_soup():
    tag = _extract_tag_from_soup(BeautifulSoup('<text></text>', 'lxml-xml'))
    assert tag.name == 'text'


def test_merge_children():
    assert _merge_children([['test']], [True]) == ['test']
    assert _merge_children([['test'], ['test 2']], [True, True]) == ['testtest 2']
    assert _merge_children([['test'], ['test 2'], ['test 3']], [True, True, True]) == ['testtest 2test 3']
    assert _merge_children([['test'], ['test 2'], ['test 3']], [True, True, False]) == ['testtest 2', 'test 3']
    assert _merge_children([['test'], ['test 2', 'test 3']], [True, True]) == ['test', 'test 2', 'test 3']
    assert _merge_children([['test'], ['test 2']], [True, False]) == ['test', 'test 2']
    table = Table([])
    assert _merge_children([['test'], [table]], [True, True]) == ['test', table]
