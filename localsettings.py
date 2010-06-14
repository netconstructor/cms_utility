import os
from socket import gethostname

ROOT_PATH = os.path.dirname(__file__)
ROOT_URL = 'http://localhost:8000/' 
ANTIWORD = '/usr/bin/antiword'
WVTEXT = '/usr/bin/wvText'
UNRTF = '/usr/bin/unrtf --text'
TEMP_FILES = '/tmp/temp_files'

# for prod
if gethostname() == 'www3.news-apps.com':
    ROOT_URL = 'http://apps.joeboydston.com/cms_utility/'
elif gethostname() == 'debian':
    ROOT_URL = 'http://debian:8000/'
else:
    pass