import pandas as pd


def check_unique_classements_csv(filename: str) -> None:
    csv = pd.read_csv(filename)
    expected_keys = ['regime', 'rubrique', 'alinea']
    for key in expected_keys:
        if key not in csv.keys():
            raise ValueError(f'Expecting key {key} in {csv.keys()}')
    nb_rows = csv.shape[0]
    nb_rows_no_repeat = csv.groupby(['rubrique', 'regime']).count().shape[0]
    if nb_rows != nb_rows_no_repeat:
        raise ValueError(
            f'Expecting {nb_rows} and {nb_rows_no_repeat} to be equal. It is not, '
            'so there are repeated couples in dataframe.'
        )
