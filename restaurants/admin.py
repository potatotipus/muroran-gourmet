"""店舗・分類を Django Admin から編集する。"""

from django.contrib import admin

from .forms import RestaurantAdminForm
from .models import Genre, Restaurant, Tag


@admin.register(Genre, Tag)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('sort_order', 'pk')


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    form = RestaurantAdminForm
    list_display = ('name', 'genre', 'area', 'price_min', 'price_max')
    list_filter = ('genre', 'area', 'tags')
    search_fields = ('name', 'description', 'address')
    filter_horizontal = ('tags',)
    readonly_fields = ('demo_key',)
    list_select_related = ('genre',)
