from django.conf import settings
from django.utils.encoding import smart_unicode

from models import DocumentsProcessed
from poster import prepare_story

import pyblog
import time
import models
import zipfile
import tempfile
import os
import unicodedata
import codecs
import shutil
import re
import urllib
import xmlrpclib

from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
from ebdata.nlp import addresses

def get_messages(request):
    message = None
    if 'message' in request.session:
        message = request.session['message']
        del request.session['message']
    return message

def lookup_settings(request):
    config = None
    if request.user:
        try:
            config = models.Settings.objects.get(email=request.user.email)
        except models.Settings.DoesNotExist:
            config = None
        except AttributeError:
            config = None
    return config

def delete_settings(email):
    try:
        config = models.Settings.objects.get(email=email)
        config.delete()
    except models.Settings.DoesNotExist:
        pass    
        
def process_file(post_file, layout='default', is_zipfile=False):
    if is_zipfile:
        file_name = post_file
        post_file = None
    else:
        file_name = post_file.name
    
    if (file_name.endswith('.txt')):
        data = text_file(post_file, file_name, is_zipfile)
    elif (file_name.endswith('.doc')):
        data = word_file(post_file, file_name, is_zipfile)
    elif (file_name.endswith('.rtf')):
        data = rtf_file(post_file, file_name, is_zipfile)
    else: 
        data = None
    
    return parse_file(data, file_name, layout)
    
def parse_file(data, file_name, layout):
    if not data:
        title = description = None
    elif layout == '1':
        title = data[0]
        description = "<br/><br/>".join(data[4:])
        description += '<br/><br/>Author: ' + data[1]
        description += '<br/>Pub Date: ' + data[2]
        description += '<br/>Source: ' + data[3]
    elif layout == '2':
        title = data[0]
        description = "<br/><br/>".join(data[3:])
        description += '<br/><br/>Author: ' + data[1]
        description += '<br/>Source: ' + data[2]
    elif layout == '3':
        title = os.path.basename(file_name)
        for ext in ['.txt', '.doc', '.rtf']:
            title = title.rstrip(ext)
        description = "<br/><br/>".join(data[3:])
        description += '<br/><br/>Author: ' + data[0]
        description += '<br/>Pub Date: ' + data[1]
        description += '<br/>Source: ' + data[2]
    elif layout == '4':
        title = os.path.basename(file_name)
        for ext in ['.txt', '.doc', '.rtf']:
            title = title.rstrip(ext)
        description = "<br/><br/>".join(data[2:])
        description += '<br/><br/>Byline: ' + data[0]
        description += '<br/>Source: ' + data[1]
    else: # default 
        title = data[0]
        description = "<br/><br/>".join(data[1:])
    
    if title:
        title = title.replace('\n', '')

    post = {'title': title, 'description': description, 'address': None,
        'latitude': None, 'longitude': None}
        
    if data and settings.PARSE_ADDRESSES:
        address = get_address(" ".join(data))
        if address['address']:
            description += '<br/><br/><font size="-2">Location: ' + address['address'] + ' '
            description += settings.CITY + ', ' + settings.STATE
            description += '<br/>Coords: ' + str(address['latitude'])
            description += ', ' + str(address['longitude']) + "</font>"
            
            post['description'] = description
            post['address'] = address['address']
            post['latitude'] = address['latitude']
            post['longitude'] = address['longitude']
            
            
    return post

def text_file(post_file, file_name, is_zipfile=False):
    if is_zipfile:
        post_file = codecs.open(file_name, encoding='mac_roman')
        lines = post_file.read()
        post_file.close()
    else:
        lines = smart_unicode(post_file.read(), encoding='mac_roman', errors='replace')
    if is_zipfile:
        os.unlink(file_name)
    
    lines = lines.replace('\n\n', '\n')
    lines = lines.replace('\r\n', '\n')
    lines = lines.replace('\r', '\n')
    lines = unicodedata.normalize('NFKD', lines).encode('ascii', 'ignore')
    
    return lines.splitlines()

def word_file(post_file, file_name, is_zipfile=False):
    if is_zipfile:
        tmp_file_name = file_name
    else:
        tmp_file_name = settings.TEMP_FILES + '/' + file_name
        tmp_file = open(tmp_file_name, 'w')
        for chunk in post_file.chunks():
            tmp_file.write(chunk)
        tmp_file.close()
        
    command = settings.WVTEXT + " \"" + tmp_file_name + "\" /dev/stdout"
    lines = os.popen(command).read()
    lines = lines.strip()
    lines = lines.split('\n\n')

    tmp_list = []
    for line in lines:
        tmp_list.append(line.replace('\n', ''))

    os.unlink(tmp_file_name)    

    return tmp_list

