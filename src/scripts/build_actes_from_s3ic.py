'''
    Fetch and dump all actes from S3IC database
    Output is used as input to ap_exploration package
'''
import json
import pathlib

from scripts.s3ic import fetch_actes


def run():
    actes = fetch_actes()
    here = pathlib.Path(__file__)
    filename = here.parent.parent.joinpath('ap_exploration/pages/actes.json')
    json.dump([acte.to_dict() for acte in actes], open(filename, 'w'))


if __name__ == '__main__':
    run()
