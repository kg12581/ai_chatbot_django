from django.urls import path

from common.analytics_views import analytics_dashboard, track_event

urlpatterns = [
    path("api/track/", track_event, name="track_event"),
    path("analytics/", analytics_dashboard, name="analytics_dashboard"),
]
