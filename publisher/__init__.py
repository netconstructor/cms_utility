from django.conf import settings
from django.utils.encoding import smart_unicode

import models
import zipfile
import tempfile
import os
import unicodedata
import codecs
import shutil
import re

def get_messages(request):
    message = None
    if 'message' in request.session:
        message = request.session['message']
        del request.session['message']
    return message

def lookup_settings(request):
    config = None
    if 'cms_email' in request.session:
        try:
            config = models.Settings.objects.get(email=request.session['cms_email'])
        except models.Settings.DoesNotExist:
            config = None
            del request.session['cms_email']

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
    
    (title, description) = parse_file(data, file_name, layout)
    return (title, description)
    
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

    return (title, description)

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
            
            post = {}
            (title, description) = process_file(extracted_name, 
                layout, is_zipfile=True)
            post['title'] = title
            post['description'] = description

            if dir_structure == '1':
                try:
                    post['category'] = info.filename.split(os.path.sep)[-2]
                except IndexError:
                    pass
            if title and description:
                posts.append(post)
             
    os.unlink(tmp_file_name)
    shutil.rmtree(directory)
    
    return posts