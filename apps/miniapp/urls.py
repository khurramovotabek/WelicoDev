from django.urls import path

from . import views

app_name = "miniapp"

urlpatterns = [
    path("", views.shell, name="shell"),
    path("me/", views.me, name="me"),
    path("home/", views.home, name="home"),
    path("courses/", views.courses, name="courses"),
    path("courses/<slug:slug>/", views.course, name="course"),
    path("courses/<slug:slug>/enroll/", views.enroll, name="enroll"),
    path("courses/<slug:slug>/buy/", views.buy, name="buy"),
    path("courses/<slug:course_slug>/<slug:lesson_slug>/", views.lesson, name="lesson"),
    path("courses/<slug:course_slug>/<slug:lesson_slug>/heartbeat/", views.heartbeat, name="heartbeat"),
    path("courses/<slug:course_slug>/<slug:lesson_slug>/watched/", views.watched, name="watched"),
    path("courses/<slug:course_slug>/<slug:lesson_slug>/homework/", views.homework, name="homework"),
    path("blog/", views.journal, name="journal"),
    path("blog/<slug:slug>/", views.article, name="article"),
    path("projects/", views.projects, name="projects"),
    path("projects/<slug:slug>/", views.project, name="project"),
    path("profile/", views.profile, name="profile"),
    path("language/", views.set_language, name="language"),
]
