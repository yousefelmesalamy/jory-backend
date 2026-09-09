from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.i18n import get_locale
from apps.core.permissions import IsOwner

from .models import Address
from .serializers import (
    AddressSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordResetVerifySerializer,
    RegisterSerializer,
    UserSerializer,
)
from .services import ensure_default_address, send_password_reset_email

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            RefreshToken(request.data["refresh"]).blacklist()
        except KeyError:
            return Response(
                {"error": {"code": "missing_refresh", "message": "A refresh token is required.", "details": {}}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except TokenError:
            return Response(
                {"error": {"code": "invalid_token", "message": "This refresh token is not valid.", "details": {}}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated."}, status=status.HTTP_200_OK)


# One message for every outcome. Deliberately says nothing about whether the
# address is registered.
RESET_REQUESTED_MESSAGE = "If that email has an account, a reset link is on its way."


class PasswordResetRequestView(APIView):
    """Mail a reset link, and reveal nothing about who has an account.

    Every path through this view returns the same 200 and the same body: a
    registered address, an unregistered one, a malformed one, and a send that
    failed at the provider. That is why the serializer's errors are discarded
    rather than raised — a 400 on a malformed address is harmless, but keeping
    a single response shape means there is no branch here that could ever be
    made to leak by a later edit.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            user = User.objects.filter(
                email__iexact=serializer.validated_data["email"], is_active=True
            ).first()
            if user:
                send_password_reset_email(user, get_locale(request))

        return Response({"detail": RESET_REQUESTED_MESSAGE}, status=status.HTTP_200_OK)


class PasswordResetVerifyView(APIView):
    """Lets the reset page say "this link has expired" before the shopper types
    a new password, rather than after."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"valid": True}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated."}, status=status.HTTP_200_OK)


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        # Scoping the queryset — not just the permission — makes another user's
        # address return 404 rather than 403, leaking nothing about its existence.
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        ensure_default_address(serializer.save(user=self.request.user))

    def perform_update(self, serializer):
        ensure_default_address(serializer.save())
