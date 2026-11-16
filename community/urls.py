from django.urls import path
from . import views

app_name = 'community'
urlpatterns = [
    path('stores/<int:restaurant_pk>/reviews/new/', views.review_create, name='review_create'),
    path('reviews/<int:pk>/edit/', views.review_edit, name='review_edit'),
    path('reviews/<int:pk>/delete/', views.review_delete, name='review_delete'),
    path('stores/<int:restaurant_pk>/favorite/', views.favorite_update, name='favorite_update'),
    path('favorites/', views.favorites, name='favorites'),
    path('stores/<int:restaurant_pk>/report/', views.report, name='report_store'),
    path('reviews/<int:review_pk>/report/', views.report, name='report_review'),
]
