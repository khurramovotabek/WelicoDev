from django.contrib.contenttypes.models import ContentType
from django.db.models import Avg, Count, FloatField, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce

from .models import Comment, Reaction, Review


def rating_summary(obj):
    if obj is None:
        return {"avg": 0, "count": 0}
    ct = ContentType.objects.get_for_model(obj)
    data = Review.objects.filter(content_type=ct, object_id=obj.pk, is_approved=True).aggregate(avg=Avg("rating"), count=Count("id"))
    return {"avg": round(data["avg"] or 0, 1), "count": data["count"]}


def annotate_stats(queryset):
    """Ro'yxatlar uchun: har bir obyektga rating_avg, rating_count, comments_n, likes_n qo'shadi (N+1 so'rovsiz)."""
    ct = ContentType.objects.get_for_model(queryset.model)

    def sub(model, expr, extra=None, output=IntegerField()):
        qs = model.objects.filter(content_type=ct, object_id=OuterRef("pk"), **(extra or {}))
        return Coalesce(Subquery(qs.values("object_id").annotate(v=expr).values("v")[:1], output_field=output), Value(0), output_field=output)

    return queryset.annotate(
        rating_avg=sub(Review, Avg("rating"), {"is_approved": True}, FloatField()),
        rating_count=sub(Review, Count("id"), {"is_approved": True}),
        comments_n=sub(Comment, Count("id"), {"is_approved": True}),
        likes_n=sub(Reaction, Count("id"), {"kind": Reaction.Kind.LIKE}),
    )


def user_reactions(user, obj):
    if not user.is_authenticated:
        return set()
    ct = ContentType.objects.get_for_model(obj)
    return set(Reaction.objects.filter(user=user, content_type=ct, object_id=obj.pk).values_list("kind", flat=True))


def reaction_count(obj, kind):
    ct = ContentType.objects.get_for_model(obj)
    return Reaction.objects.filter(content_type=ct, object_id=obj.pk, kind=kind).count()
