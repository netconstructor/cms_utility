from django.conf import settings 
from publisher.models import Settings, DocumentsProcessed


def add_settings(request):
    
    number_of_users = Settings.objects.count()
    doc_count = DocumentsProcessed.objects.get(id=1)
    return {'settings': settings, 'num_users': number_of_users, 
        'doc_count': doc_count.total }