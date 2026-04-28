from rest_framework.permissions import BasePermission
from stores.models import Store


class IsStoreOwner(BasePermission):
    """
    Grants access only if the store in the URL belongs to the requesting user.
    Use on any view that takes store_id as a URL kwarg.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        store_id = view.kwargs.get('store_id')
        if not store_id:
            return True  # No store_id in URL — let object-level check handle it
        return Store.objects.filter(id=store_id, user=request.user, is_active=True).exists()
