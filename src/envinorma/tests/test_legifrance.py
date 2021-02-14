import os


def test_legifrance_has_no_dependency_on_envinorma():
    folder = __file__.replace('envinorma/tests/test_legifrance.py', 'legifrance')

    for file_ in os.listdir(folder):
        filename = folder + '/' + file_
        if not os.path.isfile(filename):
            continue
        if 'envinorma' in open(filename).read():
            raise ValueError(f'Dependency on envinorma found in {file_}')
