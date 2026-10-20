from django.urls import path

from . import views

app_name = "gallery"

urlpatterns = [
    path("", views.index, name="index"),
    path("photos/", views.photo_list, name="photo_list"),
    path("photos/<slug:slug>/", views.photo_detail, name="photo_detail"),
    path("photos/<slug:slug>/download/", views.photo_download, name="photo_download"),
    path("music/", views.music, name="music"),
    path("videos/", views.video_list, name="video_list"),
    path("videos/<slug:slug>/", views.video_detail, name="video_detail"),
]
