from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


# Declared above Category, which types itself with it.
class ProductType(models.TextChoices):
    COFFEE = "COFFEE", "Coffee"
    EQUIPMENT = "EQUIPMENT", "Equipment"
    ROASTING_MACHINE = "ROASTING_MACHINE", "Roasting machine"
    ACCESSORY = "ACCESSORY", "Accessory"


PRODUCT_TYPE_LABELS_AR = {
    ProductType.COFFEE: "قهوة",
    ProductType.EQUIPMENT: "معدات",
    ProductType.ROASTING_MACHINE: "محمصة",
    ProductType.ACCESSORY: "إكسسوارات",
}


class Category(TimeStampedModel):
    """Browse taxonomy. One nesting level is expected (Coffee → Single Origin)."""

    name = models.CharField(max_length=120)
    name_ar = models.CharField(max_length=120, blank=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    description = models.TextField(blank=True)
    description_ar = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    # Blank means "inherit from the parent". Drives which filter facets a
    # category exposes — see apps/catalog/facets.py.
    product_type = models.CharField(max_length=20, choices=ProductType.choices, blank=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def descendant_ids(self):
        """Own id plus every id nested beneath it. Phase 3 search filters on this."""
        ids = [self.id]
        for child in Category.objects.filter(parent_id=self.id):
            ids.extend(child.descendant_ids())
        return ids

    @property
    def effective_product_type(self):
        """Own type, else the parent's, else coffee. The tree is one level deep
        by design, so this recursion is at most two hops."""
        if self.product_type:
            return self.product_type
        if self.parent_id:
            return self.parent.effective_product_type
        return ProductType.COFFEE


class Roaster(TimeStampedModel):
    """A roastery brand whose coffee Jory stocks."""

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    country = models.CharField(max_length=100, blank=True)
    logo = models.ImageField(upload_to="roasters/", blank=True, null=True)
    bio = models.TextField(blank=True)
    bio_ar = models.TextField(blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(TimeStampedModel):
    """A manufacturer of equipment or roasting machines. Kept separate from
    `Roaster`: a roastery sells beans, and its `bio` reads as coffee copy."""

    name = models.CharField(max_length=150)
    name_ar = models.CharField(max_length=150, blank=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    country = models.CharField(max_length=100, blank=True)
    logo = models.ImageField(upload_to="brands/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Origin(TimeStampedModel):
    """A coffee's country of origin. A lookup table so the API can offer a fixed
    set of choices instead of matching free text."""

    name = models.CharField(max_length=100, unique=True)
    name_ar = models.CharField(max_length=100, blank=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Grind(models.TextChoices):
    WHOLE_BEAN = "WHOLE_BEAN", "Whole bean"
    ESPRESSO = "ESPRESSO", "Espresso"
    FILTER = "FILTER", "Filter"
    FRENCH_PRESS = "FRENCH_PRESS", "French press"
    TURKISH = "TURKISH", "Turkish"


GRIND_LABELS_AR = {
    Grind.WHOLE_BEAN: "حبوب كاملة",
    Grind.ESPRESSO: "إسبريسو",
    Grind.FILTER: "فلتر",
    Grind.FRENCH_PRESS: "فرنش برس",
    Grind.TURKISH: "تركي",
}


class Process(models.TextChoices):
    WASHED = "WASHED", "Washed"
    NATURAL = "NATURAL", "Natural"
    HONEY = "HONEY", "Honey"
    ANAEROBIC = "ANAEROBIC", "Anaerobic"
    WET_HULLED = "WET_HULLED", "Wet hulled"


PROCESS_LABELS_AR = {
    Process.WASHED: "مغسولة",
    Process.NATURAL: "طبيعية",
    Process.HONEY: "هني",
    Process.ANAEROBIC: "لاهوائي",
    Process.WET_HULLED: "مقشورة رطبة",
}


class RoastLevel(models.TextChoices):
    LIGHT = "LIGHT", "Light"
    MEDIUM = "MEDIUM", "Medium"
    MEDIUM_DARK = "MEDIUM_DARK", "Medium dark"
    DARK = "DARK", "Dark"


ROAST_LEVEL_LABELS_AR = {
    RoastLevel.LIGHT: "فاتحة",
    RoastLevel.MEDIUM: "متوسطة",
    RoastLevel.MEDIUM_DARK: "متوسطة إلى داكنة",
    RoastLevel.DARK: "داكنة",
}


class MachineType(models.TextChoices):
    DRUM_ROASTER = "DRUM_ROASTER", "Drum roaster"
    FLUID_BED_ROASTER = "FLUID_BED_ROASTER", "Fluid-bed roaster"
    SAMPLE_ROASTER = "SAMPLE_ROASTER", "Sample roaster"
    GRINDER = "GRINDER", "Grinder"
    BREWER = "BREWER", "Brewer"
    KETTLE = "KETTLE", "Kettle"
    OTHER = "OTHER", "Other"


MACHINE_TYPE_LABELS_AR = {
    MachineType.DRUM_ROASTER: "محمصة أسطوانية",
    MachineType.FLUID_BED_ROASTER: "محمصة هوائية",
    MachineType.SAMPLE_ROASTER: "محمصة عينات",
    MachineType.GRINDER: "مطحنة",
    MachineType.BREWER: "أداة تحضير",
    MachineType.KETTLE: "غلاية",
    MachineType.OTHER: "أخرى",
}


class Product(TimeStampedModel):
    """The catalog entry a shopper sees as one page. Sellable units are its variants."""

    name = models.CharField(max_length=200)
    name_ar = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    short_description = models.CharField(max_length=300, blank=True)
    short_description_ar = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    description_ar = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    roaster = models.ForeignKey(
        Roaster, null=True, blank=True, on_delete=models.SET_NULL, related_name="products"
    )
    product_type = models.CharField(
        max_length=20, choices=ProductType.choices, default=ProductType.COFFEE
    )
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # Denormalized so list endpoints can sort by rating without aggregating.
    # Phase 6 recomputes these whenever a review is written.
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def active_variants(self):
        # Iterates the prefetch cache when the queryset prefetched `variants`,
        # so list endpoints stay at a fixed query count.
        return [variant for variant in self.variants.all() if variant.is_active]

    @property
    def price_from(self):
        prices = [variant.price for variant in self.active_variants]
        return min(prices) if prices else None

    @property
    def is_on_sale(self):
        return any(variant.is_on_sale for variant in self.active_variants)

    @property
    def compare_at_price_from(self):
        variants = self.active_variants
        if not variants:
            return None
        cheapest = min(variants, key=lambda variant: variant.price)
        return cheapest.compare_at_price if cheapest.is_on_sale else None

    @property
    def in_stock(self):
        return any(variant.stock_quantity > 0 for variant in self.active_variants)

    @property
    def primary_image(self):
        images = list(self.images.all())
        for image in images:
            if image.is_primary:
                return image
        return images[0] if images else None


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-is_primary", "display_order", "id"]

    def __str__(self):
        return f"Image of {self.product.name}"


class ProductVariant(TimeStampedModel):
    """The sellable unit: one SKU, one price, one stock count."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=64, unique=True)
    label = models.CharField(max_length=120, help_text='e.g. "250g / Whole bean"')
    weight_grams = models.PositiveIntegerField(null=True, blank=True)
    grind = models.CharField(max_length=20, choices=Grind.choices, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["price"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(price__gte=0), name="variant_price_not_negative"
            ),
            # Sale is derived from this relationship, so the database refuses to
            # store a "sale" that isn't one.
            models.CheckConstraint(
                check=models.Q(compare_at_price__isnull=True)
                | models.Q(compare_at_price__gt=models.F("price")),
                name="variant_compare_at_price_above_price",
            ),
        ]

    def __str__(self):
        return f"{self.product.name} — {self.label}"

    @property
    def is_on_sale(self):
        return self.compare_at_price is not None and self.compare_at_price > self.price

    @property
    def discount_percent(self):
        if not self.is_on_sale:
            return 0
        saving = self.compare_at_price - self.price
        return int(round(saving / self.compare_at_price * 100))

    @property
    def in_stock(self):
        return self.stock_quantity > 0


class CoffeeProfile(TimeStampedModel):
    """Origin attributes that only coffee has. Absent for equipment and machines."""

    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="coffee_profile")
    origin = models.ForeignKey(Origin, on_delete=models.PROTECT, related_name="coffee_profiles")
    region = models.CharField(max_length=120, blank=True)
    farm = models.CharField(max_length=150, blank=True)
    process = models.CharField(max_length=20, choices=Process.choices, blank=True)
    variety = models.CharField(max_length=150, blank=True)
    roast_level = models.CharField(max_length=20, choices=RoastLevel.choices, blank=True)
    altitude_masl = models.PositiveIntegerField(null=True, blank=True)
    tasting_notes = models.CharField(max_length=300, blank=True)
    harvest_year = models.PositiveIntegerField(null=True, blank=True)
    cupping_score = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    def __str__(self):
        return f"{self.product.name} — {self.origin}"


class HardwareProfile(TimeStampedModel):
    """Attributes only machines and equipment have. Absent for coffee — the
    mirror image of CoffeeProfile."""

    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name="hardware_profile"
    )
    brand = models.ForeignKey(
        Brand,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="hardware_profiles",
    )
    machine_type = models.CharField(max_length=30, choices=MachineType.choices, blank=True)

    def __str__(self):
        return f"{self.product.name} — {self.brand or 'unbranded'}"
