"""Product images: placeholder fallback, upload rules, processing, file cleanup."""

from http import HTTPStatus
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.templatetags.static import static
from django.urls import reverse
from PIL import Image

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Uploads land in a throwaway directory, never the real media/."""
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def image_upload(name="photo.png", size=(800, 600), fmt="PNG", mode="RGB"):
    # Half-transparent when RGBA: WebP drops an alpha channel that is
    # fully opaque.
    color = (128, 0, 128, 128) if mode == "RGBA" else "purple"
    buffer = BytesIO()
    Image.new(mode, size, color).save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue())


def edit(client, product, **extra):
    """POST the product's edit form unchanged, plus ``extra`` fields."""
    data = {
        "name": product.name,
        "slug": product.slug,
        "price": str(product.price),
        "category": str(product.category.pk),
        "is_available": "on",
        **extra,
    }
    return client.post(
        reverse("products:manage_product_update", kwargs={"pk": product.pk}), data
    )


def stored_files(media_root):
    return sorted(path.name for path in (media_root / "products").glob("*"))


# --- Display -----------------------------------------------------------------


def test_product_without_image_shows_category_placeholder(client, product):
    placeholder = static("images/placeholders/home-assistants.svg")

    assert product.display_image == placeholder
    assert (product.display_width, product.display_height) == (400, 300)
    assert placeholder in client.get(reverse("products:catalog")).content.decode()
    assert placeholder in client.get(product.get_absolute_url()).content.decode()


def test_uploaded_image_replaces_placeholder(client, product):
    product.set_image(image_upload())
    product.save()

    page = client.get(product.get_absolute_url()).content.decode()

    assert product.image.url in page
    assert 'loading="lazy"' in page
    assert 'width="800" height="600"' in page


# --- Upload rules ------------------------------------------------------------


@pytest.mark.parametrize(
    ("upload", "message"),
    [
        (image_upload("anim.gif", fmt="GIF"), "‘anim.gif’ is a GIF file."),
        (image_upload("scan.bmp", fmt="BMP"), "‘scan.bmp’ is a BMP file."),
        (
            SimpleUploadedFile("notes.png", b"definitely not pixels"),
            "‘notes.png’ isn&#x27;t an image we can read.",
        ),
        (
            SimpleUploadedFile(
                "logo.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>"
            ),
            "‘logo.svg’ isn&#x27;t an image we can read.",
        ),
    ],
)
def test_wrong_formats_are_rejected(client, staff_user, product, upload, message):
    client.force_login(staff_user)

    response = edit(client, product, image=upload)

    page = response.content.decode()
    assert response.status_code == HTTPStatus.OK
    assert message in page
    assert "Upload a JPEG, PNG, or WebP image." in page
    product.refresh_from_db()
    assert not product.image


def test_oversize_upload_is_rejected(client, staff_user, product):
    client.force_login(staff_user)
    upload = SimpleUploadedFile("huge.png", b"\0" * (6 * 1024 * 1024))

    response = edit(client, product, image=upload)

    assert "Image is 6.0 MB; the limit is 5 MB." in response.content.decode()
    product.refresh_from_db()
    assert not product.image


def test_format_is_judged_by_content_not_extension(client, staff_user, product):
    client.force_login(staff_user)

    edit(client, product, image=image_upload("photo.heic", fmt="JPEG"))

    product.refresh_from_db()
    assert product.image


# --- Processing --------------------------------------------------------------


def test_upload_is_downscaled_and_stored_as_webp(client, staff_user, product):
    client.force_login(staff_user)

    edit(client, product, image=image_upload(size=(2400, 1600)))

    product.refresh_from_db()
    assert product.image.name == "products/seraphine-home-hub.webp"
    assert (product.image_width, product.image_height) == (1200, 800)
    with Image.open(product.image.path) as stored:
        assert stored.format == "WEBP"
        assert stored.size == (1200, 800)


def test_small_upload_is_not_enlarged(product):
    product.set_image(image_upload(size=(300, 200)))

    assert (product.image_width, product.image_height) == (300, 200)


def test_transparency_survives_conversion(product):
    product.set_image(image_upload(mode="RGBA"))

    with Image.open(product.image.path) as stored:
        assert stored.mode == "RGBA"


# --- File lifecycle ----------------------------------------------------------


def test_replacing_an_image_deletes_the_old_file(
    client, staff_user, product, media_root
):
    client.force_login(staff_user)
    edit(client, product, image=image_upload())
    product.refresh_from_db()
    old_name = product.image.name

    edit(client, product, image=image_upload(size=(640, 480)))

    product.refresh_from_db()
    assert product.image.name != old_name
    assert stored_files(media_root) == [product.image.name.split("/")[-1]]


def test_clearing_reverts_to_placeholder_and_deletes_the_file(
    client, staff_user, product, media_root
):
    client.force_login(staff_user)
    edit(client, product, image=image_upload())

    edit(client, product, clear_image="on")

    product.refresh_from_db()
    assert not product.image
    assert product.image_width is None
    assert product.display_image == static(product.category.placeholder_image)
    assert stored_files(media_root) == []


def test_deleting_a_product_deletes_its_file(client, staff_user, product, media_root):
    client.force_login(staff_user)
    edit(client, product, image=image_upload())

    client.post(reverse("products:manage_product_delete", kwargs={"pk": product.pk}))

    assert stored_files(media_root) == []


def test_clear_toggle_appears_only_when_there_is_an_image(client, staff_user, product):
    client.force_login(staff_user)
    url = reverse("products:manage_product_update", kwargs={"pk": product.pk})

    assert "clear_image" not in client.get(url).content.decode()

    edit(client, product, image=image_upload())
    assert "clear_image" in client.get(url).content.decode()


# --- Access control ----------------------------------------------------------


def test_customers_cannot_upload(client, customer, product, media_root):
    client.force_login(customer)

    response = edit(client, product, image=image_upload())

    assert response.status_code == HTTPStatus.FORBIDDEN
    product.refresh_from_db()
    assert not product.image
    assert not (media_root / "products").exists()


def test_back_office_list_shows_thumbnails(client, staff_user, product):
    client.force_login(staff_user)
    product.set_image(image_upload())
    product.save()

    page = client.get(reverse("products:manage_products")).content.decode()

    assert product.image.url in page
