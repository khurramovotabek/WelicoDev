from django import forms
from django.utils.translation import gettext_lazy as _

from .models import User


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "bio", "avatar", "language", "notify_news", "notify_comments")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "field"}),
            "last_name": forms.TextInput(attrs={"class": "field"}),
            "bio": forms.TextInput(attrs={"class": "field", "placeholder": _("O'zingiz haqingizda bir jumla")}),
            "avatar": forms.ClearableFileInput(attrs={"class": "field", "accept": "image/*"}),
            "language": forms.Select(attrs={"class": "field"}),
            "notify_news": forms.CheckboxInput(),
            "notify_comments": forms.CheckboxInput(),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar and hasattr(avatar, "size") and avatar.size > 3 * 1024 * 1024:
            raise forms.ValidationError(_("Rasm hajmi 3 MB dan oshmasin"))
        return avatar
