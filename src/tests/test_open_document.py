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
    _transform_odt,
    _load_and_transform,
)


def test_extract_title():
    xml = '''<text:h text:style-name="Heading_20_3" text:outline-level="3">
<text:bookmark text:name="1.2.2 plan du site"/>
<text:bookmark-start text:name="__RefHeading__4537_1039603210"/>
<text:s/>Situation de l’établissement<text:bookmark-end text:name="__RefHeading__4537_1039603210"/>
</text:h>'''
    title = _extract_title(BeautifulSoup(xml, 'lxml-xml'))
    assert title.text == 'Situation de l’établissement'
    assert title.level == 3

    xml = '''<text:h text:style-name="Heading_20_1" text:outline-level="1">Test</text:h>'''
    title = _extract_title(BeautifulSoup(xml, 'lxml-xml'))
    assert title.text == 'Test'
    assert title.level == 1


def test_extract_string_from_tag():
    xml = '''<text:p text:style-name="P667">le bassin de réserve d’eaux incendie ;</text:p>
<text:p text:style-name="P667">les aires de stationnement des engins pompes et de mise en station des moyens élévateurs aériens ;</text:p>
'''
    text = _extract_string_from_tag(BeautifulSoup(xml, 'lxml-xml'))
    expected = '''
le bassin de réserve d’eaux incendie ;
les aires de stationnement des engins pompes et de mise en station des moyens élévateurs aériens ;
'''
    assert text == expected


def test_extract_cell():
    xml = '''<table:table-cell table:style-name="Tableau1.A2" table:number-rows-spanned="2" office:value-type="string">
<text:p text:style-name="Table_20_Contents">Fusion in column</text:p>
</table:table-cell>
'''
    cell = _extract_cell(BeautifulSoup(xml, 'lxml-xml'))
    assert cell
    assert cell.colspan == 2
    assert cell.rowspan == 1
    assert cell.content.text == 'Fusion in column'

    xml = '''<table:table-cell table:style-name="Tableau1.A2" table:number-rows-spanned="2" table:number-columns-spanned="2" office:value-type="string">
<text:p text:style-name="Table_20_Contents">Fusion in both</text:p><text:p> column and row</text:p>
</table:table-cell>
'''
    cell = _extract_cell(BeautifulSoup(xml, 'lxml-xml'))
    assert cell
    assert cell.colspan == 2
    assert cell.rowspan == 2
    assert cell.content.text == 'Fusion in both\n column and row'


def test_extract_cells():
    xml_0 = '''<table:table-cell table:style-name="Tableau1.A2" table:number-rows-spanned="2" table:number-columns-spanned="2" office:value-type="string">
<text:p text:style-name="Table_20_Contents">Fusion in both</text:p><text:p> column and row</text:p>
</table:table-cell>
'''
    xml_1 = '<table:covered-table-cell/>'
    cells = _extract_cells([BeautifulSoup(xml_0, 'lxml-xml'), BeautifulSoup(xml_1, 'lxml-xml')])
    assert len(cells) == 0
    cell = cells[0]
    assert cell.colspan == 2
    assert cell.rowspan == 2
    assert cell.content.text == 'Fusion in both\n column and row'


def test_extract_row():
    xml = '''
<table:table-header-rows>
<table:table-row>
<table:table-cell table:style-name="Tableau1.A1" office:value-type="string">
<text:p text:style-name="Table_20_Heading">A</text:p>
</table:table-cell>
<table:table-cell table:style-name="Tableau1.A1" office:value-type="string">
<text:p text:style-name="Table_20_Heading">B</text:p>
</table:table-cell>
<table:table-cell table:style-name="Tableau1.A1" office:value-type="string">
<text:p text:style-name="Table_20_Heading">C</text:p>
</table:table-cell>
<table:table-cell table:style-name="Tableau1.D1" office:value-type="string">
<text:p text:style-name="Table_20_Heading">D</text:p>
</table:table-cell>
</table:table-row>
</table:table-header-rows>
'''
    rows = _extract_rows(BeautifulSoup(xml, 'lxml-xml'))
    assert len(rows) == 1
    assert len(rows[0].cells) == 4
    assert rows[0].is_header


def test_extract_table():
    xml = '''
<table:table table:name="Tableau1" table:style-name="Tableau1">
<table:table-column table:style-name="Tableau1.A" table:number-columns-repeated="4"/>
<table:table-header-rows>
<table:table-row>
<table:table-cell table:style-name="Tableau1.A1" office:value-type="string">
<text:p text:style-name="Table_20_Heading">A</text:p>
</table:table-cell>
<table:table-cell table:style-name="Tableau1.A1" office:value-type="string">
<text:p text:style-name="Table_20_Heading">B</text:p>
</table:table-cell>
</table:table-row>
</table:table-header-rows>
<table:table-row>
<table:table-cell table:style-name="Tableau1.A2" table:number-rows-spanned="2" office:value-type="string">
<text:p text:style-name="Table_20_Contents">Fusion in column</text:p>
</table:table-cell>
<table:table-cell table:style-name="Tableau1.A2" office:value-type="string">
<text:p text:style-name="Table_20_Contents"/>
</table:table-cell>
</table:table-row>
<table:table-row>
<table:covered-table-cell/>
<table:table-cell table:style-name="Tableau1.A2" office:value-type="string">
<text:p text:style-name="Table_20_Contents"/>
</table:table-cell>
</table:table-row>
</table:table>
'''
    table = _extract_table(BeautifulSoup(xml, 'lxml-xml'))
    assert len(table.rows) == 3
    assert table.rows[0].is_header
    assert not table.rows[1].is_header
    assert not table.rows[2].is_header
    assert len(table.rows[2].cells) == 2
    assert table.rows[2].cells[0].content.text == ''


