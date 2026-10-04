"""Back-office forms for the catalog models.

ModelForms inherit the models' own rules (name required, slug unique);
the explicit ``price`` declaration adds the one rule the model doesn't
carry — the price must be positive. ``ProductImageField`` owns the upload
rules. Widgets get their DaisyUI classes in one shared ``__init__`` loop,
as on ``CheckoutForm``.
"""

from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

from .models import MAX_IMAGE_SIDE, Category, Product, Tag

MAX_IMAGE_MB = 5

# Pillow's names for the formats an upload may be. Phone cameras often
# write MPO, a JPEG carrying extra frames; it is a JPEG to everyone else.
ALLOWED_IMAGE_FORMATS = {"JPEG", "MPO", "PNG", "WEBP"}

IMAGE_RULE = "Upload a JPEG, PNG, or WebP image."


class ProductImageField(forms.ImageField):
    """An image upload judged by Pillow's detected format, never its extension."""

    default_validators = []  # drop ImageField's file-extension check
    widget = forms.FileInput

    def to_python(self, data):
        if isinstance(data, UploadedFile):
            size_mb = data.size / (1024 * 1024)
            if size_mb > MAX_IMAGE_MB:
                raise ValidationError(
                    f"Image is {size_mb:.1f} MB; the limit is {MAX_IMAGE_MB} MB.",
                    code="file_too_large",
                )
        try:
            upload = super().to_python(data)
        except ValidationError as error:
            if error.code != "invalid_image":
                raise
            raise ValidationError(
                f"‘{data.name}’ isn't an image we can read. {IMAGE_RULE}",
                code="invalid_image",
            ) from error
        if upload is not None and upload.image.format not in ALLOWED_IMAGE_FORMATS:
            raise ValidationError(
                f"‘{upload.name}’ is a {upload.image.format} file. {IMAGE_RULE}",
                code="invalid_format",
            )
        return upload


class StyledModelForm(forms.ModelForm):
    """Base form that dresses every widget in DaisyUI classes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.FileInput):
                widget.attrs["class"] = "file-input w-full"
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "toggle toggle-primary"
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = "textarea w-full"
                widget.attrs.setdefault("rows", 6)
            elif isinstance(widget, forms.SelectMultiple):
                widget.attrs["class"] = "select h-auto w-full"
                widget.attrs.setdefault("size", 8)
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "select w-full"
            else:
                widget.attrs["class"] = "input w-full"


class ProductForm(StyledModelForm):
    price = forms.DecimalField(
        label="Price (USD)",
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    # Not model fields in Meta: the upload is processed by
    # Product.set_image, never assigned raw.
    image = ProductImageField(
        required=False,
        help_text=f"JPEG, PNG, or WebP, up to {MAX_IMAGE_MB} MB. Stored as "
        f"WebP, at most {MAX_IMAGE_SIDE}px on the long side.",
    )
    clear_image = forms.BooleanField(
        required=False,
        label="Remove the image (show the category placeholder)",
    )

    class Meta:
        model = Product
        fields = [
            "name",
            "slug",
            "tagline",
            "description",
            "price",
            "category",
            "tags",
            "is_available",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.image:
            del self.fields["clear_image"]

    def save(self, commit=True):
        upload = self.cleaned_data.get("image")
        if upload:
            self.instance.set_image(upload)
        elif self.cleaned_data.get("clear_image"):
            self.instance.image = ""
        return super().save(commit)


class CategoryForm(StyledModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug"]


class TagForm(StyledModelForm):
    class Meta:
        model = Tag
        fields = ["name", "slug"]
