from django.urls import path

from .views import ProductReviewListCreateView, ReviewDetailView

app_name = "reviews"

urlpatterns = [
    path(
        "products/<str:product_lookup>/reviews/",
        ProductReviewListCreateView.as_view(),
        name="product-reviews",
    ),
    path("reviews/<int:pk>/", ReviewDetailView.as_view(), name="review-detail"),
]
