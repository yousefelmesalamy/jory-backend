from django.urls import path

from .views import WishlistItemDeleteView, WishlistView

app_name = "wishlist"

urlpatterns = [
    path("wishlist/", WishlistView.as_view(), name="wishlist"),
    path("wishlist/<int:product_id>/", WishlistItemDeleteView.as_view(), name="wishlist-remove"),
]
