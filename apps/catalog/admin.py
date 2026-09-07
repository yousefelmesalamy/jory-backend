from django.contrib import admin

from .models import (
    Brand,
    Category,
    CoffeeProfile,
    HardwareProfile,
    Origin,
    Product,
    ProductImage,
    ProductVariant,
    Roaster,
)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = [
        "sku", "label", "weight_grams", "grind", "price", "compare_at_price",
        "stock_quantity", "is_active",
    ]


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class CoffeeProfileInline(admin.StackedInline):
    model = CoffeeProfile
    extra = 0
    max_num = 1
    can_delete = True


class HardwareProfileInline(admin.StackedInline):
    model = HardwareProfile
    extra = 0
    max_num = 1
    can_delete = True


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "is_active"]
    list_filter = ["is_active", "country"]
    search_fields = ["name", "country"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "parent", "product_type", "is_active", "display_order"]
    list_filter = ["is_active", "parent", "product_type"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Roaster)
class RoasterAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "is_active"]
    list_filter = ["is_active", "country"]
    search_fields = ["name", "country"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Origin)
class OriginAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name", "product_type", "category", "roaster", "is_active", "is_featured", "rating_avg",
    ]
    list_filter = ["product_type", "is_active", "is_featured", "category", "roaster"]
    search_fields = ["name", "description", "variants__sku"]
    prepopulated_fields = {"slug": ("name",)}
    # Phase 6 computes these from reviews; a staff edit would be overwritten.
    readonly_fields = ["rating_avg", "rating_count"]
    inlines = [
        ProductVariantInline,
        ProductImageInline,
        CoffeeProfileInline,
        HardwareProfileInline,
    ]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = [
        "sku", "product", "label", "price", "compare_at_price", "stock_quantity", "is_active",
    ]
    list_filter = ["is_active", "grind"]
    search_fields = ["sku", "product__name"]
