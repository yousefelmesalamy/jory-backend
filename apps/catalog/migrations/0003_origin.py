import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_product_productvariant_productimage_coffeeprofile_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Origin",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(blank=True, max_length=120, unique=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["name"]},
        ),
        # Nullable for now: the backfill in the next migration fills it before
        # 0005 tightens it to NOT NULL.
        migrations.AddField(
            model_name="coffeeprofile",
            name="origin",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="coffee_profiles",
                to="catalog.origin",
            ),
        ),
    ]
