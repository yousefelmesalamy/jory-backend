from django.urls import path

from .views import (
    ApplyVoucherView,
    CartItemDetailView,
    CartItemsView,
    CartView,
    MergeCartView,
    RemoveVoucherView,
)

app_name = "cart"

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/", CartItemsView.as_view(), name="cart-items"),
    path("cart/items/<int:pk>/", CartItemDetailView.as_view(), name="cart-item-detail"),
    path("cart/apply-voucher/", ApplyVoucherView.as_view(), name="cart-apply-voucher"),
    path("cart/voucher/", RemoveVoucherView.as_view(), name="cart-remove-voucher"),
    path("cart/merge/", MergeCartView.as_view(), name="cart-merge"),
]
