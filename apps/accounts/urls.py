from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from . import views

app_name = "auth"

urlpatterns = [
    # JWT Authentication
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("verify/", TokenVerifyView.as_view(), name="token_verify"),
    # User management
    path("register/", views.RegisterView.as_view(), name="register"),
    path("profile/", views.UserProfileView.as_view(), name="profile"),
    path(
        "change-password/", views.ChangePasswordView.as_view(), name="change_password"
    ),
    # User CRUD (for admin purposes)
    path("users/", views.UserListView.as_view(), name="user_list"),
    path("users/<int:pk>/", views.UserDetailView.as_view(), name="user_detail"),
]
