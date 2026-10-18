from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path(
        "products/<slug:slug>/review/",
        views.ReviewWriteView.as_view(),
        name="write",
    ),
]
