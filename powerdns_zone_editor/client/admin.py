from django.contrib import admin

from client.models import Zone, ZoneRecord

class ZoneAdmin(admin.ModelAdmin):
    list_display = ('zone_name', 'created', 'user', 'comment')

class ZoneRecordAdmin(admin.ModelAdmin):
    list_display = ('rr_name', 'rr_type', 'rr_ttl', 'rr_content')

admin.site.register(Zone, ZoneAdmin)
admin.site.register(ZoneRecord, ZoneRecordAdmin)
