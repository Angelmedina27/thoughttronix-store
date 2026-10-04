"""Back-office forms for the catalog models.

ModelForms inherit the models' own rules (name required, slug unique);
the explicit ``price`` declaration and ``clean_image`` add the rules the
model doesn't carry — the price must be positive and an image at most
5 MB. Widgets get their DaisyUI classes in one shared ``__init__`` loop,
as on ``CheckoutForm``.
"""

from decimal import Decimal

from django import forms

from .models import Category, Product, Tag, validate_image_extension

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


class StyledModelForm(forms.ModelForm):
    """Base form that dresses every widget in DaisyUI classes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.ClearableFileInput):
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


class ProductImageField(forms.ImageField):
    """An image field that checks the extension before Pillow opens the file.

    Django's own ImageField verifies the content first and then allows
    every format Pillow knows, so a wrong file type would get a vague
    "not an image" error or a list of ~70 formats. Checking first gives
    the short allowed-formats message.
    """

    default_validators = []  # replaced by the stricter check in to_python

    def to_python(self, data):
        if data:
            validate_image_extension(data)
        return super().to_python(data)


class ProductForm(StyledModelForm):
    price = forms.DecimalField(
        label="Price (USD)",
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
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
            "image",
        ]
        field_classes = {"image": ProductImageField}

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > MAX_IMAGE_SIZE:
            raise forms.ValidationError("Image must be 5 MB or smaller.")
        return image


class CategoryForm(StyledModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug"]


class TagForm(StyledModelForm):
    class Meta:
        model = Tag
        fields = ["name", "slug"]
