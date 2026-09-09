from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.core.exceptions import InvalidResetLinkError

from .models import Address
from .services import load_user_from_reset, revoke_refresh_tokens

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "full_name", "phone", "date_joined"]
        read_only_fields = ["id", "email", "username", "date_joined"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = [
            "id", "email", "username", "full_name", "phone",
            "password", "password_confirm", "date_joined",
        ]
        read_only_fields = ["id", "date_joined"]

    def validate_email(self, value):
        normalized = User.objects.normalize_email(value)
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return normalized

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("An account with this username already exists.")
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "The two passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class LoginSerializer(TokenObtainPairSerializer):
    """Accepts either the email or the username in the identifier field
    (still named "email" for backward compatibility with existing clients),
    then resolves it to the account's email before handing off to SimpleJWT,
    since `User.USERNAME_FIELD` is "email"."""

    username_field = User.USERNAME_FIELD

    def validate(self, attrs):
        identifier = attrs.get(self.username_field, "")
        if identifier and "@" not in identifier:
            user = User.objects.filter(username__iexact=identifier).first()
            if user:
                attrs[self.username_field] = user.email

        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Your current password is incorrect.")
        return value

    def validate_new_password(self, value):
        try:
            validate_password(value, self.context["request"].user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        # Deliberately no "does this user exist" check: a validation error here
        # would tell an anonymous caller which addresses have accounts.
        return User.objects.normalize_email(value)


class PasswordResetVerifySerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        user = load_user_from_reset(attrs["uid"], attrs["token"])
        if user is None:
            raise InvalidResetLinkError()
        attrs["user"] = user
        return attrs


class PasswordResetConfirmSerializer(PasswordResetVerifySerializer):
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        # Link first, password second: `validate_password` needs the user for
        # its "not similar to your own email" check, and there is no point
        # grading a password for a link that was never going to work.
        attrs = super().validate(attrs)
        try:
            validate_password(attrs["new_password"], attrs["user"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        revoke_refresh_tokens(user)
        return user


class AddressSerializer(serializers.ModelSerializer):
    # `user` is deliberately absent so a client cannot assign an address to
    # somebody else; the view sets it from request.user.
    class Meta:
        model = Address
        fields = [
            "id", "full_name", "phone", "country", "city", "area",
            "street_address", "postal_code", "notes", "is_default", "created_at",
        ]
        read_only_fields = ["id", "created_at"]
