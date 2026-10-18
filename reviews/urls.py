from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path(
        "products/<slug:slug>/review/",
        views.ReviewWriteView.as_view(),
        name="write",
    ),
    path(
        "reviews/<int:pk>/delete/",
        views.ReviewDeleteView.as_view(),
        name="delete",
    ),
    path(
        "backoffice/reviews/",
        views.ManageReviewListView.as_view(),
        name="manage_reviews",
    ),
    path(
        "backoffice/reviews/<int:pk>/toggle-hidden/",
        views.ToggleReviewHiddenView.as_view(),
        name="toggle_hidden",
    ),
]
