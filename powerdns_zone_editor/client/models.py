from django.db import models
from django.contrib.auth.models import User

class Zone(models.Model):
    zone_name = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User)
    comment = models.CharField(max_length=255)

    def __unicode__(self):
        return "%s changed by %s on %s" % (self.zone_name, self.user.username, self.created)

class ZoneRecord(models.Model):
    rr_name = models.CharField(max_length=255)
    rr_type = models.CharField(max_length=50)
    rr_ttl = models.IntegerField()
    rr_content = models.CharField(max_length=255)
    zone = models.ForeignKey(Zone, related_name='records')

    def __unicode__(self):
        return "%s %s %s %s" % (self.rr_name, self.rr_type, self.rr_ttl, self.rr_content)
