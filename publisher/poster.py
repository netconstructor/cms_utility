import pyblog, os, xmlrpclib, unicodedata, urllib, time, re, tempfile, zipfile
import codecs, shutil

from django.conf import settings
from django.utils.encoding import smart_unicode

from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
from forms import CMSUploadForm, WPUploadForm
from models import DocumentsProcessed
from ebdata.nlp import addresses

class CMSUtility(object):
    
    def __init__(self, config, blogid='story'):
        self.config = config
        self.blogid = blogid
        self.posts = []
        self.posted_posts = []
        
        if config.cms_type == 'WP':
            self._pyblog = pyblog.WordPress(config.cms_url, config.cms_user,
                config.cms_pass)
            self.form = WPUploadForm
        elif config.cms_type == 'DR': 
            self._pyblog = pyblog.MetaWeblog(config.cms_url, config.cms_user,
                config.cms_pass, appkey='')
            self.form = CMSUploadForm
        elif config.cms_type == 'MT':
            self._pyblog = pyblog.MovableType(config.cms_url, config.cms_user,
                config.cms_pass)
            blogs = self._pyblog.get_users_blogs()
            self.blogid = blogs[0]['blogid']
            self.form = CMSUploadForm
        elif config.cms_type == 'BL':
            self._pyblog = pyblog.Blogger(config.cms_user, config.cms_pass)
            self.blogid = self._pyblog.blog_id
            self.form = CMSUploadForm
        else:
            raise pyblog.BlogError('Unsupported Blog Type')
    
    def get_categories(self):
        return self._pyblog.get_categories(self.blogid)
    
    def get_links(self):
        links = []
        for post in self.posted_posts:
            if type(post) == dict and 'permaLink' in post:
                links.append(post['permaLink'])
            elif getattr(post, 'link', None):
                links.append(post.link[-1].href)            
            else:
                pass
        return links
                
    def upload_image(self, image_file, path):
        tmp_file_name = path + os.path.sep + image_file.name
        tmp_file = open(tmp_file_name, 'w')
        
        for chunk in image_file.chunks():
            tmp_file.write(chunk)
        tmp_file.close()
        
        tmp_file= open(tmp_file_name)
        data = xmlrpclib.Binary(tmp_file.read())
        tmp_file.close()
        
        os.unlink(tmp_file_name)
        
        image = self._pyblog.new_media_object({'name': image_file.name, 
            'type': image_file.content_type, 'bits': data, 
            'overwrite': 'true'})
        
        return image
        
    def parse_form(self, form, isZip=False, isHierarchy=False):
        post_file = form.cleaned_data['post_file']
        layout = form.cleaned_data['layout']
        dir_structure = form.cleaned_data['dir_structure']
        
        if isZip:
            self.posts = process_zip_file(post_file, layout=layout, 
                dir_structure=dir_structure)
        else:
            post = process_file(post_file, layout=layout)
        
            if 'image_file' in form.cleaned_data:
                if form.cleaned_data['image_file']:
                    image_file = form.cleaned_data['image_file']
                    img = self.upload_image(image_file, settings.TEMP_FILES)
                    post['description'] += '<br/><img src="' + img['url'] + '"/>'

            if self.config.cms_type == 'WP':
                pub_date = form.cleaned_data['date']
                post['dateCreated'] = xmlrpclib.DateTime(
                    time.mktime(pub_date.timetuple()))
                post['mt_keywords'] = form.cleaned_data['tags']
                post['categories'] = [form.cleaned_data['category']]
            
            self.posts.append(post)
        
    def post_stories(self):
        for post in self.posts:
            self.create_story(post)
    
    def create_story(self, post):
        if not post['title'] and not post['description']:
            return False
      
        address = post.pop('address', None) 
        latitude = post.pop('latitude', None)
        longitude = post.pop('longitude', None)
      
        post_id = self._pyblog.new_post(post, True, self.blogid)
        if 'category' in post:
            self.add_category(post_id, post['category'])
        posted_post = self._pyblog.get_post(post_id)
        
        self.posted_posts.append(posted_post)
        
        if address and self.config.cms_type == 'WP':
            try:
                idx = self._pyblog.methods.index('wpgeo.setCoords')
                coords = self._pyblog.server.wpgeo.setCoords(post_id, 
                    self._pyblog.username, self._pyblog.password, 
                    {'_wp_geo_latitude': latitude, 
                    '_wp_geo_longitude': longitude})
            except ValueError, AttributeError:
                pass
        increase_docs(1)
      
    def add_category(self, post_id, category):
        cat_id = 0
        for cat in self.get_categories():
            if cat['categoryName'] == category:
                cat_id = int(cat['categoryId'])
        
        if not cat_id:
            cat_id = self._pyblog.new_category({'name': category,
                'slug': category.replace(' ', '-'), 'parent_id': 0,
                'description': category})
                
        post = self._pyblog.get_post(post_id)
        post['categories'] = [category]
        self._pyblog.edit_post(post_id, post, True)
        
def prepare_story(config, post):
    story = {}
    
    story['title'] = post['title']
    story['description'] = post['description']
        
    if config.cms_type == 'WP':
        if 'date' in post and post['date']:    
            pub_date = post['date']
            story['dateCreated'] = xmlrpclib.DateTime(
                time.mktime(pub_date.timetuple()))

        if 'tags' in post and post['tags']:
            story['mt_keywords'] = post['tags']
        if 'category' in post and post['category']:
            story['categories'] = [post['category']]
        if 'status' in post and post['status']:
            story['status'] = post['status']
            
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
    
def increase_docs(how_many=1):
    dp = DocumentsProcessed.objects.get(id=1)
    dp.total += how_many
    dp.save()
    
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