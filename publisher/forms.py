from django import forms
from models import Settings

class SettingsForm(forms.ModelForm):
    cms_pass = forms.CharField(widget=forms.PasswordInput())
    class Meta:
        model = Settings
        
class FileUploadForm(forms.Form):
    post_file = forms.FileField()
    image_file = forms.FileField(required=False)
    category = forms.CharField()
    status = forms.CharField()
    date = forms.DateTimeField()
    tags = forms.CharField(required=False)
    layout = forms.CharField()
    dir_structure = forms.CharField()
    
