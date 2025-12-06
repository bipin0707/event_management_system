from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    # your existing login/register urls here...

    path("become-organizer/", views.become_organizer, name="become_organizer"),
    path("profile/", views.profile, name="profile"),

]
