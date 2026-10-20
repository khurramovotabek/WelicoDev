from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display

from apps.core.admin_mixins import TranslatedAdmin
from apps.portfolio.admin import thumb

from .models import Album, MediaCategory, Photo, Playlist, Track, Video


@admin.register(MediaCategory)
class MediaCategoryAdmin(TranslatedAdmin):
    list_display = ("name", "kind", "order")
    list_filter = ("kind",)
    list_editable = ("order",)


@admin.register(Album)
class AlbumAdmin(TranslatedAdmin):
    list_display = ("title", "location", "is_published", "created_at")
    search_fields = ("title",)


@admin.register(Photo)
class PhotoAdmin(TranslatedAdmin):
    list_display = ("preview", "title", "album", "category", "location", "taken_at", "is_featured", "is_published", "views_count")
    list_display_links = ("preview", "title")
    list_filter = ("category", "album", "is_featured", "is_published")
    list_editable = ("is_featured", "is_published")
    search_fields = ("title", "location")
    autocomplete_fields = ("tags",)

    @display(description="")
    def preview(self, obj):
        return thumb(obj.image)


@admin.register(Video)
class VideoAdmin(TranslatedAdmin):
    list_display = ("preview", "title", "category", "duration", "recorded_at", "is_published", "views_count")
    list_display_links = ("preview", "title")
    list_filter = ("category", "is_published")
    search_fields = ("title",)
    autocomplete_fields = ("tags",)

    @display(description="")
    def preview(self, obj):
        return thumb(obj.thumbnail)


@admin.register(Track)
class TrackAdmin(ModelAdmin):
    list_display = ("preview", "title", "artist", "category", "duration", "is_favorite", "is_published", "order")
    list_display_links = ("preview", "title")
    list_editable = ("is_favorite", "is_published", "order")
    list_filter = ("category", "is_favorite")
    search_fields = ("title", "artist")

    @display(description="")
    def preview(self, obj):
        return thumb(obj.cover, 36)


@admin.register(Playlist)
class PlaylistAdmin(TranslatedAdmin):
    list_display = ("title", "order", "is_published")
    filter_horizontal = ("tracks",)
