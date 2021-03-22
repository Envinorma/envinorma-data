'''
Script for generating repo for ap-envinorma.herokuapp.com
'''

import shutil
from shutil import copytree, ignore_patterns, rmtree

if __name__ == '__main__':
    docs = '/Users/remidelbouys/EnviNorma'
    main_repo = f'{docs}/envinorma'
    source_folder = f'{main_repo}/src'
    main_dest = f'{docs}/ap_app'
    destination_folder = f'{main_dest}/src'
    rmtree(destination_folder)
    ignore = ignore_patterns('backups/*', '*__pycache__*', '*.DS_Store', '*.mypy_cache*', '*AM.zip', 'venv')
    copytree(source_folder, destination_folder, ignore=ignore)
    shutil.copyfile(f'{source_folder}/ap_exploration/Procfile', f'{main_dest}/Procfile')
    shutil.copyfile(f'{source_folder}/ap_exploration/Aptfile', f'{main_dest}/Aptfile')
    shutil.copyfile(f'{main_repo}/requirements.txt', f'{main_dest}/requirements.txt')
    shutil.copyfile(f'{main_repo}/runtime.txt', f'{main_dest}/runtime.txt')
    shutil.copyfile(f'{main_repo}/.gitignore', f'{main_dest}/.gitignore')
    shutil.copyfile(f'{main_repo}/assets/favicon.ico', f'{main_dest}/assets/favicon.ico')
