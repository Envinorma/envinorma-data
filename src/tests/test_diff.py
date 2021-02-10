from lib.diff import (
    AddedLine,
    ModifiedLine,
    RemovedLine,
    TextDifferences,
    UnchangedLine,
    _apply_mask,
    _build_difflines,
    _empty_mask,
    _is_modified_line_consistent,
    _parse_mask,
    build_text_differences,
)


def test_build_text_differences():
    text_1 = [
        'Première ligne',
        'InterLudE',
        'Deuxième ligne',
        'Troisième ligne',
        '4 ligne',
        'cinquième lignee',
        'sixièm ligne',
    ]
    text_2 = [
        'Première ligne',
        'Deuxièmee ligne',
        'Troisième ligns',
        '4 ligne',
        'cinquième lig',
        'sIxième lign',
        'postlude',
    ]
    res = build_text_differences(text_1, text_2)
    expected = TextDifferences(
        diff_lines=[
            UnchangedLine(content='Première ligne'),
            RemovedLine(content='InterLudE'),
            ModifiedLine(
                content_before='Deuxième ligne',
                mask_before=_parse_mask("              "),
                content_after='Deuxièmee ligne',
                mask_after=_parse_mask("        +"),
            ),
            ModifiedLine(
                content_before='Troisième ligne',
                mask_before=_parse_mask("              ^"),
                content_after='Troisième ligns',
                mask_after=_parse_mask("              ^"),
            ),
            UnchangedLine(content='4 ligne'),
            ModifiedLine(
                content_before='cinquième lignee',
                mask_before=_parse_mask("             ---"),
                content_after='cinquième lig',
                mask_after=_parse_mask("                "),
            ),
            ModifiedLine(
                content_before='sixièm ligne',
                mask_before=_parse_mask(" ^         -"),
                content_after='sIxième lign',
                mask_after=_parse_mask(" ^    +"),
            ),
            AddedLine(content='postlude'),
        ]
    )
    assert res == expected


def test_build_difflines():
    input_ = [
        "- ### 43-2-6. Pour les sites nouveaux, les bassins de confinement des eaux d'incendie :",
        '?             ^^^^^^^^^^^^^^^^^^^^^^^^^^\n',
        "+ ### 43-2-6. Les bassins de confinement des eaux d'incendie :",
        '?             ^\n',
        "  -sont implantés hors des zones d'effet thermique d'intensité supérieure à 5 kW/ m2 identifiées dans l'étude de dangers, ou ;",
        "  -sont constitués de matériaux résistant aux effets générés par les accidents identifiés dans l'étude de dangers et susceptibles de conduire à leur emploi.",
        "  ## 43-3. Moyens en eau, émulseurs et taux d'application.",
    ]
    res = _build_difflines(input_)
    assert res == [
        ModifiedLine(
            content_before="### 43-2-6. Pour les sites nouveaux, les bassins de confinement des eaux d'incendie :",
            mask_before=_parse_mask("            ^^^^^^^^^^^^^^^^^^^^^^^^^^"),
            content_after="### 43-2-6. Les bassins de confinement des eaux d'incendie :",
            mask_after=_parse_mask("            ^"),
        ),
        UnchangedLine(
            content="-sont implantés hors des zones d'effet thermique d'intensité supérieure à 5 kW/ m2 identifiées dans l'étude de dangers, ou ;"
        ),
        UnchangedLine(
            content="-sont constitués de matériaux résistant aux effets générés par les accidents identifiés dans l'étude de dangers et susceptibles de conduire à leur emploi."
        ),
        UnchangedLine(content="## 43-3. Moyens en eau, émulseurs et taux d'application."),
    ]

    input_ = [
        '+ Ces personnes sont entraînées à la manœuvre de ces moyens.',
        "- ### 43-2-6. Pour les sites nouveaux, les bassins de confinement des eaux d'incendie :",
        '?             ^^^^^^^^^^^^^^^^^^^^^^^^^^\n',
        "+ ### 43-2-6. Les bassins de confinement des eaux d'incendie :",
        '?             ^\n',
        "  -sont implantés hors des zones d'effet thermique d'intensité supérieure à 5 kW/ m2 identifiées dans l'étude de dangers, ou ;",
        "  -sont constitués de matériaux résistant aux effets générés par les accidents identifiés dans l'étude de dangers et susceptibles de conduire à leur emploi.",
        "  ## 43-3. Moyens en eau, émulseurs et taux d'application.",
    ]
    res = _build_difflines(input_)

    input_ = [
        '  Première ligne',
        '- InterLudE',
        '- Deuxième ligne',
        '+ Deuxièmee ligne',
        '?         +\n',
        '- Troisième ligne',
        '?               ^\n',
        '+ Troisième ligns',
        '?               ^\n',
        '  4 ligne',
        '- cinquième lignee',
        '?              ---\n',
        '+ cinquième lig',
        '- sixièm ligne',
        '?  ^         -\n',
        '+ sIxième lign',
        '?  ^    +\n',
        '+ postlude',
    ]

    assert _build_difflines(input_[:1]) == [UnchangedLine(input_[0][2:])]
    assert _build_difflines(input_[:2]) == [UnchangedLine(input_[0][2:]), RemovedLine(input_[1][2:])]
    assert _build_difflines(input_[:3]) == [
        UnchangedLine(input_[0][2:]),
        RemovedLine(input_[1][2:]),
        RemovedLine(input_[2][2:]),
    ]
    assert _build_difflines(input_[:5]) == [
        UnchangedLine(input_[0][2:]),
        RemovedLine(input_[1][2:]),
        ModifiedLine('Deuxième ligne', _empty_mask(14), 'Deuxièmee ligne', _parse_mask('        +')),
    ]
    assert _build_difflines(input_[:9])[:3] == [
        UnchangedLine(input_[0][2:]),
        RemovedLine(input_[1][2:]),
        ModifiedLine('Deuxième ligne', _empty_mask(14), 'Deuxièmee ligne', _parse_mask('        +')),
    ]


