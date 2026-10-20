"""schema.org JSON-LD strukturalari (Google rich results uchun)."""

from django.conf import settings
from django.urls import reverse
from django.utils.html import strip_tags


def _abs(path):
    return f"{settings.SITE_URL}{path}" if path and path.startswith("/") else path


def site_graph(site, socials):
    """Har bir sahifada: Person (muallif) va WebSite (sayt ichida qidiruv bilan)."""
    person_id = f"{settings.SITE_URL}/#person"
    person = {
        "@type": "Person",
        "@id": person_id,
        "name": site.owner_name,
        "jobTitle": site.owner_role,
        "description": site.owner_bio,
        "url": settings.SITE_URL,
        "sameAs": [s.url for s in socials if s.url.startswith("http")],
        "address": {"@type": "PostalAddress", "addressLocality": site.location},
    }
    if site.avatar:
        person["image"] = _abs(site.avatar.url)
    if site.email:
        person["email"] = f"mailto:{site.email}"
    website = {
        "@type": "WebSite",
        "@id": f"{settings.SITE_URL}/#website",
        "url": settings.SITE_URL,
        "name": site.brand_name,
        "publisher": {"@id": person_id},
        "inLanguage": [code for code, _n in settings.LANGUAGES],
        "potentialAction": {
            "@type": "SearchAction",
            "target": {"@type": "EntryPoint", "urlTemplate": f"{settings.SITE_URL}{reverse('core:search')}?q={{search_term_string}}"},
            "query-input": "required name=search_term_string",
        },
    }
    return {"@context": "https://schema.org", "@graph": [person, website]}


def breadcrumbs(*items):
    """breadcrumbs(("Loyihalar", url), ("NutriZone", url))"""
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": str(name), "item": _abs(url)}
            for i, (name, url) in enumerate(items, start=1)
        ],
    }


def project(p, rating):
    data = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": p.title,
        "alternativeHeadline": p.subtitle,
        "description": p.short_description,
        "url": _abs(p.get_absolute_url()),
        "image": [_abs(p.cover.url), *[_abs(i.image.url) for i in p.images.all()[:5]]],
        "author": {"@id": f"{settings.SITE_URL}/#person"},
        "dateCreated": p.created_at.isoformat(),
        "dateModified": p.updated_at.isoformat(),
        "keywords": ", ".join([t.name for t in p.tags.all()] + [s.name for s in p.tech_stack.all()]),
    }
    if p.live_url:
        data["sameAs"] = p.live_url
    if rating and rating.get("count"):
        data["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": rating["avg"], "reviewCount": rating["count"], "bestRating": 5}
    return data


def article(a, site):
    return {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": a.title[:110],
        "description": a.excerpt,
        "image": _abs(a.cover.url),
        "url": _abs(a.get_absolute_url()),
        "mainEntityOfPage": _abs(a.get_absolute_url()),
        "datePublished": a.published_at.isoformat(),
        "dateModified": a.updated_at.isoformat(),
        "author": {"@id": f"{settings.SITE_URL}/#person", "@type": "Person", "name": site.owner_name},
        "publisher": {"@id": f"{settings.SITE_URL}/#person"},
        "keywords": ", ".join(t.name for t in a.tags.all()),
        "articleSection": a.category.name if a.category else None,
        "wordCount": len(strip_tags(a.content or "").split()),
        "timeRequired": f"PT{a.reading_minutes}M",
    }


def course(c, lessons, rating, site):
    data = {
        "@context": "https://schema.org",
        "@type": "Course",
        "name": c.title,
        "description": c.subtitle,
        "url": _abs(c.get_absolute_url()),
        "image": _abs(c.cover.url),
        "provider": {"@type": "Person", "@id": f"{settings.SITE_URL}/#person", "name": site.owner_name},
        "educationalLevel": c.get_level_display(),
        "inLanguage": "uz",
        "isAccessibleForFree": c.is_free,
        "hasCourseInstance": {
            "@type": "CourseInstance",
            "courseMode": "online",
            "courseWorkload": f"PT{max(1, c.total_seconds // 60)}M",
        },
        "syllabusSections": [{"@type": "Syllabus", "name": lesson.title, "timeRequired": f"PT{max(1, lesson.duration_seconds // 60)}M"} for lesson in lessons],
        "offers": {"@type": "Offer", "category": "Free" if c.is_free else "Paid", "price": str(c.price), "priceCurrency": "UZS"},
    }
    if rating and rating.get("count"):
        data["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": rating["avg"], "ratingCount": rating["count"], "bestRating": 5}
    return data


def lesson_video(lesson, youtube_id=""):
    """Bepul ko'rinadigan darslar uchun VideoObject (Google Video natijalari)."""
    thumb = lesson.thumbnail.url if lesson.thumbnail else lesson.course.cover.url
    data = {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": f"{lesson.order}. {lesson.title} — {lesson.course.title}",
        "description": lesson.summary or lesson.course.subtitle,
        "thumbnailUrl": _abs(thumb),
        "uploadDate": lesson.created_at.isoformat(),
        "duration": f"PT{lesson.duration_seconds // 60}M{lesson.duration_seconds % 60}S",
        "inLanguage": "uz",
        "isPartOf": {"@type": "Course", "name": lesson.course.title, "url": _abs(lesson.course.get_absolute_url())},
    }
    if youtube_id:
        data["embedUrl"] = f"https://www.youtube.com/embed/{youtube_id}"
    return data


def faq(items):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f.question, "acceptedAnswer": {"@type": "Answer", "text": f.answer}} for f in items
        ],
    }
