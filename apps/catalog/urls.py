from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import CategoryViewSet, ProductViewSet, RoasterViewSet, SearchSuggestView

app_name = "catalog"

# SimpleRouter, not DefaultRouter: the accounts router already owns the API root.
router = SimpleRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("roasters", RoasterViewSet, basename="roaster")
router.register("products", ProductViewSet, basename="product")

urlpatterns = [
    # Registered before the router so a future catch-all route cannot shadow it.
    path("search/suggest/", SearchSuggestView.as_view(), name="search-suggest"),
    path("", include(router.urls)),
]