def test_extract_flattened_elements():
    xml = '''
<text:p>
<text:list>
<text:list-item>
<text:p text:style-name="P667">les différents dispositifs de lutte contre l’incendie (RIA…) ;</text:p>
</text:list-item>
<text:list-item>
<text:p text:style-name="P668">les organes de coupure des installations électrique du site ;</text:p>
</text:list-item>
<text:list-item>
<text:p text:style-name="P669">toutes informations complémentaires demandées par les services d’incendie et de secours.</text:p>
</text:list-item>
</text:list>
<text:p text:style-name="P401"/>
<text:h text:style-name="P688" text:outline-level="2">
<text:bookmark-start text:name="__RefHeading__4845_1039603210"/>Dispositions constructives<text:bookmark-end text:name="__RefHeading__4845_1039603210"/>
</text:h>
<text:h text:style-name="P719" text:outline-level="3">
<text:bookmark-start text:name="__RefHeading__4847_1039603210"/>
<text:bookmark text:name="8.3.1 explosion"/>
<text:s/>Comportement au feu<text:bookmark-end text:name="__RefHeading__4847_1039603210"/>
</text:h>
<text:p text:style-name="P67">Les bâtiments et locaux sont conçus et aménagés de façon à pouvoir détecter rapidement un départ d'incendie et s'opposer à la propagation d'un incendie.</text:p>
<text:p text:style-name="P67"/>
<text:p text:style-name="P209">Les bâtiments ou locaux susceptibles d’être l’objet d’une explosion sont suffisamment éloignés des autres bâtiments et unités de l’installation, ou protégés en conséquence. <text:span text:style-name="T90">L’installation de dépoussiérage est munie d’une surface anti-déflagrante, d’un dôme d’explosion, de ventilateurs anti-déflagrants et d’un système anti-étincelle</text:span>
<text:span text:style-name="T467">. Avant broyage, une vérification visuelle de l’absence de déchets suspects (bouteille de gaz non vide…) est réalisée par le grutier ou une autre personne qui est formée en conséquence.</text:span>
</text:p>
</text:p>
'''
    elements = _extract_flattened_elements(BeautifulSoup(xml, 'lxml-xml'))
    assert len(elements) == 10
    assert isinstance(elements[0], str)
    assert elements[0] == '- les différents dispositifs de lutte contre l’incendie (RIA…) ;'


def test_build_enriched_alineas():
    assert _build_enriched_alineas(['Hello'])[0].text == 'Hello'
    assert _build_enriched_alineas([Table([])])[0].table.rows == []


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
    xml = '''
<text:p>
<text:list>
<text:list-item>
<text:p text:style-name="P667">les différents dispositifs de lutte contre l’incendie (RIA…) ;</text:p>
</text:list-item>
<text:list-item>
<text:p text:style-name="P668">les organes de coupure des installations électrique du site ;</text:p>
</text:list-item>
<text:list-item>
<text:p text:style-name="P669">toutes informations complémentaires demandées par les services d’incendie et de secours.</text:p>
</text:list-item>
</text:list>
<text:p text:style-name="P401"/>
<text:h text:style-name="P688" text:outline-level="2">
<text:bookmark-start text:name="__RefHeading__4845_1039603210"/>Dispositions constructives<text:bookmark-end text:name="__RefHeading__4845_1039603210"/>
</text:h>
<text:h text:style-name="P719" text:outline-level="3">
<text:bookmark-start text:name="__RefHeading__4847_1039603210"/>
<text:bookmark text:name="8.3.1 explosion"/>
<text:s/>Comportement au feu<text:bookmark-end text:name="__RefHeading__4847_1039603210"/>
</text:h>
<text:p text:style-name="P67">Les bâtiments et locaux sont conçus et aménagés de façon à pouvoir détecter rapidement un départ d'incendie et s'opposer à la propagation d'un incendie.</text:p>
<text:p text:style-name="P67"/>
<text:p text:style-name="P209">Les bâtiments ou locaux susceptibles d’être l’objet d’une explosion sont suffisamment éloignés des autres bâtiments et unités de l’installation, ou protégés en conséquence. <text:span text:style-name="T90">L’installation de dépoussiérage est munie d’une surface anti-déflagrante, d’un dôme d’explosion, de ventilateurs anti-déflagrants et d’un système anti-étincelle</text:span>
<text:span text:style-name="T467">. Avant broyage, une vérification visuelle de l’absence de déchets suspects (bouteille de gaz non vide…) est réalisée par le grutier ou une autre personne qui est formée en conséquence.</text:span>
</text:p>
</text:p>
'''
    text = _build_structured_text_from_soup(BeautifulSoup(xml, 'lxml-xml'))
    assert len(text.sections) == 1
    assert text.title.text == ''
    assert len(text.sections[0].sections) == 1
    assert text.sections[0].title.text == 'Dispositions constructives'
    assert len(text.sections[0].sections[0].sections) == 0
    assert text.sections[0].sections[0].title.text == 'Comportement au feu'


def test_extract_tag_from_soup():
    _extract_tag_from_soup(BeautifulSoup('<text></text>', 'lxml-xml')).name == 'text'
