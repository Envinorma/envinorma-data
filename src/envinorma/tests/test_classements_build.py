import json
from datetime import date

import pandas
import pytest

from envinorma.data_build.build.build_classements import _check_classements
from envinorma.data_build.validate.check_classements import (
    DetailedClassement,
    DetailedRegime,
    State,
    _check_classement_is_safe,
    _is_4xxx,
    _is_47xx,
)


def test_is_47xx():
    assert _is_47xx('47')
    assert _is_47xx('472')
    assert _is_47xx('4722')
    assert _is_47xx('47222')
    assert not _is_47xx(None)
    assert not _is_47xx('4')
    assert not _is_47xx('14')
    assert not _is_47xx('142')
    assert not _is_47xx('1422')
    assert not _is_47xx('14222')


def test_is_4xxx():
    assert _is_4xxx('4642')
    assert _is_4xxx('47xx')
    assert _is_4xxx('4801')
    assert not _is_4xxx('4')
    assert not _is_4xxx('42')
    assert not _is_4xxx('422')
    assert not _is_4xxx('14')
    assert not _is_4xxx('142')
    assert not _is_4xxx('1422')
    assert not _is_4xxx('14222')


def test_check_classement_is_safe():
    _check_classement_is_safe(
        DetailedClassement(
            s3ic_id='0065.12345',
            rubrique='47xx',
            regime=DetailedRegime.NC,
            alinea=None,
            date_autorisation=None,
            state=None,
            regime_acte=DetailedRegime.NC,
            alinea_acte=None,
            rubrique_acte='47xx',
            activite=None,
            volume='',
            unit='',
        )
    )

    _check_classement_is_safe(
        DetailedClassement(
            s3ic_id='0065.12345',
            rubrique='4801',
            regime=DetailedRegime.NC,
            alinea=None,
            date_autorisation=None,
            state=None,
            regime_acte=None,
            alinea_acte=None,
            rubrique_acte='4801',
            activite=None,
            volume='',
            unit='',
        )
    )

    _check_classement_is_safe(
        DetailedClassement(
            s3ic_id='0065.12345',
            rubrique='4029',
            regime=DetailedRegime.A,
            alinea='1.',
            date_autorisation=date.today(),
            state=State.EN_FONCTIONNEMENT,
            regime_acte=DetailedRegime.A,
            alinea_acte='',
            rubrique_acte='3019',
            activite='',
            volume='',
            unit='',
        )
    )

    with pytest.raises(AssertionError):
        _check_classement_is_safe(
            DetailedClassement(
                s3ic_id='0065.12345',
                rubrique='47xx',
                regime=DetailedRegime.A,
                alinea='1.',
                date_autorisation=date.today(),
                state=State.EN_FONCTIONNEMENT,
                regime_acte=DetailedRegime.A,
                alinea_acte='',
                rubrique_acte='3019',
                activite='',
                volume='1.2',
                unit='t',
            )
        )


def test_build_dataframe():
    records = [
        json.loads(
            DetailedClassement(
                s3ic_id='0065.12345',
                rubrique='4029',
                regime=DetailedRegime.A,
                alinea='1.',
                date_autorisation=date.today(),
                state=State.EN_FONCTIONNEMENT,
                regime_acte=DetailedRegime.A,
                alinea_acte='',
                rubrique_acte='3019',
                activite='',
                volume='',
                unit='2',
            ).json()
        )
    ]
    res = pandas.DataFrame.from_records(records)
    _check_classements(res)
