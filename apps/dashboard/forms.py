from django import forms
from django.conf import settings
from django.forms import modelformset_factory
from django.utils.translation import gettext_lazy as _
from django_ckeditor_5.widgets import CKEditor5Widget

from apps.blog.models import Article
from apps.core.models import SiteSettings, SocialLink, Tag
from apps.portfolio.models import Project, Skill
from apps.telegram_bot.models import BotSettings, Broadcast

LANGS = [code for code, _name in settings.LANGUAGES]


def tr(*names):
    """['title'] -> ['title_uz', 'title_ru', 'title_en']"""
    return [f"{n}_{lang}" for n in names for lang in LANGS]


class StyledMixin:
    """Barcha maydonlarga dizayn klassini qo'shadi."""

    def _style(self):
        for name, field in self.fields.items():
            w = field.widget
            if isinstance(w, (forms.CheckboxInput, CKEditor5Widget)):
                continue
            if isinstance(w, forms.CheckboxSelectMultiple):
                continue
            css = w.attrs.get("class", "")
            w.attrs["class"] = f"{css} field".strip()


class TagField(forms.CharField):
    """Vergul bilan ajratilgan teglar: "django, api" -> [Tag, Tag]"""

    def prepare_value(self, value):
        if isinstance(value, (list, tuple)):
            return ", ".join(t.name if isinstance(t, Tag) else str(Tag.objects.filter(pk=t).first() or "") for t in value)
        return value

    def clean(self, value):
        value = super().clean(value)
        names = [n.strip() for n in (value or "").split(",") if n.strip()]
        return [Tag.objects.get_or_create(name=n[:50])[0] for n in names]


class TagsMixin:
    """`tags` maydonini taggit'ga saqlaydi (commit=False bo'lsa save_m2m orqali)."""

    def save(self, commit=True):
        obj = super().save(commit=commit)
        if commit:
            obj.tags.set(self.cleaned_data["tags"])
        else:
            original = self.save_m2m

            def save_m2m():
                original()
                obj.tags.set(self.cleaned_data["tags"])

            self.save_m2m = save_m2m
        return obj


