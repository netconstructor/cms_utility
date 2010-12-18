import pyblog
#import time
import xmlrpclib

from django.views.generic.simple import direct_to_template
from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required

from models import Settings, LAYOUTS, DIR_STRUCTURES, DocumentsProcessed
from forms import FileUploadForm, SettingsForm
from publisher import *
from publisher.poster import CMSUtility

def index(request):
    config = lookup_settings(request)
    return direct_to_template(request, 'index.html', 
        {'config': config,})

@login_required
def cms_settings(request):
    config = None
    message = get_messages(request)
    
    if request.method == 'POST':
        form = SettingsForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            delete_settings(email=email)
            
            config = form.save()
            message = "Settings saved."
            request.session['cms_email'] = config.email
            return HttpResponseRedirect(settings.ROOT_URL+'options/')
    else:
        form = SettingsForm()
    
    config = lookup_settings(request)
    
    return direct_to_template(request, 'settings.html', 
        {'config': config, 'message': message, 'form': form, })
    
def get_cms_settings(request):
    if request.method == 'POST':
        if 'cms_email' in request.POST:
            request.session['cms_email'] = request.POST['cms_email']
    return HttpResponseRedirect(settings.ROOT_URL+'options/')

def clear_cms_settings(request):
    if 'cms_email' in request.session:
        del request.session['cms_email']
    request.session['message'] = "Settings Cleared."
    return HttpResponseRedirect(settings.ROOT_URL+'options/')
        
@login_required
def single_upload(request):
    posts = categories = pub_date = image = None
    config = lookup_settings(request)
    
    if config:
        blog = CMSUtility(config)
        categories = blog.get_categories()

        if request.method == 'POST':
            form = blog.form(request.POST, request.FILES)
            file_name = None
            if form.is_valid():
                blog.parse_form(form)
                blog.post_stories()
                posts = blog.get_links()
        else:
            form = blog.form()
            posts = pub_date = None
    else:
        posts = form = categories = pub_date = None
        
    return direct_to_template(request, 'single_upload.html', 
        {'config': config, 'categories': categories,
        'form': form, 'posts': posts, 'pub_date': pub_date, 
        'layout': 'default', })
    
@login_required
def batch_upload(request):
    posts = form = categories = pub_date = rv_posts = None
    config = lookup_settings(request)

    if config:
        blog = CMSUtility(config)
        categories = blog.get_categories()
        
        if request.method == 'POST':
            form = blog.form(request.POST, request.FILES)
            file_name = None
            if form.is_valid():
                blog.parse_form(form, isZip=True)
                blog.post_stories()
                posts = blog.get_links()
        else:
            form = blog.form()
            posts = None
    else:
        posts = form = categories = pub_date = None
        
    return direct_to_template(request, 'batch_upload.html', 
        {'config': config, 'categories': categories,
        'form': form, 'posts': posts, 'pub_date': pub_date, })
        
@login_required
def single_upload_file_info(request):
    posts = form = categories = pub_date = None
    config = lookup_settings(request)

    if config: 
        blog = CMSUtility(config)
        categories = blog.get_categories()

        if request.method == 'POST':
            form = blog.form(request.POST, request.FILES)
            file_name = None
            if form.is_valid():
                blog.parse_form(form)
                blog.post_stories()
                posts = blog.get_links()
        else:
            form = blog.form()
            posts = None
    else:
        posts = form = categories = pub_date = None
        
    return direct_to_template(request, 'single_upload_file_info.html', 
        {'config': config, 'categories': categories,
        'form': form, 'posts': posts, 'pub_date': pub_date, 
        'layouts': LAYOUTS})
        
@login_required
def batch_upload_hierarchy(request):
    posts = form = categories = pub_date = rv_posts = None
    config = lookup_settings(request)

    if config:
        blog = CMSUtility(config)
        categories = blog.get_categories()

        if request.method == 'POST':
            form = blog.form(request.POST, request.FILES)
            file_name = None
            if form.is_valid():
                blog.parse_form(form, isZip=True, isHierarchy=True)
                blog.post_stories()
                posts = blog.get_links()

        else:
            form = blog.form()
            posts = None
    else:
        posts = form = categories = pub_date = None
        
    return direct_to_template(request, 'batch_upload_hierarchy.html', 
        {'config': config, 'categories': categories,
        'form': form, 'posts': posts, 'pub_date': pub_date, 
        'layouts': LAYOUTS, 'dir_structures': DIR_STRUCTURES, })

def server_error(request, template_name='500.html'):
    return render_to_response(template_name,
           context_instance = RequestContext(request))
           
def page_not_found(request, template_name='404.html'):
    return render_to_response(template_name,
           context_instance = RequestContext(request))
    