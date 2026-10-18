from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path("reviews/add/<int:pk>/", views.CreateReviewView.as_view(), name="create"),
]
