from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils.feedgenerator import Atom1Feed

from apps.core.models import SiteSettings

from .models import Article


class LatestArticlesFeed(Feed):
    feed_type = Atom1Feed

    def title(self):
        s = SiteSettings.load()
        return f"{s.brand_name} Blog"

    def subtitle(self):
        return SiteSettings.load().meta_description

    def link(self):
        return reverse("blog:article_list")

    def items(self):
        return Article.objects.published()[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt

    def item_pubdate(self, item):
        return item.published_at

    def item_updateddate(self, item):
        return item.updated_at

    def item_categories(self, item):
        return [t.name for t in item.tags.all()]
