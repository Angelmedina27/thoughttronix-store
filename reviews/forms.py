"""The customer review form.

Both rules are declarative: the rating is a 1–5 choice, and the comment
has a 20-character minimum, measured after ``CharField`` trims it — so
whitespace padding doesn't count. The rating renders as DaisyUI star
radios in the template; no JavaScript.
"""

from django import forms

from .models import Review

RATING_CHOICES = [(n, f"{n} star{'s' if n > 1 else ''}") for n in range(1, 6)]

MIN_COMMENT_LENGTH = 20


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES,
        coerce=int,
        widget=forms.RadioSelect,
        error_messages={"required": "Pick a rating from 1 to 5 stars."},
    )
    comment = forms.CharField(
        min_length=MIN_COMMENT_LENGTH,
        label="Your review",
        help_text=f"At least {MIN_COMMENT_LENGTH} characters.",
        widget=forms.Textarea(attrs={"class": "textarea w-full", "rows": 6}),
        error_messages={
            "required": "Tell us how it went.",
            "min_length": (
                "Tell us a little more — reviews need at least "
                "%(limit_value)d characters (you wrote %(show_value)d)."
            ),
        },
    )

    class Meta:
        model = Review
        fields = ["rating", "comment"]
