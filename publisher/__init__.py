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
        
def process_file(post_file, local=0):
    if local:
        file_name = post_file
        post_file = None
    else:
        file_name = post_file.name
    
    if (file_name.endswith('.txt')):
        (title, description) = text_file(post_file, file_name, local)
    elif (file_name.endswith('.doc')):
        (title, description) = word_file(post_file, file_name, local)
    elif (file_name.endswith('.rtf')):
        (title, description) = rtf_file(post_file, file_name, local)
    else: 
        title = descripiton = None
    return (title, description)

def text_file(post_file, file_name, local=0):
    if local:
        post_file = open(file_name, 'r')
        title = post_file.readline()
        description = ''
        for chunk in post_file.readlines():
            description += chunk
    else:
        title = post_file.readlines()[0]
        description = ''
        for chunk in post_file.readlines()[1:]:
            description += chunk
    description += '\n\nSource: %s' % os.path.basename(file_name)

    if local:
        os.unlink(file_name)
        
    return (title, description)

def word_file(post_file, file_name, local=0):
    if local:
        tmp_file_name = file_name
    else:
        tmp_file_name = settings.TEMP_FILES + '/' + file_name
        tmp_file = open(tmp_file_name, 'w')
        for chunk in post_file.chunks():
            tmp_file.write(chunk)
        tmp_file.close()
        
    command = settings.ANTIWORD + " \"" + tmp_file_name + "\""
    lines = os.popen(command).read().split('\n\n')

    title = lines[0].strip('\n')
    description = ''
    for chunk in lines[1:]:
        description += chunk
    description += '\n\nSource: %s' % os.path.basename(file_name)

    os.unlink(tmp_file_name)    

    return (title, description)

def rtf_file(post_file, file_name, local=0):
    if local:
        tmp_file_name = file_name
    else:
        tmp_file_name = settings.TEMP_FILES + '/' + file_name
        tmp_file = open(tmp_file_name, 'w')
        for chunk in post_file.chunks():
            tmp_file.write(chunk)
        tmp_file.close()

    command = settings.UNRTF + " -t text \"" + tmp_file_name + "\""
    data = os.popen(command).read()
    lines = data.split('-----------------')[1].split('\n')[1:]

    title = lines[0]
    description = ''
    for chunk in lines[1:]:
        if chunk == '': 
            chunk = '\n'
        description += chunk
    description += '\n\nSource: %s' % os.path.basename(file_name)

    os.unlink(tmp_file_name)    

    return (title, description)
    
def process_zip_file(post_file):
    file_name = post_file.name
    directory = tempfile.mkdtemp(dir=settings.TEMP_FILES)
    
    tmp_file_name = directory + '/' + file_name
    tmp_file = open(tmp_file_name, 'w')
    for chunk in post_file.chunks():
        tmp_file.write(chunk)
    tmp_file.close()
    
    zip_file = open(tmp_file_name, 'r')
    cms_zipfile = zipfile.ZipFile(zip_file)
    cms_zipfile.extractall(path=directory)
    
    posts = []
    for zfile in cms_zipfile.filelist:
        filename = directory + '/' + zfile.filename
        (title, description) = process_file(filename, local=1)
        posts.append({'title': title, 'description': description})
    
    os.unlink(tmp_file_name)
    os.rmdir(directory)
    
    return posts