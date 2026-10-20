from django.http import HttpResponseRedirect
from django.urls import reverse
from modeltranslation.admin import TabbedTranslationAdmin, TranslationStackedInline, TranslationTabularInline
from unfold.admin import ModelAdmin, StackedInline, TabularInline


class TranslatedAdmin(ModelAdmin, TabbedTranslationAdmin):
    """Unfold ko'rinishi + har bir tarjima maydoni uchun uz/ru/en tablari."""

    compressed_fields = True
    warn_unsaved_form = True


class TranslatedTabularInline(TabularInline, TranslationTabularInline):
    extra = 0


class TranslatedStackedInline(StackedInline, TranslationStackedInline):
    extra = 0


class SingletonAdminMixin:
    """Bitta yozuvli modellar (sozlamalar): ro'yxat o'rniga to'g'ridan-to'g'ri tahrirlash sahifasi."""

    def has_add_permission(self, request):
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = self.model.load()
        opts = self.model._meta
        return HttpResponseRedirect(reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[obj.pk]))
