from django import forms
from django.utils.translation import gettext_lazy as _

from .models import HomeworkSubmission

ALLOWED = (".zip", ".pdf", ".txt", ".md", ".py", ".png", ".jpg", ".jpeg", ".yml", ".yaml", ".json")


class HomeworkForm(forms.ModelForm):
    class Meta:
        model = HomeworkSubmission
        fields = ("text", "link", "file")
        widgets = {
            "text": forms.Textarea(attrs={"class": "field", "rows": 4, "placeholder": _("Javobingiz, izohlar yoki kod...")}),
            "link": forms.URLInput(attrs={"class": "field", "placeholder": "https://github.com/username/repo"}),
            "file": forms.ClearableFileInput(attrs={"class": "field"}),
        }

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if f:
            if f.size > 20 * 1024 * 1024:
                raise forms.ValidationError(_("Fayl hajmi 20 MB dan oshmasin"))
            if not f.name.lower().endswith(ALLOWED):
                raise forms.ValidationError(_("Bu turdagi fayl qabul qilinmaydi"))
        return f

    def clean(self):
        data = super().clean()
        if not (data.get("text") or data.get("link") or data.get("file")):
            raise forms.ValidationError(_("Javob, havola yoki fayldan kamida bittasini yuboring"))
        return data
