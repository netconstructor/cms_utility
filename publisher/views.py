import pyblog
import time
import xmlrpclib

from django.views.generic.simple import direct_to_template
from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from models import Settings, LAYOUTS, DIR_STRUCTURES, DocumentsProcessed
from forms import FileUploadForm, SettingsForm
from publisher import *

def index(request):
    config = lookup_settings(request)
    return direct_to_template(request, 'index.html', 
        {'config': config,})
    
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
        
def single_upload(request):
    post = form = categories = pub_date = image = None
    config = lookup_settings(request)
    
    if config: 
        blog = pyblog.WordPress(config.cms_url, config.cms_user, 
                config.cms_pass)
        categories = blog.get_categories()
        if request.method == 'POST':
            form = FileUploadForm(request.POST, request.FILES)
            file_name = None
            if form.is_valid():
                post_file = form.cleaned_data['post_file']
                post = process_file(post_file)

                if 'image_file' in form.cleaned_data:
                    if form.cleaned_data['image_file']:
                        image_file = form.cleaned_data['image_file']
                        img = upload_image(blog, image_file)
                        post['description'] += '<br/><img src="' + img['url'] + '"/>'
                    
                pub_date = form.cleaned_data['date']
                post['dateCreated'] = xmlrpclib.DateTime(
                    time.mktime(pub_date.timetuple()))
                    
                post['mt_keywords'] = form.cleaned_data['tags']
                post['categories'] = [form.cleaned_data['category']]            
            
                rv = new_post(blog, post)
                post = blog.get_post(rv)
        else:
            form = FileUploadForm()
            post = None
    else:
        post = form = categories = pub_date = None
        
    return direct_to_template(request, 'single_upload.html', 
        {'config': config, 'categories': categories,
        'form': form, 'post': post, 'pub_date': pub_date, 
        'layout': 'default', })
    
def batch_upload(request):
    post = form = categories = pub_date = rv_posts = None
    config = lookup_settings(request)
    
    if config:
        blog = pyblog.WordPress(config.cms_url, config.cms_user, 
                config.cms_pass)
        categories = blog.get_categories()
        
        if request.method == 'POST':
            form = FileUploadForm(request.POST, request.FILES)
            file_name = None
            if form.is_valid():
                post_file = form.cleaned_data['post_file']
                posts = process_zip_file(post_file)
                
                pub_date = form.cleaned_data['date']
                dateCreated = xmlrpclib.DateTime(
                    time.mktime(pub_date.timetuple()))
                mt_keywords = form.cleaned_data['tags']
                categories = [form.cleaned_data['category']]
                
                rv_posts = []
                for cms_post in posts:
                    cms_post['dateCreated'] = dateCreated
                    cms_post['mt_keywords'] = mt_keywords
                    cms_post['categories'] = categories
                    rv = new_post(blog, cms_post)
                    post = blog.get_post(rv)
                    rv_posts.append(post)
        else:
            form = FileUploadForm()
            posts = None
    else:
        post = form = categories = pub_date = None
        
    return direct_to_template(request, 'batch_upload.html', 
        {'config': config, 'categories': categories,
        'form': form, 'posts': rv_posts, 'pub_date': pub_date, })
        
def single_upload_file_info(request):
    post = form = categories = pub_date = None
    config = lookup_settings(request)
    
    if config: 
        blog = pyblog.WordPress(config.cms_url, config.cms_user, 
                config.cms_pass)
        categories = blog.get_categories()
        if request.method == 'POST':
            form = FileUploadForm(request.POST, request.FILES)
            file_name = None
            if form.is_valid():
                post_file = form.cleaned_data['post_file']
                layout = form.cleaned_data['layout']
                post = process_file(post_file, layout=layout)
                
                if 'image_file' in form.cleaned_data:
                    if form.cleaned_data['image_file']:
                        image_file = form.cleaned_data['image_file']
                        img = upload_image(blog, image_file)
                        post['description'] += '<br/><img src="' + img['url'] + '"/>'                
                
                pub_date = form.cleaned_data['date']
                post['dateCreated'] = xmlrpclib.DateTime(
                    time.mktime(pub_date.timetuple()))
                post['mt_keywords'] = form.cleaned_data['tags']
                post['categories'] = [form.cleaned_data['category']]
                
                rv = new_post(blog, post)
                post = blog.get_post(rv)
        else:
            form = FileUploadForm()
            post = None
    else:
        post = form = categories = pub_date = None
        
    return direct_to_template(request, 'single_upload_file_info.html', 
        {'config': config, 'categories': categories,
        'form': form, 'post': post, 'pub_date': pub_date, 
        'layouts': LAYOUTS})
        
def batch_upload_hierarchy(request):
    post = form = categories = pub_date = rv_posts = None
    config = lookup_settings(request)

    if config:
        blog = pyblog.WordPress(config.cms_url, config.cms_user, 
                config.cms_pass)
        categories = blog.get_categories()

        if request.method == 'POST':
            form = FileUploadForm(request.POST, request.FILES)
            file_name = None
            if form.is_valid():
                post_file = form.cleaned_data['post_file']
                layout = form.cleaned_data['layout']
                dir_structure = form.cleaned_data['dir_structure']
                posts = process_zip_file(post_file, layout=layout, 
                    dir_structure=dir_structure)
                    
                pub_date = form.cleaned_data['date']
                dateCreated = xmlrpclib.DateTime(
                    time.mktime(pub_date.timetuple()))
                mt_keywords = form.cleaned_data['tags']
                category = form.cleaned_data['category']


                rv_posts = []
                for cms_post in posts:
                    if 'category' in cms_post:
                        post_category = [cms_post['category']]
                        cat_id = 0
                        for cat in categories:
                            if cat['categoryName'] == cms_post['category']:
                                cat_id = int(cat['categoryId'])
                        if not cat_id:
                            cat_id = blog.new_category(
                                {'name': cms_post['category'],
                                'slug': cms_post['category'].replace(' ', '-'),
                                'parent_id': 0, 
                                'description': cms_post['category']})
                        cms_post['category'] = [cms_post['category']]
                    else: 
                        cms_post['category'] = [category]
                        
                    cms_post['mt_keywords'] = mt_keywords
                    cms_post['dateCreated'] = dateCreated
                    
                    rv = new_post(blog, cms_post)
                    if rv:
                        post = blog.get_post(rv)            
                        rv_posts.append(post)
        else:
            form = FileUploadForm()
            posts = None
    else:
        post = form = categories = pub_date = None
        
    return direct_to_template(request, 'batch_upload_hierarchy.html', 
        {'config': config, 'categories': categories,
        'form': form, 'posts': rv_posts, 'pub_date': pub_date, 
        'layouts': LAYOUTS, 'dir_structures': DIR_STRUCTURES, })

def server_error(request, template_name='500.html'):
    return render_to_response(template_name,
           context_instance = RequestContext(request))
           
def page_not_found(request, template_name='404.html'):
    return render_to_response(template_name,
           context_instance = RequestContext(request))
    