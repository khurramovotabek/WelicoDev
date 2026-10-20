from django.urls import path

from . import views
from .feeds import LatestArticlesFeed

app_name = "blog"

urlpatterns = [
    path("", views.article_list, name="article_list"),
    path("subscribe/", views.subscribe, name="subscribe"),
    path("feed/", LatestArticlesFeed(), name="feed"),
    path("<slug:slug>/", views.article_detail, name="article_detail"),
]
