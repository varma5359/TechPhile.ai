from django.contrib import admin
from django.contrib.admin.apps import AdminConfig
from django.contrib.admin import sites


class TechPhileAdminConfig(AdminConfig):
    """Install the custom Unfold site before Django autodiscovers admin modules."""

    def ready(self):
        from techphile_exams.admin_site import TechPhileAdminSite

        site = TechPhileAdminSite()
        admin.site = site
        sites.site = site
        super().ready()
