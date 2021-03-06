'''
Script for manually adding title sequences to parametrization.
Deprecated now: this feature is fully integrated in the back office.
'''
import argparse

from envinorma.back_office.fetch_data import (
    load_initial_am,
    load_parametrization,
    load_structured_am,
    upsert_new_parametrization,
)
from envinorma.parametrization import add_titles_sequences


def run(am_id: str):
    parametrization = load_parametrization(am_id)
    if not parametrization:
        raise ValueError('Parametrization not found.')
    am = load_structured_am(am_id) or load_initial_am(am_id)
    if not am:
        raise ValueError('AM not found.')
    new_parametrization = add_titles_sequences(parametrization, am)
    upsert_new_parametrization(am_id, new_parametrization)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--am-id', '-a', dest='am_id', required=True)
    run(parser.parse_args().am_id)
