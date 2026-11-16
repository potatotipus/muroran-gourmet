"""担当 C の実装に引き継ぐマップ検索の仮画面。"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.cache import never_cache


@never_cache
@login_required
def search(request):
    return render(request, 'placeholder.html', {
        'screen_number': '08',
        'page_title': 'マップ検索',
        'description': '街を眺めて、気になる一軒へ。',
        'notice': '地図からお店を探す機能は、現在準備中です。',
    })
