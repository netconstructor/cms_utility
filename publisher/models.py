from django.db import models

# Create your models here.
class Settings(models.Model):
    CMS_CHOICES = (('WP', 'Wordpress'),)
    email = models.EmailField()
    cms_type = models.CharField(max_length=2, choices=CMS_CHOICES)
    cms_url = models.URLField()
    cms_user = models.CharField(max_length=75)
    cms_pass = models.CharField(max_length=75)