from django.urls import path
from . import views

urlpatterns = [
    # Public event pages
    path("", views.event_list, name="event_list"),
    path("<int:event_id>/", views.event_detail, name="event_detail"),

    # Organizer dashboard
    path("manage/", views.manage_events, name="manage_events"),
    path("manage/events/new/", views.event_create, name="event_create"),
    path("manage/events/<int:event_id>/edit/", views.event_edit, name="event_edit"),
    path("manage/venues/new/", views.venue_create, name="venue_create"),

    # Organizer analytics
    path("manage/analytics/", views.organizer_analytics, name="organizer_analytics"),
    
    path("analytics/", views.organizer_analytics, name="analytics_dashboard"),

]
