"""店舗検索とユーザー別の表示状態を一元化する。"""

from django.db.models import Avg, BooleanField, Count, Exists, OuterRef, Q, Value

from community.models import Favorite
from visits.models import Visit
from .models import Restaurant, Tag


def restaurant_queryset(user=None):
    queryset = Restaurant.objects.select_related('genre').prefetch_related('tags').order_by('name', 'pk').annotate(
        avg_rating=Avg('reviews__rating'), review_count=Count('reviews', distinct=True),
    )
    if user and user.is_authenticated:
        return queryset.annotate(
            is_favorite=Exists(Favorite.objects.filter(user=user, restaurant=OuterRef('pk'))),
            is_visited=Exists(Visit.objects.filter(user=user, restaurant=OuterRef('pk'))),
        )
    return queryset.annotate(is_favorite=Value(False, output_field=BooleanField()),
                             is_visited=Value(False, output_field=BooleanField()))


def filter_restaurants(form, user=None):
    queryset = restaurant_queryset(user)
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
