from django.contrib import admin
from django.utils import timezone
from .models import Favorite, Report, Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'user', 'rating', 'created_at', 'edited_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('comment', 'restaurant__name', 'user__first_name')
    readonly_fields = ('created_at', 'edited_at')
    list_select_related = ('restaurant', 'user')

    def save_model(self, request, obj, form, change):
        if change:
            obj.edited_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'restaurant', 'created_at')
    list_select_related = ('user', 'restaurant')


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'kind', 'user', 'status', 'created_at')
    list_filter = ('status', 'kind')
    search_fields = ('reason', 'restaurant__name')
    readonly_fields = ('user', 'restaurant', 'review', 'kind', 'reason', 'created_at')
