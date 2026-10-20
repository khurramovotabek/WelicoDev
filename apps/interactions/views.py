"""Izoh, sharh, like/saqlash va ulashish. Barcha so'rovlar HTMX orqali keladi."""

import json

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import IntegrityError
from django.db.models import F, Prefetch
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.blog.models import Article
from apps.education.models import Course
from apps.gallery.models import Photo, Video
from apps.portfolio.models import Project

from .forms import CommentForm, ReviewForm
from .models import Comment, CommentLike, Reaction, Review, ShareEvent
from .notify import notify_admins_comment, notify_admins_review
from .services import rating_summary, reaction_count, user_reactions

# URL'dagi qisqa nom -> model. Faqat shu obyektlarga izoh/sharh yozish mumkin.
TARGETS = {
    "project": Project,
    "article": Article,
    "photo": Photo,
    "video": Video,
    "course": Course,
}


def _target(kind, pk):
    model = TARGETS.get(kind)
    if model is None:
        raise Http404
    obj = get_object_or_404(model, pk=pk)
    status = getattr(obj, "status", "published")
    if status != "published" or not getattr(obj, "is_published", True):
        raise Http404
    return obj


def _throttle(request, action, limit, seconds):
    key = f"throttle:{action}:{request.user.pk}"
    n = cache.get(key, 0)
    if n >= limit:
        return True
    cache.set(key, n + 1, seconds)
    return False


def _comments_qs(obj, user):
    ct = ContentType.objects.get_for_model(obj)
    replies = Comment.objects.filter(is_approved=True).select_related("user").order_by("created_at")
    qs = (
        Comment.objects.filter(content_type=ct, object_id=obj.pk, parent=None, is_approved=True)
        .select_related("user").prefetch_related(Prefetch("replies", queryset=replies))
    )
    return ct, qs


def comment_list(request, kind, pk):
    obj = _target(kind, pk)
    ct, qs = _comments_qs(obj, request.user)
    order = request.GET.get("order", "newest")
    qs = qs.order_by("-is_pinned", "created_at" if order == "oldest" else "-created_at")
    limit = int(request.GET.get("limit", 5))
    liked = set()
    if request.user.is_authenticated:
        liked = set(CommentLike.objects.filter(user=request.user, comment__object_id=obj.pk, comment__content_type=ct).values_list("comment_id", flat=True))
    return render(request, "interactions/comments.html", {
        "obj": obj, "kind": kind, "comments": qs[:limit], "total": qs.count(), "limit": limit,
        "next_limit": limit + 5, "order": order, "liked": liked, "form": CommentForm(),
        "allow": getattr(obj, "allow_comments", True),
    })


@require_POST
def comment_create(request, kind, pk):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    obj = _target(kind, pk)
    if not getattr(obj, "allow_comments", True) or request.user.is_blocked:
        return HttpResponseForbidden()
    if _throttle(request, "comment", 5, 60):
        return HttpResponse(status=429)
    form = CommentForm(request.POST)
    if form.is_valid():
        parent = None
        if request.POST.get("parent"):
            parent = Comment.objects.filter(pk=request.POST["parent"], object_id=obj.pk, parent=None).first()
        comment = form.save(commit=False)
        comment.user = request.user
        comment.target = obj
        comment.parent = parent
        comment.save()
        url = request.build_absolute_uri(obj.get_absolute_url()) + "#comments"
        notify_admins_comment(comment, url)
        if parent and parent.user_id != request.user.pk:
            from .notify import notify_reply

            notify_reply(parent, comment, url)
    return comment_list(request, kind, pk)


@require_POST
def comment_like(request, pk):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    comment = get_object_or_404(Comment, pk=pk, is_approved=True)
    like = CommentLike.objects.filter(comment=comment, user=request.user).first()
    if like:
        like.delete()
        Comment.objects.filter(pk=pk).update(likes_count=F("likes_count") - 1)
        liked = False
    else:
        try:
            CommentLike.objects.create(comment=comment, user=request.user)
            Comment.objects.filter(pk=pk).update(likes_count=F("likes_count") + 1)
        except IntegrityError:
            pass
        liked = True
    comment.refresh_from_db(fields=["likes_count"])
    return render(request, "interactions/partials/comment_like.html", {"c": comment, "is_liked": liked})


@require_POST
def comment_delete(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if not request.user.is_authenticated or (comment.user_id != request.user.pk and not request.user.is_staff):
        return HttpResponseForbidden()
    comment.delete()
    return HttpResponse("")


def review_list(request, kind, pk):
    obj = _target(kind, pk)
    ct = ContentType.objects.get_for_model(obj)
    reviews = Review.objects.filter(content_type=ct, object_id=obj.pk, is_approved=True).select_related("user")
    mine = None
    if request.user.is_authenticated:
        mine = Review.objects.filter(content_type=ct, object_id=obj.pk, user=request.user).first()
    return render(request, "interactions/reviews.html", {
        "obj": obj, "kind": kind, "reviews": reviews[:6], "rating": rating_summary(obj),
        "mine": mine, "form": ReviewForm(), "allow": getattr(obj, "allow_reviews", True),
    })


@require_POST
def review_create(request, kind, pk):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    obj = _target(kind, pk)
    if not getattr(obj, "allow_reviews", True) or request.user.is_blocked:
        return HttpResponseForbidden()
    form = ReviewForm(request.POST)
    if form.is_valid():
        ct = ContentType.objects.get_for_model(obj)
        review, _created = Review.objects.update_or_create(
            user=request.user, content_type=ct, object_id=obj.pk,
            defaults={"rating": form.cleaned_data["rating"], "body": form.cleaned_data["body"], "is_approved": False},
        )
        notify_admins_review(review, request.build_absolute_uri(obj.get_absolute_url()))
    resp = review_list(request, kind, pk)
    resp["HX-Trigger"] = json.dumps({"toast": {"value": _("Rahmat! Sharhingiz tekshiruvdan keyin chiqadi")}})
    return resp


@require_POST
def react(request, kind, pk, reaction):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    if reaction not in Reaction.Kind.values:
        raise Http404
    obj = _target(kind, pk)
    ct = ContentType.objects.get_for_model(obj)
    existing = Reaction.objects.filter(user=request.user, content_type=ct, object_id=obj.pk, kind=reaction)
    if existing.exists():
        existing.delete()
    else:
        Reaction.objects.get_or_create(user=request.user, content_type=ct, object_id=obj.pk, kind=reaction)
    return render(request, "interactions/partials/reaction_button.html", {
        "obj": obj, "kind": kind, "reaction": reaction,
        "active": reaction in user_reactions(request.user, obj),
        "count": reaction_count(obj, reaction),
    })


@require_POST
def track_share(request, kind, pk):
    obj = _target(kind, pk)
    platform = request.POST.get("platform", "other")
    if platform not in ShareEvent.Platform.values:
        platform = "other"
    ShareEvent.objects.create(
        target=obj, platform=platform, user=request.user if request.user.is_authenticated else None,
    )
    return HttpResponse(status=204)
