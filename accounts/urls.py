from django.urls import path

from .views import AccountLoginView, AccountLogoutView, ChooseView, SignUpView, profile, profile_edit

app_name = 'accounts'

urlpatterns = [
    path('login/', AccountLoginView.as_view(), name='login'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('logout/', AccountLogoutView.as_view(), name='logout'),
    path('choose/', ChooseView.as_view(), name='choose'),
    path('profile/', profile, name='profile'),
    path('profile/edit/', profile_edit, name='profile_edit'),
]
