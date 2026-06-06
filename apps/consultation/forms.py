from django import forms
from .models import VOTE_CHOICE


class VoteForm(forms.Form):
    choice = forms.ChoiceField(
        choices=VOTE_CHOICE.CHOICES,
        widget=forms.RadioSelect(attrs={"class": "sr-only vote-radio"}),
        label="Votre position",
    )
    justification = forms.CharField(
        widget=forms.Textarea(attrs={
            "placeholder": "Expliquez votre position en vous appuyant sur des faits, des articles constitutionnels ou votre vécu de citoyen...",
            "rows": 6,
            "class": "form-textarea",
            "maxlength": "2000",
        }),
        label="Justification (obligatoire)",
        max_length=2000,
        min_length=30,
        help_text="Minimum 30 caractères. Vous pouvez citer un article de la Constitution.",
    )
    cited_article_numbers = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Ex: 1, 35, 220",
            "class": "form-input",
        }),
        label="Articles cités (facultatif)",
        help_text="Numéros d'articles séparés par des virgules",
    )

    def clean_cited_article_numbers(self):
        raw = self.cleaned_data.get("cited_article_numbers", "")
        if not raw.strip():
            return []
        numbers = []
        for part in raw.split(","):
            part = part.strip()
            if part:
                try:
                    numbers.append(int(part))
                except ValueError:
                    raise forms.ValidationError(f"'{part}' n'est pas un numéro d'article valide.")
        return numbers
