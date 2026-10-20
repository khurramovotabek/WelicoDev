from django.db.models import F

from .models import PageHero


def client_ip(request):
    # X-Real-IP'ni o'zimizning Nginx qo'yadi (mijoz yuborgan qiymatni almashtiradi)
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")


def get_hero(page):
    return PageHero.objects.filter(page=page).first()


def count_view(request, obj, field="views_count"):
    """Bir sessiyada bir obyekt ko'rishini faqat bir marta hisoblaydi."""
    key = f"viewed:{obj._meta.label_lower}:{obj.pk}"
    if request.session.get(key):
        return
    request.session[key] = True
    type(obj).objects.filter(pk=obj.pk).update(**{field: F(field) + 1})
    setattr(obj, field, getattr(obj, field) + 1)