def rtf_file(post_file, file_name, is_zipfile=False):
    regex = re.compile(r'<.*?>')
    if is_zipfile:
        tmp_file_name = file_name
    else:
        tmp_file_name = settings.TEMP_FILES + '/' + file_name
        tmp_file = open(tmp_file_name, 'w')
        for chunk in post_file.chunks():
            tmp_file.write(chunk)
        tmp_file.close()

    command = settings.UNRTF + " -t html \"" + tmp_file_name + "\" 2> /dev/null"
    data = os.popen(command).read()
    data = regex.sub('', data)
    data = data.strip()
    data = data.replace('\n\n', '\n')

    os.unlink(tmp_file_name)    

    return data.splitlines()
    
def process_zip_file(post_file, layout="default", dir_structure='default'):
    file_name = post_file.name
    directory = tempfile.mkdtemp(dir=settings.TEMP_FILES)
    
    tmp_file_name = directory + '/' + file_name
    tmp_file = open(tmp_file_name, 'w')
    for chunk in post_file.chunks():
        tmp_file.write(chunk)
    tmp_file.close()
    
    posts = []
    dirs = []
    zip_file = open(tmp_file_name, 'r')
    cms_zipfile = zipfile.ZipFile(zip_file)
    for info in cms_zipfile.infolist():
        if info.filename.startswith('.'):
            pass
        elif info.filename.startswith('_'):
            pass
        elif info.filename.find('/.') > 0:
            pass
        elif info.filename.endswith('/'):
            os.mkdir(directory + '/' + info.filename)
            dirs.append(directory + '/' + info.filename)
        else:
            extracted_name = directory + '/' + info.filename
            outfile = open(extracted_name, 'w')
            outfile.write(cms_zipfile.read(info.filename))
            outfile.flush()
            outfile.close()
            
            post = process_file(extracted_name, 
                layout, is_zipfile=True)

            if dir_structure == '1':
                try:
                    post['category'] = info.filename.split(os.path.sep)[-2]
                except IndexError:
                    pass
                    
            if post['title'] and post['description']:
                posts.append(post)
             
    os.unlink(tmp_file_name)
    shutil.rmtree(directory)
    
    return posts
    
def get_address(text=""):
    _addresses = addresses.parse_addresses(text)
    a_dict = {'address': None, 'latitude': None, 'longitude': None}
    for address in _addresses:
        if a_dict['address']: # only use the first match for now
            continue
        a_dict = geocode(address[0], city=settings.CITY, state=settings.STATE)
    
    return a_dict

def geocode(address="", city="", state="CA"):
    address = urllib.quote(address.encode('utf-8'))
    g_url = 'http://local.yahooapis.com/MapsService/V1/geocode?appid='
    g_url += '0MoPk9DV34FH0rumXB_xENjSlf.jdG4woRO9nFqyUcM86nLsFSynUvAwZZo6g--'
    g_url += '&street=%s&city=%s&state=%s' % (address, city, state)

    url = urllib.urlopen(g_url)
    dom = BeautifulStoneSoup(url)
    url.close()

    coords = { 'address': None, 'latitude': None, 'longitude': None, }

    result_attr = dom.find('result')

    if result_attr and result_attr['precision'] == 'address':

        dom_fields = ['address', 'latitude', 'longitude']
        for field in dom_fields:
            i = dom.find(field)
            if i:
                if field == 'address': 
                    coords[field] = i.string
                else:
                    try:
                        coords[field] = float(i.string)
                    except:
                        pass

    return coords
    
def new_wp_post(config, post):
    if not post['title'] and not post['description']:
        return False

    blog = pyblog.WordPress(config.cms_url, config.cms_user, 
        config.cms_pass)
    

    
    address = post.pop('address', None)
    latitude = post.pop('latitude', None)
    longitude = post.pop('longitude', None)
    rv = blog.new_post(post)
    post = blog.get_post(rv)
    dp = DocumentsProcessed.objects.get(id=1)
    dp.total += 1
    dp.save()
    
    if latitude and longitude:
        add_coords(blog, rv, latitude, longitude)
    print post
    return post
    
def add_coords(blog, post_id, latitude, longitude):
        try:
            idx = blog.methods.index('wpgeo.setCoords')
            coords = blog.server.wpgeo.setCoords(post_id, blog.username,
                blog.password, {'_wp_geo_latitude': latitude, 
                '_wp_geo_longitude': longitude})
        except ValueError:
            pass
            
def upload_image(blog, image_file):
    tmp_file_name = settings.TEMP_FILES + '/' + image_file.name
    tmp_file = open(tmp_file_name, 'w')

    for chunk in image_file.chunks():
        tmp_file.write(chunk)
    tmp_file.close()
    
    tmp_file = open(tmp_file_name)
    data = xmlrpclib.Binary(tmp_file.read())
    tmp_file.close()
    
    img = blog.upload_file({'name': image_file.name, 
        'type': image_file.content_type, 'bits': data, 'overwrite': 'true'})
    
    os.unlink(tmp_file_name)
    return img
    
def create_post(config, post):
    story = prepare_story(config, post)
    if config.cms_type == 'WP': 
        return new_wp_post(config, story)
