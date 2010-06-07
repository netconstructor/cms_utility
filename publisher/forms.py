from django import forms
from models import Settings

class SettingsForm(forms.ModelForm):
    class Meta:
        model = Settings
        
class SingleUploadForm(forms.Form):
    post_file = forms.FileField()
    category = forms.CharField()
    status = forms.CharField()
    date = forms.DateTimeField()
    tags = forms.CharField()
    
class ZipUploadForm(forms.Form):
    post_file = forms.FileField()
    category = forms.CharField()
    status = forms.CharField()
    date = forms.DateTimeField()
    tags = forms.CharField()
    