"""ログイン後のジャンル選択・店舗検索・店舗詳細。"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache

from .forms import RestaurantSearchForm
from .models import Genre
from .query import filter_restaurants, restaurant_queryset


@never_cache
@login_required
def genres(request):
    return render(request, 'restaurants/genres.html', {'genres': Genre.objects.all()})


@never_cache
@login_required
def restaurant_list(request):
    form = RestaurantSearchForm(request.GET)
    restaurants = filter_restaurants(form, request.user)
    return render(request, 'restaurants/list.html', {
        'form': form, 'restaurants': restaurants, 'result_count': restaurants.count(),
        'query_string': form.query_string,
    })


@never_cache
@login_required
def filters(request):
    form = RestaurantSearchForm(request.GET)
    return render(request, 'restaurants/filters.html', {'form': form, 'query_string': form.query_string})


@never_cache
@login_required
def detail(request, pk):
    restaurant = get_object_or_404(restaurant_queryset(request.user), pk=pk)
    form = RestaurantSearchForm(request.GET)
    return render(request, 'restaurants/detail.html', {
        'restaurant': restaurant, 'query_string': form.query_string,
        'reviews': restaurant.reviews.select_related('user').all(),
    })
