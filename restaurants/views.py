"""ログイン後のジャンル選択・店舗検索・店舗詳細。"""

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Exists, OuterRef, Q
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache

from .forms import RestaurantSearchForm
from .models import Genre, Restaurant, Tag


def restaurant_queryset():
    return Restaurant.objects.select_related('genre').prefetch_related('tags')


def filter_restaurants(form):
    queryset = restaurant_queryset()
    if not form.is_valid():
        return queryset.none()
    data = form.cleaned_data
    for word in data['q'].split():
        # 特徴名は相関サブクエリで検索し、語数に比例した多対多 JOIN を避ける。
        tag_matches = Tag.objects.filter(restaurants=OuterRef('pk'), name__icontains=word)
        queryset = queryset.filter(
            Q(name__icontains=word) | Q(description__icontains=word) | Q(address__icontains=word)
            | Q(area__icontains=word) | Q(genre__name__icontains=word) | Exists(tag_matches)
            | Q(recommended_menu__icontains=word) | Q(owner_description__icontains=word)
        )
    if data['genre']:
        queryset = queryset.filter(genre=data['genre'])
    if data['area']:
        queryset = queryset.filter(area=data['area'])
    if data['budget']:
        queryset = queryset.filter(price_max__lte=int(data['budget']))
    selected_tags = data['tags']
    if selected_tags:
        # 選択されたタグの一致数が、選択数と同じ店舗だけを残す（AND 検索）。
        queryset = queryset.annotate(
            matched_tags=Count('tags', filter=Q(tags__in=selected_tags), distinct=True),
        ).filter(matched_tags=len(selected_tags))
        if any(tag.slug == 'late-night' for tag in selected_tags):
            queryset = queryset.exclude(opening_hours='')
    return queryset.distinct()


@never_cache
@login_required
def genres(request):
    return render(request, 'restaurants/genres.html', {'genres': Genre.objects.all()})


@never_cache
@login_required
def restaurant_list(request):
    form = RestaurantSearchForm(request.GET)
    restaurants = filter_restaurants(form)
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
    restaurant = get_object_or_404(restaurant_queryset(), pk=pk)
    form = RestaurantSearchForm(request.GET)
    return render(request, 'restaurants/detail.html', {
        'restaurant': restaurant, 'query_string': form.query_string,
    })
