from django.urls import path

from . import views

app_name = "interactions"

urlpatterns = [
    path("comments/<str:kind>/<int:pk>/", views.comment_list, name="comments"),
    path("comments/<str:kind>/<int:pk>/add/", views.comment_create, name="comment_create"),
    path("comment/<int:pk>/like/", views.comment_like, name="comment_like"),
    path("comment/<int:pk>/delete/", views.comment_delete, name="comment_delete"),
    path("reviews/<str:kind>/<int:pk>/", views.review_list, name="reviews"),
    path("reviews/<str:kind>/<int:pk>/add/", views.review_create, name="review_create"),
    path("react/<str:kind>/<int:pk>/<str:reaction>/", views.react, name="react"),
    path("share/<str:kind>/<int:pk>/", views.track_share, name="track_share"),
]
