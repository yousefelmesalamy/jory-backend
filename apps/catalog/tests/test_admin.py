import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client_logged_in(client, staff_user, user_password):
    client.login(email=staff_user.email, password=user_password)
    return client


@pytest.mark.parametrize(
    "url",
    [
        "/admin/catalog/category/",
        "/admin/catalog/roaster/",
        "/admin/catalog/origin/",
        "/admin/catalog/product/",
    ],
)
def test_catalog_admin_list_pages_render(admin_client_logged_in, url):
    assert admin_client_logged_in.get(url).status_code == 200


def test_the_product_admin_change_page_renders_its_inlines(admin_client_logged_in, product):
    response = admin_client_logged_in.get(f"/admin/catalog/product/{product.id}/change/")
    assert response.status_code == 200
    body = response.content.decode()
    assert "variants" in body
    assert "images" in body
    assert "coffee profile" in body.lower()


def test_the_catalog_admin_requires_staff(client, user, user_password):
    client.login(email=user.email, password=user_password)
    response = client.get("/admin/catalog/product/")
    assert response.status_code in (302, 403)
