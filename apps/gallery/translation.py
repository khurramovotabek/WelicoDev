from modeltranslation.translator import TranslationOptions, register

from .models import Album, MediaCategory, Photo, Playlist, Track, Video


@register(MediaCategory)
class MediaCategoryTR(TranslationOptions):
    fields = ("name",)


@register(Album)
class AlbumTR(TranslationOptions):
    fields = ("title", "location")


@register(Photo)
class PhotoTR(TranslationOptions):
    fields = ("title", "description", "location")


@register(Video)
class VideoTR(TranslationOptions):
    fields = ("title", "description")


@register(Playlist)
class PlaylistTR(TranslationOptions):
    fields = ("title",)


@register(Track)
class TrackTR(TranslationOptions):
    fields = ("note",)
