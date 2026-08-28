from django.contrib import admin

from apps.ranking.models import Season, SeasonConfig


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("year", "name", "stage", "start_at", "end_at", "settle_at")
    list_filter = ("stage",)
    search_fields = ("name",)


@admin.register(SeasonConfig)
class SeasonConfigAdmin(admin.ModelAdmin):
    list_display = ("current_season", "auto_reset", "updated_at")
