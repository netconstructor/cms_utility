from django.db import models

LAYOUTS = (
    ('1', """Line 1: Headline
Line 2: Author
Line 3: Pub Date
Line 4: Source
Line 5: Begin Story"""),
    ('2', """Line 1: Headline
Line 2: Author
Line 3: Source
Line 4: Begin Story"""),
    ('3', """File Name: Headline
Line 1: Author
Line 2: Pub Date
Line 3: Source
Line 4: Begin Story"""),
    ('4', """File Name: Headline
Line 1: Byline
Line 2: Source
Line 3: Begin Story""")
)

DIR_STRUCTURES = (
   # ('default', 'Single Folder'),
    ('1', 'TOP DIRECTORY -> MAIN CATEGORY')
)

# Create your models here.
class Settings(models.Model):
    CMS_CHOICES = (('WP', 'Wordpress'),)
    email = models.EmailField()
    cms_type = models.CharField(max_length=2, choices=CMS_CHOICES)
    cms_url = models.URLField()
    cms_user = models.CharField(max_length=75)
    cms_pass = models.CharField(max_length=75)
    
class DocumentsProcessed(models.Model):
    total = models.IntegerField()
