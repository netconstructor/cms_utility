from django.conf import settings
import models
import zipfile
import tempfile
import os

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
        description = "".join(data[4:])
        description += 'Author: ' + data[1]
        description += 'Pub Date: ' + data[2]
        description += 'Source: ' + data[3]
    elif layout == '2':
        title = data[0]
        description = "".join(data[3:])
        description += 'Author: ' + data[1]
        description += 'Source: ' + data[2]
    elif layout == '3':
        title = os.path.basename(file_name)
        for ext in ['.txt', '.doc', '.rtf']:
            title = title.rstrip(ext)
        description = "".join(data[3:])
        description += 'Author: ' + data[0]
        description += 'Pub Date: ' + data[1]
        description += 'Source: ' + data[2]
    elif layout == '4':
        title = os.path.basename(file_name)
        for ext in ['.txt', '.doc', '.rtf']:
            title = title.rstrip(ext)
        description = "".join(data[2:])
        description += 'Byline: ' + data[0]
        description += 'Source: ' + data[1]
    else: # default 
        title = data[0]
        description = "".join(data[1:])
    
    return (title, description)

def text_file(post_file, file_name, is_zipfile=False):
    if is_zipfile:
        post_file = open(file_name, 'r')
        lines = post_file.readlines()
        post_file.close()
    else:
        lines = post_file.readlines()

    if is_zipfile:
        os.unlink(file_name)
        
    return lines

def word_file(post_file, file_name, is_zipfile=False):
    if is_zipfile:
        tmp_file_name = file_name
    else:
        tmp_file_name = settings.TEMP_FILES + '/' + file_name
        tmp_file = open(tmp_file_name, 'w')
        for chunk in post_file.chunks():
            tmp_file.write(chunk)
        tmp_file.close()
        
    command = settings.ANTIWORD + " \"" + tmp_file_name + "\""
    lines = os.popen(command).read().split('\n\n')
    
    tmp_list = []
    for line in lines[0].lstrip('\n').split('\n'):
        tmp_list.append(line + '\n')

    os.unlink(tmp_file_name)    

    return tmp_list

def rtf_file(post_file, file_name, is_zipfile=False):
    if is_zipfile:
        tmp_file_name = file_name
    else:
        tmp_file_name = settings.TEMP_FILES + '/' + file_name
        tmp_file = open(tmp_file_name, 'w')
        for chunk in post_file.chunks():
            tmp_file.write(chunk)
        tmp_file.close()

    command = settings.UNRTF + " -t text \"" + tmp_file_name + "\" 2> /dev/null"
    data = os.popen(command).read()
    lines = data.split('-----------------')[1].split('\n')[1:]
    
    tmp_list = []
    for line in lines:
        tmp_list.append(line + '\n')
        
    os.unlink(tmp_file_name)    

    return tmp_list
    
def process_zip_file(post_file):
    file_name = post_file.name
    directory = tempfile.mkdtemp(dir=settings.TEMP_FILES)
    
    tmp_file_name = directory + '/' + file_name
    tmp_file = open(tmp_file_name, 'w')
    for chunk in post_file.chunks():
        tmp_file.write(chunk)
    tmp_file.close()
    
    posts = []
    zip_file = open(tmp_file_name, 'r')
    cms_zipfile = zipfile.ZipFile(zip_file)
    for info in cms_zipfile.infolist():
        extracted_name = directory + '/' + info.filename
        data = cms_zipfile.read(info.filename)
        outfile = open(extracted_name, 'w')
        outfile.write(data)
        outfile.flush()
        outfile.close()
            
        (title, description) = process_file(extracted_name, is_zipfile=True)
        posts.append({'title': title, 'description': description})
        
    os.unlink(tmp_file_name)
    os.rmdir(directory)
    
    return posts