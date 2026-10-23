from django.db.models import F
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from apps.core.utils import count_view, get_hero
from apps.interactions.services import annotate_stats, reaction_count, user_reactions

from .models import Album, MediaCategory, Photo, Playlist, Track, Video


def index(request):
    photo_cat = request.GET.get("photo", "")
    video_cat = request.GET.get("video", "")
    music_cat = request.GET.get("music", "")
    photos = Photo.objects.filter(is_published=True).select_related("album")
    videos = Video.objects.filter(is_published=True)
    # Pleyerga faqat audio fayli bor treklar; tashqi havolalilar (Spotify...) Musiqa sahifasida
    tracks = Track.objects.filter(is_published=True).exclude(audio="")
    if photo_cat:
        photos = photos.filter(category__slug=photo_cat)
    if video_cat:
        videos = videos.filter(category__slug=video_cat)
    if music_cat == "favorites":
        tracks = tracks.filter(is_favorite=True)
    elif music_cat:
        tracks = tracks.filter(category__slug=music_cat)

    ctx = {
        "hero": get_hero("media"),
        "now": timezone.localtime(),
        "photo_total": Photo.objects.filter(is_published=True).count(),
        "video_total": Video.objects.filter(is_published=True).count(),
        "track_total": Track.objects.filter(is_published=True).count(),
        "photo_categories": MediaCategory.objects.filter(kind="photo"),
        "video_categories": MediaCategory.objects.filter(kind="video"),
        "music_categories": MediaCategory.objects.filter(kind="music"),
        "photos": photos[:8],
        "photos_more": max(photos.count() - 8, 0),
        "videos": annotate_stats(videos)[:4],
        "videos_more": max(videos.count() - 4, 0),
        "tracks": tracks[:8],
        "playlists": Playlist.objects.filter(is_published=True).prefetch_related("tracks")[:4],
        "photo_cat": photo_cat, "video_cat": video_cat, "music_cat": music_cat,
    }
    if request.htmx and request.htmx.target in ("photos-grid", "videos-grid", "music-list"):
        return render(request, f"gallery/partials/{request.htmx.target}.html", ctx)
    return render(request, "gallery/index.html", ctx)


def photo_list(request):
    cat = request.GET.get("category", "")
    photos = Photo.objects.filter(is_published=True)
    if cat:
        photos = photos.filter(category__slug=cat)
    return render(request, "gallery/photo_list.html", {
        "hero": get_hero("media"), "photos": photos, "categories": MediaCategory.objects.filter(kind="photo"),
        "active": cat, "albums": Album.objects.filter(is_published=True),
    })


def video_list(request):
    cat = request.GET.get("category", "")
    videos = Video.objects.filter(is_published=True)
    if cat:
        videos = videos.filter(category__slug=cat)
    return render(request, "gallery/video_list.html", {
        "hero": get_hero("media"), "videos": annotate_stats(videos), "categories": MediaCategory.objects.filter(kind="video"), "active": cat,
    })


def photo_detail(request, slug):
    photo = get_object_or_404(Photo.objects.filter(is_published=True).select_related("album").prefetch_related("tags"), slug=slug)
    count_view(request, photo)
    siblings = Photo.objects.filter(is_published=True, album=photo.album) if photo.album else Photo.objects.filter(is_published=True)
    siblings = list(siblings[:24])
    index = next((i for i, p in enumerate(siblings) if p.pk == photo.pk), 0)
    return render(request, "gallery/photo_detail.html", {
        "photo": photo,
        "siblings": siblings,
        "index": index + 1,
        "prev": siblings[index - 1] if index > 0 else None,
        "next": siblings[index + 1] if index + 1 < len(siblings) else None,
        "reactions": user_reactions(request.user, photo),
        "likes": reaction_count(photo, "like"),
        "related_photos": Photo.objects.filter(is_published=True).exclude(pk=photo.pk)[:4],
        "related_videos": Video.objects.filter(is_published=True)[:2],
        "albums": Album.objects.filter(is_published=True).exclude(pk=photo.album_id)[:3],
        "location_albums": Album.objects.filter(is_published=True, location__iexact=photo.location).exclude(pk=photo.album_id)[:4] if photo.location else [],
    })


def photo_download(request, slug):
    photo = get_object_or_404(Photo, slug=slug, is_published=True)
    if not photo.allow_download:
        raise Http404
    Photo.objects.filter(pk=photo.pk).update(downloads_count=F("downloads_count") + 1)
    return FileResponse(photo.image.open("rb"), as_attachment=True, filename=photo.image.name.rsplit("/", 1)[-1])


def video_detail(request, slug):
    video = get_object_or_404(Video.objects.filter(is_published=True), slug=slug)
    count_view(request, video)
    return render(request, "gallery/video_detail.html", {
        "video": video,
        "reactions": user_reactions(request.user, video),
        "likes": reaction_count(video, "like"),
        "related": Video.objects.filter(is_published=True).exclude(pk=video.pk)[:6],
    })


def music(request):
    """Musiqa: to'liq pleyer, navbat, sevimlilar va pleylistlar."""
    cat, playlist = request.GET.get("category", ""), request.GET.get("playlist", "")
    tracks = Track.objects.filter(is_published=True).select_related("category")
    active_playlist = None
    if playlist:
        active_playlist = Playlist.objects.filter(pk=playlist, is_published=True).first()
        if active_playlist:
            tracks = active_playlist.tracks.filter(is_published=True)
    if cat == "favorites":
        tracks = tracks.filter(is_favorite=True)
    elif cat:
        tracks = tracks.filter(category__slug=cat)
    tracks = list(tracks)
    return render(request, "gallery/music.html", {
        "hero": get_hero("media"),
        "tracks": tracks,
        "playable": [t for t in tracks if t.is_playable],
        "categories": MediaCategory.objects.filter(kind="music", tracks__is_published=True).distinct(),
        "playlists": Playlist.objects.filter(is_published=True).prefetch_related("tracks"),
        "active": cat, "active_playlist": active_playlist,
        "favorites_count": Track.objects.filter(is_published=True, is_favorite=True).count(),
    })
