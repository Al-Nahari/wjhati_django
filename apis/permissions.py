from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsStaffOrReadOnly(BasePermission):
    """القراءة لأي مستخدم مسجَّل، أما الكتابة فللمشرفين فقط."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or user.is_staff


class IsDriverOrStaffOrReadOnly(BasePermission):
    """القراءة لأي مستخدم مسجَّل، أما الكتابة فللسائقين والمشرفين."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.is_staff or hasattr(user, 'driver')
