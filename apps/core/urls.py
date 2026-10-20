from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("contact/", views.contact, name="contact"),
    path("search/", views.search, name="search"),
    path("share/<str:kind>/<slug:slug>/", views.share, name="share"),
]
