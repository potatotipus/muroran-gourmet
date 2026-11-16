from django.urls import path

from . import views

app_name = 'restaurants'

urlpatterns = [
    path('', views.restaurant_list, name='list'),
    path('genres/', views.genres, name='genres'),
    path('filters/', views.filters, name='filters'),
    path('<int:pk>/', views.detail, name='detail'),
]
