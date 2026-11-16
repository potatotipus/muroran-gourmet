from django.urls import path

from . import views

app_name = 'maps'

urlpatterns = [
    path('search/', views.search, name='search'),
    path('stores/<int:pk>/', views.store, name='store'),
    path('stores/<int:pk>/directions/', views.directions, name='directions'),
]
