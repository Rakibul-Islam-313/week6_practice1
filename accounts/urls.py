from django.urls import path
from .views import UserBankAccountUpdateView
from .import views
urlpatterns = [
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login_page'),
    path('logout/', views.UserLogoutView.as_view(), name='logout_page'),
    path('profile/', UserBankAccountUpdateView.as_view(), name='profile_page' ),
]