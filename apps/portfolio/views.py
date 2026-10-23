from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from apps.core.charts import donut, line_area
from apps.core.models import CurrentStatus
from apps.core.utils import count_view, get_hero
from apps.interactions.services import annotate_stats, rating_summary, user_reactions

from .models import Experience, Interest, JourneyStep, Project, ProjectCategory, Skill, SkillCategory


def about(request):
    categories = SkillCategory.objects.prefetch_related("skills").all()[:4]
    return render(request, "portfolio/about.html", {
        "hero": get_hero("about"),
        "statuses": CurrentStatus.objects.filter(is_active=True),
        "skill_categories": categories,
        "interests": Interest.objects.all()[:6],
        "journey": JourneyStep.objects.all(),
        "projects_count": Project.objects.published().count(),
    })


def skills(request):
    category = request.GET.get("category", "")
    q = request.GET.get("q", "").strip()
    all_skills = Skill.objects.select_related("category")
    if category:
        all_skills = all_skills.filter(category__slug=category)
    if q:
        all_skills = all_skills.filter(name__icontains=q)

    levels = {lvl: Skill.objects.filter(level=lvl).count() for lvl, _label in Skill.Level.choices}
    years = list(Skill.objects.exclude(started_year=None).values_list("started_year", flat=True))
    timeline = []
    if years:
        for y in range(min(years), max(years) + 1):
            timeline.append((y, sum(1 for v in years if v <= y)))

    return render(request, "portfolio/skills.html", {
        "hero": get_hero("skills"),
        "categories": SkillCategory.objects.annotate(n=Count("skills")),
        "active_category": category,
        "q": q,
        "featured": Skill.objects.filter(is_featured=True).select_related("category")[:8],
        "skills": all_skills,
        "learning": Skill.objects.filter(is_learning=True)[:4],
        "levels": levels,
        "total": Skill.objects.count(),
        "chart": line_area(timeline),
        "level_donut": donut([(label, levels[lvl]) for lvl, label in reversed(Skill.Level.choices)]),
        "projects_count": Project.objects.published().count(),
    })


def project_list(request):
    projects = Project.objects.published().select_related("category").prefetch_related("tags")
    category = request.GET.get("category", "")
    q = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "latest")
    if category:
        projects = projects.filter(category__slug=category)
    if q:
        projects = projects.filter(Q(title__icontains=q) | Q(short_description__icontains=q) | Q(tags__name__icontains=q)).distinct()
    projects = projects.order_by({"popular": "-views_count", "oldest": "created_at"}.get(sort, "-created_at"))

    featured = Project.objects.published().filter(is_featured=True).prefetch_related("tags", "images").first()
    ctx = {
        "hero": get_hero("projects"),
        "categories": ProjectCategory.objects.filter(projects__status="published").distinct(),
        "active_category": category,
        "q": q,
        "sort": sort,
        "featured": featured,
        "featured_rating": rating_summary(featured) if featured else None,
        "projects": annotate_stats(projects.exclude(pk=featured.pk) if featured and not (category or q) else projects),
        "total": Project.objects.published().count(),
    }
    if request.htmx and request.htmx.target == "project-grid":
        return render(request, "portfolio/partials/project_grid.html", ctx)
    return render(request, "portfolio/projects.html", ctx)


def project_detail(request, slug):
    project = get_object_or_404(
        Project.objects.published().prefetch_related("tags", "tech_stack", "images", "features", "challenges", "results"),
        slug=slug,
    )
    count_view(request, project)
    related = (
        Project.objects.published().exclude(pk=project.pk)
        .filter(Q(category=project.category) | Q(tags__in=project.tags.all())).distinct()[:2]
    )
    rating = rating_summary(project)
    from apps.core import seo

    return render(request, "portfolio/project_detail.html", {
        "project": project,
        "jsonld": seo.project(project, rating),
        "rating": rating,
        "related": related,
        "reactions": user_reactions(request.user, project),
    })


def experience_list(request):
    kind = request.GET.get("kind", "")
    items = Experience.objects.filter(is_published=True).prefetch_related("technologies")
    education = list(items.filter(kind=Experience.Kind.EDUCATION).order_by("-start_date"))
    if kind:
        items = items.filter(kind=kind)
    elif education:
        # Ta'lim alohida bo'limda ko'rsatiladi
        items = items.exclude(kind=Experience.Kind.EDUCATION)
    all_items = Experience.objects.filter(is_published=True)
    # order_by() — Meta.ordering GROUP BY'ga qo'shilib, har yozuvni alohida guruh qilmasin
    by_kind = all_items.order_by().values("kind").annotate(n=Count("id")).order_by("-n")
    distribution = donut([(Experience.Kind(r["kind"]).label, r["n"]) for r in by_kind])
    return render(request, "portfolio/experience.html", {
        "hero": get_hero("experience"),
        "items": items,
        "education": education if not kind else [],
        "kinds": Experience.Kind.choices,
        "active_kind": kind,
        "skill_categories": SkillCategory.objects.prefetch_related("skills"),
        "distribution": distribution,
        "projects_count": Project.objects.published().count(),
        "tech_count": Skill.objects.count(),
    })


def experience_detail(request, slug):
    exp = get_object_or_404(
        Experience.objects.filter(is_published=True).prefetch_related(
            "technologies", "responsibilities", "milestones", "images", "projects__tags",
        ),
        slug=slug,
    )
    return render(request, "portfolio/experience_detail.html", {
        "exp": exp,
        "related": Experience.objects.filter(is_published=True).exclude(pk=exp.pk)[:2],
    })
