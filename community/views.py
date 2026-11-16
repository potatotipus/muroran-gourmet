"""本人の操作に限定した口コミ・お気に入り・情報の通報。"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from config.http import local_destination, redirect_back
from restaurants.models import Restaurant
from .forms import ReportForm, ReviewForm, StateActionForm
from .models import Favorite, Review


@never_cache
@login_required
def review_create(request, restaurant_pk):
    restaurant = get_object_or_404(Restaurant, pk=restaurant_pk)
    form = ReviewForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        review = form.save(commit=False)
        review.user = request.user
        review.restaurant = restaurant
        review.save()
        messages.success(request, '口コミを投稿しました。')
        return redirect_back(request, restaurant.get_absolute_url())
    return render(request, 'community/review_form.html', {
        'form': form, 'restaurant': restaurant, 'editing': False,
        'return_url': local_destination(request, request.POST.get('next') or request.GET.get('next'), restaurant.get_absolute_url()),
    })


@never_cache
@login_required
def review_edit(request, pk):
    review = get_object_or_404(Review.objects.select_related('restaurant'), pk=pk, user=request.user)
    form = ReviewForm(request.POST if request.method == 'POST' else None, instance=review)
    if request.method == 'POST' and form.is_valid():
        review = form.save(commit=False)
        review.edited_at = timezone.now()
        review.save()
        messages.success(request, '口コミを更新しました。')
        return redirect_back(request, review.restaurant.get_absolute_url())
    return render(request, 'community/review_form.html', {
        'form': form, 'restaurant': review.restaurant, 'editing': True,
        'return_url': local_destination(request, request.POST.get('next') or request.GET.get('next'), review.restaurant.get_absolute_url()),
    })


@never_cache
@login_required
def review_delete(request, pk):
    reviews = Review.objects.select_related('restaurant')
    if not (request.user.is_staff and request.user.has_perm('community.delete_review')):
        reviews = reviews.filter(user=request.user)
    review = get_object_or_404(reviews, pk=pk)
    if request.method == 'POST':
        destination = review.restaurant.get_absolute_url()
        review.delete()
        messages.success(request, '口コミを削除しました。')
        return redirect_back(request, destination)
    return render(request, 'community/review_delete.html', {
        'review': review,
        'return_url': local_destination(request, request.POST.get('next') or request.GET.get('next'), review.restaurant.get_absolute_url()),
    })


@never_cache
@login_required
@require_POST
def favorite_update(request, restaurant_pk):
    restaurant = get_object_or_404(Restaurant, pk=restaurant_pk)
    form = StateActionForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest('登録または解除を指定してください。')
    if form.cleaned_data['action'] == 'add':
        _, created = Favorite.objects.get_or_create(user=request.user, restaurant=restaurant)
        messages.success(request, 'お気に入りに追加しました。' if created else 'すでにお気に入りに登録されています。')
    else:
        Favorite.objects.filter(user=request.user, restaurant=restaurant).delete()
        messages.success(request, 'お気に入りを解除しました。')
    return redirect_back(request, restaurant.get_absolute_url())


@never_cache
@login_required
def favorites(request):
    from restaurants.query import restaurant_queryset
    restaurants = restaurant_queryset(request.user).filter(is_favorite=True)
    return render(request, 'community/favorites.html', {'restaurants': restaurants, 'result_count': restaurants.count()})


@never_cache
@login_required
def report(request, restaurant_pk=None, review_pk=None):
    review = get_object_or_404(Review, pk=review_pk) if review_pk is not None else None
    restaurant = review.restaurant if review else get_object_or_404(Restaurant, pk=restaurant_pk)
    form = ReportForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        report = form.save(commit=False)
        report.user, report.restaurant, report.review = request.user, restaurant, review
        report.kind = 'review' if review else 'restaurant'
        report.save()
        messages.success(request, '内容を送信しました。管理者が確認し、必要に応じて対応します。店舗情報は直接変更されません。')
        return redirect(restaurant.get_absolute_url())
    return render(request, 'community/report_form.html', {'form': form, 'restaurant': restaurant, 'review': review})
