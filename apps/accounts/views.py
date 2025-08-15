from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    ChangePasswordSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """User registration endpoint"""

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens for the newly registered user
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserSerializer(user).data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get and update user profile"""

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.UpdateAPIView):
    """Change user password"""

    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserListView(generics.ListAPIView):
    """List all users (admin only)"""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["is_active", "is_staff", "date_joined"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["date_joined", "last_login", "username"]
    ordering = ["-date_joined"]

    def get_queryset(self):
        # Check if this is a schema generation request
        if getattr(self, "swagger_fake_view", False):
            return User.objects.none()
        # Only allow staff users to view all users
        if self.request.user.is_staff:
            return User.objects.all()
        else:
            # Regular users can only see themselves
            return User.objects.filter(id=self.request.user.id)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete a specific user (admin only)"""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Check if this is a schema generation request
        if getattr(self, "swagger_fake_view", False):
            return User.objects.none()
        # Only allow staff users to manage other users
        if self.request.user.is_staff:
            return User.objects.all()
        else:
            # Regular users can only access their own profile
            return User.objects.filter(id=self.request.user.id)
