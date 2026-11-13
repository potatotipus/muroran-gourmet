"""アプリ全体の共通画面。"""

from django.views.generic import TemplateView


class HomeView(TemplateView):
    """初期構築段階のトップ画面。"""

    template_name = 'home.html'
