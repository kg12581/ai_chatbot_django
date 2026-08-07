from django.urls import path

from common.scanner_views import scanner_home, scanner_run, scanner_status, scanner_update_status

urlpatterns = [
    path("", scanner_home, name="scanner_home"),
    path("run/", scanner_run, name="scanner_run"),
    path("status/<int:run_id>/", scanner_status, name="scanner_status"),
    path("findings/<int:pk>/status/", scanner_update_status, name="scanner_update_status"),
]
