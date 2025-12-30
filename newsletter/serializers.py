from rest_framework import serializers
from .models import Item, Subscriber, EmailConfig
from django.contrib.auth.models import User
from .crypto_utils import encrypt_secret

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = '__all__' # Or specify a list of fields: ['id', 'name', 'description']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # Expose safe user fields only
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "last_login",
            "date_joined",
        ]

class SubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscriber
        fields = [
            "id",
            "name",
            "email",
            "subscribed_on",
            "is_active",
        ]


class EmailConfigSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)

    class Meta:
        model = EmailConfig
        fields = [
            "id",
            "name",
            "from_email",
            "is_active",
            "is_primary",
            "provider",
            "host",
            "port",
            "username",
            "password",        # write-only virtual
            "password_set",    # read-only flag
            "use_tls",
            "use_ssl",
            "from_name",
            "reply_to",
            "last_verified_at",
            "last_verify_error",
            "daily_quota",
            "per_minute_rate",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["password_set", "last_verified_at", "last_verify_error", "created_at", "updated_at"]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = self.context["request"].user
        obj = EmailConfig(user=user, **validated_data)
        if password:
            obj.password_encrypted = encrypt_secret(password)
            obj.password_set = True
        obj.full_clean()
        obj.save()
        return obj

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password is not None:
            instance.password_encrypted = encrypt_secret(password)
            instance.password_set = True
        instance.full_clean()
        instance.save()
        return instance