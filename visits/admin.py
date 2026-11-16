from django.contrib import admin
from .models import Visit


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('user', 'restaurant', 'visited_at')
    readonly_fields = ('visited_at',)
    list_select_related = ('user', 'restaurant')
