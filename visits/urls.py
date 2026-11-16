from django.urls import path
from . import views

app_name = 'visits'
urlpatterns = [
    path('stores/<int:restaurant_pk>/', views.update, name='update'),
    path('history/', views.history, name='history'),
    path('stamps/', views.stamps, name='stamps'),
]
