import os
import shutil
from distutils.dir_util import copy_tree


if __name__ == '__main__':
    full_repo = '/Users/remidelbouys/EnviNorma/envinorma/'
    heroku_repo = '/Users/remidelbouys/EnviNorma/heroku-dashboard/'
    tuples = [(full_repo + x, heroku_repo + x) for x in ('src/lib', 'src/data/maps', 'src/scripts')]
    for src_folder, dst_folder in tuples:
        if not os.path.exists(dst_folder):
            os.makedirs(dst_folder)
        copy_tree(src_folder, dst_folder)
    for file_ in ('requirements.txt', 'Procfile', '.gitignore'):
        shutil.copyfile(full_repo + file_, heroku_repo + file_)
