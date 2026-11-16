"""担当 B の実装に引き継ぐジャンル選択の仮画面。"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.cache import never_cache


@never_cache
@login_required
def genres(request):
    return render(request, 'placeholder.html', {
        'screen_number': '05',
        'page_title': 'ジャンル選択',
        'description': '食べたいものから、お店を見つける。',
        'notice': 'ジャンルからお店を探す機能は、現在準備中です。',
    })
