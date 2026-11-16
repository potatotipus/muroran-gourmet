from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from community.forms import StateActionForm
from config.http import redirect_back
from restaurants.models import Restaurant
from .models import Visit
from .services import visit_summary


@never_cache
@login_required
@require_POST
def update(request, restaurant_pk):
    restaurant = get_object_or_404(Restaurant, pk=restaurant_pk)
    form = StateActionForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest('登録または解除を指定してください。')
    if form.cleaned_data['action'] == 'add':
        _, created = Visit.objects.get_or_create(user=request.user, restaurant=restaurant)
        messages.success(request, '訪問済み（自己申告）に登録しました。' if created else 'このお店は訪問済みとして登録されています。')
    else:
        Visit.objects.filter(user=request.user, restaurant=restaurant).delete()
        messages.success(request, '訪問登録を解除しました。対応するスタンプ・ポイントも減少します。')
    return redirect_back(request, restaurant.get_absolute_url())


@never_cache
@login_required
def history(request):
    return render(request, 'visits/history.html', {
        'visits': Visit.objects.filter(user=request.user).select_related('restaurant'),
        'summary': visit_summary(request.user),
    })


@never_cache
@login_required
def stamps(request):
    return render(request, 'visits/stamps.html', {
        'visits': Visit.objects.filter(user=request.user).select_related('restaurant'),
        'summary': visit_summary(request.user),
    })
