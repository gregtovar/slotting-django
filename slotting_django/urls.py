from django.urls import include, path

urlpatterns = [
    path("", include("slotting.urls")),
]
