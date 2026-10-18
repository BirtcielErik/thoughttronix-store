"""The customer review form.

The form owns the review's validation: a rating that is one of the five
stars, and a comment that is required, at most 2,000 characters, and not
just whitespace (``CharField`` strips it, so blank-after-stripping fails
``required``). The rating input is rendered by hand as DaisyUI's star
``rating``, so the widget here only carries the choices.
"""

from django import forms

from .models import Review

RATING_CHOICES = [(stars, stars) for stars in range(1, 6)]


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES,
        coerce=int,
        widget=forms.RadioSelect,
        error_messages={"required": "Choose a star rating."},
    )

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "comment": forms.Textarea(
                attrs={
                    "class": "textarea w-full",
                    "rows": 4,
                    "placeholder": "What did you think? Be honest. We'll know.",
                }
            ),
        }
        error_messages = {"comment": {"required": "Write a comment."}}
