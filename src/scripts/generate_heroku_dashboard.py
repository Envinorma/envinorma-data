'''
Script for generating repo for dashboard-envinorma.herokuapp.com
'''

import os
from distutils.dir_util import copy_tree

if __name__ == '__main__':
    full_repo = '/Users/remidelbouys/EnviNorma/envinorma/src/envinorma/dashboard'
    heroku_repo = '/Users/remidelbouys/EnviNorma/heroku-dashboard/'
    if not os.path.exists(heroku_repo):
        os.makedirs(heroku_repo)
    copy_tree(heroku_repo, heroku_repo)
