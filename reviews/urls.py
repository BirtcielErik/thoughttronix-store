from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path("reviews/add/<int:pk>/", views.CreateReviewView.as_view(), name="create"),
    path("reviews/<int:pk>/edit/", views.EditReviewView.as_view(), name="edit"),
    path(
        "reviews/<int:pk>/cancel/", views.CancelEditReviewView.as_view(), name="cancel"
    ),
    path("reviews/<int:pk>/delete/", views.DeleteReviewView.as_view(), name="delete"),
    # Back office — staff-only.
    path(
        "backoffice/reviews/",
        views.ManageReviewListView.as_view(),
        name="manage_reviews",
    ),
]
