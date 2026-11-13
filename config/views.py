"""アプリ全体の共通画面。"""

from django.views.generic import TemplateView


class HomeView(TemplateView):
    """アプリ全体の公開トップ画面。"""

    template_name = 'home.html'
