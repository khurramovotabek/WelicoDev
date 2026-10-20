from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.core.utils import count_view, get_hero
from apps.interactions.models import Comment
from apps.interactions.services import annotate_stats, user_reactions

from .models import Article, ArticleCategory, Subscriber


def _sidebar():
    published = Article.objects.published()
    year = timezone.now().year
    monthly = (
        published.filter(published_at__year=year).annotate(m=TruncMonth("published_at"))
        .values("m").annotate(n=Count("id")).order_by("m")
    )
    per_month = {row["m"].month: row["n"] for row in monthly}
    peak = max(per_month.values(), default=1)
    return {
        "topics": ArticleCategory.objects.annotate(n=Count("articles", filter=Q(articles__status="published"))).filter(n__gt=0).order_by("-n"),
        "stats": {
            "articles": published.count(),
            "reads": published.aggregate(v=Sum("views_count"))["v"] or 0,
            "comments": Comment.objects.filter(content_type__model="article", is_approved=True).count(),
        },
        "writing": [(m, per_month.get(m, 0), round(per_month.get(m, 0) * 100 / peak)) for m in range(1, 13)],
        "year": year,
    }


def article_list(request):
    articles = Article.objects.published().select_related("category")
    category = request.GET.get("category", "")
    q = request.GET.get("q", "").strip()
    if category:
        articles = articles.filter(category__slug=category)
    if q:
        articles = articles.filter(Q(title__icontains=q) | Q(excerpt__icontains=q))
    featured = None
    if not category and not q:
        featured = Article.objects.published().filter(is_featured=True).first()
        if featured:
            articles = articles.exclude(pk=featured.pk)
    ctx = {
        "hero": get_hero("journal"),
        "categories": ArticleCategory.objects.filter(articles__status="published").distinct(),
        "active_category": category,
        "q": q,
        "featured": featured,
        "articles": annotate_stats(articles)[:24],
        **_sidebar(),
    }
    return render(request, "blog/articles.html", ctx)


def article_detail(request, slug):
    article = get_object_or_404(Article.objects.published().select_related("category", "author").prefetch_related("tags", "images"), slug=slug)
    count_view(request, article)
    published = Article.objects.published()
    from apps.core import seo
    from apps.core.models import SiteSettings

    return render(request, "blog/article_detail.html", {
        "article": article,
        "jsonld": seo.article(article, SiteSettings.load()),
        "categories": ArticleCategory.objects.filter(articles__status="published").distinct(),
        "related": published.exclude(pk=article.pk).filter(category=article.category)[:4]
        or published.exclude(pk=article.pk)[:4],
        "prev_article": published.filter(published_at__lt=article.published_at).first(),
        "next_article": published.filter(published_at__gt=article.published_at).order_by("published_at").first(),
        "reactions": user_reactions(request.user, article),
        "comments_total": Comment.objects.filter(content_type__model="article", object_id=article.pk, is_approved=True).count(),
    })


@require_POST
def subscribe(request):
    email = request.POST.get("email", "").strip().lower()
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError

    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, _("Email manzil noto'g'ri"))
    else:
        Subscriber.objects.update_or_create(email=email, defaults={"is_active": True, "language": request.LANGUAGE_CODE})
        messages.success(request, _("Obuna bo'ldingiz! Yangi maqolalar emailingizga keladi."))
    return redirect(request.POST.get("next") or "blog:article_list")
