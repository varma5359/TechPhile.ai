from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Contact

@admin.register(Contact)
class ContactAdmin(ModelAdmin):
    list_display = ('name', 'email', 'get_subject_display', 'submitted_at')
    list_filter = ('subject', 'submitted_at')
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('submitted_at', 'ip_address')
    date_hierarchy = 'submitted_at'
