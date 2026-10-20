from modeltranslation.translator import TranslationOptions, register

from .models import Article, ArticleCategory, ArticleImage


@register(ArticleCategory)
class ArticleCategoryTR(TranslationOptions):
    fields = ("name",)


@register(Article)
class ArticleTR(TranslationOptions):
    fields = ("title", "excerpt", "content", "meta_title", "meta_description")


@register(ArticleImage)
class ArticleImageTR(TranslationOptions):
    fields = ("caption",)
