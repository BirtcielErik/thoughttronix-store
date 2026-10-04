from io import BytesIO

from django.core.files.base import ContentFile
from django.db import models
from django.templatetags.static import static
from django.urls import reverse
from PIL import Image, ImageOps

# Categories with a dedicated placeholder illustration; anything else
# falls back to default.svg. A product without an uploaded image shows
# its category's placeholder, a static file.
PLACEHOLDER_CATEGORIES = {
    "home-assistants",
    "neural-implants",
    "neural-wearables",
    "accessories",
    "defense",
    "legacy-products",
}

# Every placeholder SVG is drawn on a 400×300 viewBox.
PLACEHOLDER_SIZE = (400, 300)

# Uploaded images are stored downscaled to this long side, as WebP.
MAX_IMAGE_SIDE = 1200
WEBP_QUALITY = 80


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("products:category", kwargs={"slug": self.slug})

    @property
    def placeholder_image(self):
        """Static path of the placeholder image shown for this category's products."""
        if self.slug in PLACEHOLDER_CATEGORIES:
            return f"images/placeholders/{self.slug}.svg"
        return "images/placeholders/default.svg"


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        return self.filter(is_available=True)

    def search(self, text):
        """Simple icontains search over name and description."""
        return self.filter(
            models.Q(name__icontains=text) | models.Q(description__icontains=text)
        )


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    tagline = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")
    image = models.ImageField(
        upload_to="products/",
        blank=True,
        width_field="image_width",
        height_field="image_height",
    )
    image_width = models.PositiveIntegerField(null=True, editable=False)
    image_height = models.PositiveIntegerField(null=True, editable=False)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # A replaced or cleared image leaves its old file behind; remove it
        # once the new state is saved.
        old_name = (
            Product.objects.filter(pk=self.pk).values_list("image", flat=True).first()
            if self.pk
            else None
        )
        super().save(*args, **kwargs)
        if old_name and old_name != self.image.name:
            self.image.storage.delete(old_name)

    def get_absolute_url(self):
        return reverse("products:detail", kwargs={"slug": self.slug})

    def delete(self, *args, **kwargs):
        # Bulk queryset deletes skip this; the seed wipes media on its own.
        result = super().delete(*args, **kwargs)
        if self.image:
            self.image.storage.delete(self.image.name)
        return result

    @property
    def display_image(self):
        """URL of the uploaded image, or the category placeholder's."""
        if self.image:
            return self.image.url
        return static(self.category.placeholder_image)

    @property
    def display_width(self):
        return self.image_width if self.image else PLACEHOLDER_SIZE[0]

    @property
    def display_height(self):
        return self.image_height if self.image else PLACEHOLDER_SIZE[1]

    def set_image(self, source):
        """Attach ``source`` as this product's image, processed for the web.

        Downscales to ``MAX_IMAGE_SIDE`` on the long side and re-encodes as
        WebP, keeping transparency; only the processed file is stored.
        Doesn't save the product — the caller does, and ``save`` removes
        the file this one replaces.
        """
        source.seek(0)
        with Image.open(source) as original:
            picture = ImageOps.exif_transpose(original)
        picture = picture.convert("RGBA" if picture.has_transparency_data else "RGB")
        picture.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
        buffer = BytesIO()
        picture.save(buffer, "WEBP", quality=WEBP_QUALITY)
        # The content needs a name too: ImageField reads the dimensions
        # from it, and a nameless file counts as no file.
        name = f"{self.slug}.webp"
        self.image.save(name, ContentFile(buffer.getvalue(), name=name), save=False)
