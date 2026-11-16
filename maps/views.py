"""共通コンポーネントを使う地図と外部経路案内。"""

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from urllib.parse import urlencode

from restaurants.forms import RestaurantSearchForm
from restaurants.models import Restaurant
from restaurants.query import filter_restaurants, restaurant_queryset

from .services import google_maps_urls, map_data
from .forms import PersonalMapForm


@never_cache
@login_required
def search(request):
    form = RestaurantSearchForm(request.GET)
    restaurants = filter_restaurants(form, request.user)
    data = map_data(restaurants, form.query_string)
    return render(request, 'maps/search.html', {
        'form': form, 'query_string': form.query_string, 'map_data': data,
        'total_count': len(restaurants), 'missing_count': len(restaurants) - len(data['stores']),
    })


@never_cache
@login_required
def store(request, pk):
    restaurant = get_object_or_404(restaurant_queryset(request.user), pk=pk)
    return render(request, 'maps/store.html', {
        'restaurant': restaurant, 'map_data': map_data([restaurant]),
        'google_urls': google_maps_urls(restaurant),
    })


@never_cache
@login_required
def directions(request, pk):
    restaurant = get_object_or_404(restaurant_queryset(request.user), pk=pk)
    return render(request, 'maps/directions.html', {
        'restaurant': restaurant, 'google_urls': google_maps_urls(restaurant),
    })


@never_cache
@login_required
def personal(request):
    form = PersonalMapForm(request.GET)
    restaurants = restaurant_queryset(request.user).filter(Q(is_favorite=True) | Q(is_visited=True))
    if form.is_valid():
        if form.cleaned_data['mode'] == 'favorites':
            restaurants = restaurants.filter(is_favorite=True)
        elif form.cleaned_data['mode'] == 'visited':
            restaurants = restaurants.filter(is_visited=True)
    else:
        restaurants = restaurants.none()
    return render(request, 'maps/personal.html', {
        'form': form, 'map_data': map_data(restaurants, query_string=urlencode({'mode': form.cleaned_data.get('mode', '')}), source='personal'),
        'record_count': len(restaurants),
    })
