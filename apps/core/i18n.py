SUPPORTED_LOCALES = ("en", "ar")
DEFAULT_LOCALE = "en"


def get_locale(request):
    """Resolve the storefront locale for this request: `?lang=` query param,
    then `Accept-Language`, then English. Mirrors the frontend's own
    cookie -> Accept-Language -> "ar" resolution order (see the Angular
    TranslationService), just without the cookie since the API is stateless."""
    lang = request.query_params.get("lang") if hasattr(request, "query_params") else None
    if not lang:
        lang = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
    lang = (lang or "").strip().lower()[:2]
    return lang if lang in SUPPORTED_LOCALES else DEFAULT_LOCALE
