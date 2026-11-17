"""公開用WSGI。ローカル用config/wsgi.pyと分離する。"""

import os

from django.core.wsgi import get_wsgi_application

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings_public'
application = get_wsgi_application()

