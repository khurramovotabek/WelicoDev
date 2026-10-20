from django.urls import path

from . import views

app_name = "education"

urlpatterns = [
    path("", views.course_list, name="course_list"),
    path("my/", views.my_courses, name="my_courses"),
    path("certificate/<str:code>/", views.certificate, name="certificate"),
    path("resource/<int:pk>/", views.resource_download, name="resource_download"),
    path("<slug:slug>/", views.course_detail, name="course_detail"),
    path("<slug:slug>/enroll/", views.enroll, name="enroll"),
    path("<slug:slug>/buy/", views.buy, name="buy"),
    path("<slug:course_slug>/<slug:lesson_slug>/", views.lesson_detail, name="lesson_detail"),
    path("<slug:course_slug>/<slug:lesson_slug>/video/", views.lesson_video, name="lesson_video"),
    path("<slug:course_slug>/<slug:lesson_slug>/heartbeat/", views.lesson_heartbeat, name="lesson_heartbeat"),
    path("<slug:course_slug>/<slug:lesson_slug>/watched/", views.lesson_mark_watched, name="lesson_mark_watched"),
    path("<slug:course_slug>/<slug:lesson_slug>/homework/", views.homework_submit, name="homework_submit"),
]
