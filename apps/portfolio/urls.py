from django.urls import path

from . import views

app_name = "portfolio"

urlpatterns = [
    path("about/", views.about, name="about"),
    path("skills/", views.skills, name="skills"),
    path("projects/", views.project_list, name="project_list"),
    path("projects/<slug:slug>/", views.project_detail, name="project_detail"),
    path("experience/", views.experience_list, name="experience_list"),
    path("experience/<slug:slug>/", views.experience_detail, name="experience_detail"),
]
