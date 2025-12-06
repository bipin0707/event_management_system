from django.contrib import admin
from .models import Admin as AdminModel


@admin.register(AdminModel)
class AdminTableAdmin(admin.ModelAdmin):
    list_display = ("admin_id", "username", "email", "role")
    list_filter = ("role",)
    search_fields = ("username", "email")
