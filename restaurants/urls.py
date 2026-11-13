from django.urls import path

from . import views

app_name = 'restaurants'

urlpatterns = [
    path('genres/', views.genres, name='genres'),
]