class ProjectForm(TagsMixin, StyledMixin, forms.ModelForm):
    tags = TagField(label=_("Teglar"), required=False, help_text=_("Vergul bilan ajrating"))

    class Meta:
        model = Project
        fields = [
            *tr("title", "subtitle", "short_description", "description"),
            "slug", "category", "tech_stack", "cover", "video", "video_url", "video_duration",
            "live_url", "source_url", *tr("project_type", "role", "duration", "team_size"), "completed_year",
            "is_featured", "allow_comments", "allow_reviews", "order",
            *tr("meta_title", "meta_description"),
        ]
        widgets = {
            **{f"description_{l}": CKEditor5Widget(config_name="default") for l in LANGS},
            **{f"short_description_{l}": forms.Textarea(attrs={"rows": 2, "maxlength": 200}) for l in LANGS},
            **{f"meta_description_{l}": forms.Textarea(attrs={"rows": 2, "maxlength": 170}) for l in LANGS},
            "tech_stack": forms.CheckboxSelectMultiple(attrs={"class": "sr-only"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tech_stack"].queryset = Skill.objects.order_by("name")
        self.fields["slug"].required = False
        self.fields["title_uz"].required = True
        self.fields["short_description_uz"].required = True
        if self.instance.pk:
            self.initial["tags"] = ", ".join(self.instance.tags.values_list("name", flat=True))
        self._style()



class ArticleForm(TagsMixin, StyledMixin, forms.ModelForm):
    tags = TagField(label=_("Teglar"), required=False)

    class Meta:
        model = Article
        fields = [
            *tr("title", "excerpt", "content"), "slug", "focus_keyword", "cover", "category", "status", "published_at",
            "is_featured", "allow_comments", *tr("meta_title", "meta_description"),
        ]
        widgets = {
            **{f"content_{l}": CKEditor5Widget(config_name="default") for l in LANGS},
            **{f"excerpt_{l}": forms.Textarea(attrs={"rows": 2, "maxlength": 300}) for l in LANGS},
            **{f"meta_description_{l}": forms.Textarea(attrs={"rows": 2, "maxlength": 170}) for l in LANGS},
            "published_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False
        self.fields["title_uz"].required = True
        self.fields["excerpt_uz"].required = True
        self.fields["content_uz"].required = True
        if self.instance.pk:
            self.initial["tags"] = ", ".join(self.instance.tags.values_list("name", flat=True))
        self._style()


class BroadcastForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Broadcast
        fields = ["title", "text", "image", "button_text", "button_url", "audience", "course", "scheduled_at"]
        widgets = {
            "text": CKEditor5Widget(config_name="telegram"),
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean(self):
        data = super().clean()
        if bool(data.get("button_text")) != bool(data.get("button_url")):
            raise forms.ValidationError(_("Tugma uchun matn va havola birga kiritilishi kerak"))
        if data.get("audience") == Broadcast.Audience.COURSE and not data.get("course"):
            raise forms.ValidationError(_("Kursni tanlang"))
        from apps.telegram_bot.formatting import html_to_telegram, visible_length

        if data.get("image") and visible_length(html_to_telegram(data.get("text") or "")) > 1024:
            raise forms.ValidationError(_("Rasmli xabar matni 1024 belgidan oshmasligi kerak (Telegram cheklovi)"))
        return data


class BotSettingsForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = BotSettings
        fields = [
            "is_enabled", *tr(*BotSettings.RICH_FIELDS, "mini_app_button_text"),
            "notify_new_user", "notify_new_comment", "notify_new_review", "notify_contact_message", "notify_homework",
            "channel_id", "auto_post_articles", "auto_post_lessons",
        ]
        widgets = {f: CKEditor5Widget(config_name="telegram") for f in tr(*BotSettings.RICH_FIELDS)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class ReplyForm(forms.Form):
    text = forms.CharField(max_length=4000, widget=forms.Textarea(attrs={"rows": 2, "class": "field", "placeholder": _("Xabar yozing...")}))


class SiteSettingsForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            "brand_name", *tr("brand_tagline"), "logo", "favicon",
            "owner_name", *tr("owner_role", "owner_bio", "hero_badges"), "avatar", "portrait", "cv_file",
            "background_preset", "background_image", "background_dim", "background_blur", "background_motion",
            "payment_telegram", *tr("payment_note"),
            "latitude", "longitude", "map_zoom", "timezone_name",
            "intro_video_url", "intro_video_duration", "available_for_work", "years_experience", "people_impacted",
            "google_verification", "yandex_verification", "bing_verification", "indexnow_key", "umami_script_url", "umami_website_id",
            "email", "phone", *tr("location", "working_hours", "response_time"), "map_url", "timezone_label",
            *tr("meta_description", "footer_text"), "og_image",
        ]
        widgets = {
            **{f"owner_bio_{l}": forms.Textarea(attrs={"rows": 4}) for l in LANGS},
            **{f"payment_note_{l}": forms.Textarea(attrs={"rows": 3}) for l in LANGS},
            "background_preset": forms.RadioSelect,
            "background_dim": forms.NumberInput(attrs={"type": "range", "min": 0, "max": 80, "step": 1}),
            "background_blur": forms.NumberInput(attrs={"type": "range", "min": 0, "max": 24, "step": 1}),
            "latitude": forms.NumberInput(attrs={"step": "0.000001"}),
            "longitude": forms.NumberInput(attrs={"step": "0.000001"}),
            "map_zoom": forms.NumberInput(attrs={"min": 3, "max": 18}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
        for name in ("background_preset", "background_dim", "background_blur"):
            self.fields[name].widget.attrs.pop("class", None)

    def clean_background_dim(self):
        return max(0, min(80, self.cleaned_data["background_dim"] or 0))

    def clean_background_blur(self):
        return max(0, min(24, self.cleaned_data["background_blur"] or 0))

    def clean_map_zoom(self):
        return max(3, min(18, self.cleaned_data["map_zoom"] or 12))

    def clean_timezone_name(self):
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        value = (self.cleaned_data["timezone_name"] or "Asia/Tashkent").strip()
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise forms.ValidationError(_("Noto'g'ri vaqt zonasi. Masalan: Asia/Tashkent"))
        return value

    def clean_payment_telegram(self):
        value = self.cleaned_data["payment_telegram"].strip().lstrip("@").replace("https://t.me/", "")
        if value and not value.replace("_", "").isalnum():
            raise forms.ValidationError(_("Faqat Telegram username: harf, raqam va _"))
        return value


class SocialLinkForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = SocialLink
        fields = ["platform", "label", "url", "order", "is_active", "show_in_header", "show_in_footer", "show_in_contact"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean_url(self):
        url = self.cleaned_data["url"].strip()
        if not url.startswith(("https://", "http://", "mailto:", "tel:")):
            raise forms.ValidationError(_("Havola https://, mailto: yoki tel: bilan boshlanishi kerak"))
        return url


SocialLinkFormSet = modelformset_factory(SocialLink, form=SocialLinkForm, extra=1, can_delete=True)


# --------------------------------------------------------------------------- Kanal, musiqa, tajriba, ko'nikmalar

from apps.gallery.models import MediaCategory, Playlist, Track  # noqa: E402
from apps.portfolio.models import Experience, SkillCategory  # noqa: E402
from apps.telegram_bot.models import ChannelPost  # noqa: E402

AUDIO_EXT = (".mp3", ".m4a", ".ogg", ".wav", ".aac", ".flac")


class ChannelPostForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = ChannelPost
        fields = ["title", "body", "image", "button_text", "button_url", "disable_preview", "silent", "pin", "scheduled_at"]
        widgets = {
            "body": CKEditor5Widget(config_name="telegram"),
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean(self):
        data = super().clean()
        if bool(data.get("button_text")) != bool(data.get("button_url")):
            raise forms.ValidationError(_("Tugma uchun matn va havola birga kiritilishi kerak"))
        return data


class TrackForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Track
        fields = ["title", "artist", "album", "year", "audio", "external_url", "cover", "duration", "category",
                  *tr("note"), "is_favorite", "is_published", "order"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = MediaCategory.objects.filter(kind="music")
        self._style()

    def clean_audio(self):
        f = self.cleaned_data.get("audio")
        if f and hasattr(f, "size"):
            if f.size > 30 * 1024 * 1024:
                raise forms.ValidationError(_("Audio fayl 30 MB dan oshmasin"))
            if not f.name.lower().endswith(AUDIO_EXT):
                raise forms.ValidationError(_("MP3, M4A, OGG, WAV, AAC yoki FLAC fayl yuklang"))
        return f

    def clean(self):
        data = super().clean()
        if not data.get("audio") and not data.get("external_url") and not (self.instance.pk and self.instance.audio):
            raise forms.ValidationError(_("Audio fayl yuklang yoki tashqi havola kiriting"))
        return data


class PlaylistForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Playlist
        fields = [*tr("title"), "cover", "tracks", "order", "is_published"]
        widgets = {"tracks": forms.CheckboxSelectMultiple(attrs={"class": "sr-only"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class ExperienceForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Experience
        fields = [
            "kind", "company", "slug", "logo", *tr("role", "degree", "field_of_study", "location", "summary"),
            "grade", "start_date", "end_date", "is_current", *tr("description", "achievements", "quote"),
            "website", "map_url", *tr("company_description", "company_industry"), "team_size", "products_count",
            "technologies", "is_published", "order",
        ]
        widgets = {
            **{f"{n}_{l}": CKEditor5Widget(config_name="default") for n in ("description", "achievements") for l in LANGS},
            **{f"summary_{l}": forms.Textarea(attrs={"rows": 3}) for l in LANGS},
            **{f"company_description_{l}": forms.Textarea(attrs={"rows": 3}) for l in LANGS},
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "technologies": forms.CheckboxSelectMultiple(attrs={"class": "sr-only"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False
        self.fields["technologies"].queryset = Skill.objects.order_by("name")
        self.fields["role_uz"].required = True
        self.fields["summary_uz"].required = True
        self._style()


class SkillForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Skill
        fields = ["name", "category", *tr("subtitle"), "devicon", "icon", "level", "proficiency", "years",
                  "started_year", "is_featured", "is_learning", "learning_progress", "order"]
        widgets = {
            "proficiency": forms.NumberInput(attrs={"type": "range", "min": 0, "max": 100, "step": 5}),
            "learning_progress": forms.NumberInput(attrs={"type": "range", "min": 0, "max": 100, "step": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = SkillCategory.objects.all()
        self._style()
