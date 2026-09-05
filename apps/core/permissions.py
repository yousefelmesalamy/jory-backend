from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """Object access limited to the user the object belongs to."""

    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user_id == request.user.id
