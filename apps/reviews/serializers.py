from rest_framework import serializers

from .models import Review


class ReviewAuthorSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)


class ReviewSerializer(serializers.ModelSerializer):
    user = ReviewAuthorSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ["id", "user", "rating", "title", "body", "created_at", "updated_at"]
        # `product` and `user` are absent on purpose: they come from the URL and
        # the request, never from the body.
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("A rating must be between 1 and 5.")
        return value
