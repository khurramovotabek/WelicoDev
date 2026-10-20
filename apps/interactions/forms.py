from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Comment, ContactMessage, Review

ALLOWED_ATTACHMENTS = (".png", ".jpg", ".jpeg", ".webp", ".pdf", ".doc", ".docx", ".zip", ".txt")


class ContactForm(forms.ModelForm):
    # Botlar to'ldiradigan yashirin maydon
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = ContactMessage
        fields = ("name", "email", "subject", "message", "attachment")
        widgets = {
            "name": forms.TextInput(attrs={"class": "field", "placeholder": "John Doe", "autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"class": "field", "placeholder": "john@example.com", "autocomplete": "email"}),
            "subject": forms.TextInput(attrs={"class": "field", "placeholder": _("Loyiha bo'yicha hamkorlik")}),
            "message": forms.Textarea(attrs={"class": "field", "rows": 5, "placeholder": _("Loyihangiz yoki g'oyangiz haqida yozing...")}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None and user.is_authenticated and not self.is_bound:
            self.initial.setdefault("name", user.get_full_name())

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("spam")
        return ""

    def clean_attachment(self):
        f = self.cleaned_data.get("attachment")
        if f:
            if f.size > 10 * 1024 * 1024:
                raise forms.ValidationError(_("Fayl hajmi 10 MB dan oshmasin"))
            if not f.name.lower().endswith(ALLOWED_ATTACHMENTS):
                raise forms.ValidationError(_("Bu turdagi fayl qabul qilinmaydi"))
        return f


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("body",)
        widgets = {"body": forms.Textarea(attrs={"class": "field min-h-[46px]", "rows": 1, "placeholder": _("Izoh yozing..."), "maxlength": 2000})}

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if len(body) < 2:
            raise forms.ValidationError(_("Izoh juda qisqa"))
        return body


class ReviewForm(forms.ModelForm):
    rating = forms.IntegerField(min_value=1, max_value=5)

    class Meta:
        model = Review
        fields = ("rating", "body")
        widgets = {"body": forms.Textarea(attrs={"class": "field", "rows": 3, "placeholder": _("Fikringizni yozing..."), "maxlength": 1000})}