def test_apply_mask():
    _apply_mask('foo bar foo', _empty_mask(11)) == 'foo bar foo'
    _apply_mask('foo bar foo', _empty_mask(9)) == 'foo bar foo'
    _apply_mask('foo bar foo', _parse_mask('-^')) == 'o bar foo'
    _apply_mask('foo bar foo', _parse_mask(' -^')) == 'f bar foo'
    _apply_mask('foo bar foo', _parse_mask(' -^+')) == 'fbar foo'


def test_is_modified_line_consistent():
    candidate = ModifiedLine(
        content_before="### 43-2-6. Pour les sites nouveaux, les bassins de confinement des eaux d'incendie :",
        mask_before=_parse_mask("            ^^^^^^^^^^^^^^^^^^^^^^^^^^"),
        content_after="### 43-2-6. Les bassins de confinement des eaux d'incendie :",
        mask_after=_parse_mask("            ^"),
    )
    assert _is_modified_line_consistent(candidate)
    assert not _is_modified_line_consistent(ModifiedLine("xxxx", _parse_mask(""), "yyyy", _parse_mask("")))
    assert not _is_modified_line_consistent(ModifiedLine("xxxx", _parse_mask("-"), "yyyy", _parse_mask("")))
    assert not _is_modified_line_consistent(ModifiedLine("xxxx", _parse_mask("--"), "yyyy", _parse_mask("")))
    assert not _is_modified_line_consistent(ModifiedLine("xxxx", _parse_mask("---"), "yyyy", _parse_mask("")))
    assert _is_modified_line_consistent(ModifiedLine("xxxx", _parse_mask(""), "xxxx", _parse_mask("")))
    assert _is_modified_line_consistent(ModifiedLine("xxxxx", _parse_mask("-"), "xxxx", _parse_mask("")))
    assert _is_modified_line_consistent(ModifiedLine("xxxxx", _parse_mask(" -"), "xxxx", _parse_mask("")))
    assert _is_modified_line_consistent(ModifiedLine("xxxxx", _parse_mask(" -"), "xyxxx", _parse_mask(" -")))
    assert _is_modified_line_consistent(ModifiedLine("xxxxx", _parse_mask(" -"), "xyxxx", _parse_mask(" ^")))
