# -*- coding: utf-8 -*-
import cgi
import os
import re

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import urlfetch
from google.appengine.ext import db
from xml.dom import minidom 

AFJV_URL = 'http://emploi.afjv.com/afjv_rss.xml'
METIERS = ['Administratif', 'Commercial / Marketing', 'Conception',
    u'Développement', 'Infographie', 'Management', 'Musique / Son', 'Presse / Communication',
    'Production', 'Support / Hotline', 'Technique',
    'Test / QA', 'Trad. / Localisation', 'Web / Internet']
PAYS = {
    'Allemagne': ['Germany', 'Allemagne'],
    'Argentine': ['Argentina', 'Argentine'],
    'Belgique': ['Belgium', 'Belgique'],
    'Canada': ['Canada'],
    'Chine': ['China', 'Chine'],
    u'Corée': ['Korea', u'Corée'],
    'Danemark': ['Denmark', 'Danemark'],
    'Espagne': ['Spain', 'Espagne', u'España'],
    'Etats-Unis': ['United States', 'Etats-Unis'],
    'France': ['France'],
    'Irlande': ['Ireland', 'Irlande'],
    'Italie': ['Italy', 'Italie'],
    'Japon': ['Japan', 'Japon'],
    'Mexique': ['Mexico', 'Mexique'],
    u'Nouvelle-Zélande': ['New Zealand', u'Nouvelle-Zélande'],
    'Philippines': ['Philipinnes', 'Philippines'],
    'Roumanie': ['Romania', 'Romanie'],
    'Royaume-Uni': ['United Kingdom', 'Angleterre'],
    u'Corée du sud': ['South Korea', u'Corée du sud'],
    'Suisse': ['Switzerland', 'Suisse'],
    'Ukraine': ['Ukraine'],
    'Vietnam': ['Vietnam']
}
ROLES = ['Emploi', 'Stage']

class Request(db.Model):
    categories = db.StringListProperty()
    date = db.DateTimeProperty(auto_now_add=True)

def parse(url) :
  result = urlfetch.fetch(url)
  if result.status_code == 200:
    return minidom.parseString(result.content) 
  
class MainPage(webapp.RequestHandler):
  def read_fieldsets(self):
    fieldsets = []
    
    roles = []
    for role in ROLES:
      roles.append({
        'type': u'checkbox',
        'name': role,
        'value': role
      })
    fieldsets.append({
      'legend': u'Emploi et stage',
      'inputs': roles
    })
    
    countries = []
    for country, code in sorted(PAYS.items()):
      countries.append({
        'type': u'checkbox',
        'name': country,
        'value': country
      })
      
    fieldsets.append({
      'legend': u'Pays',
      'inputs': countries,
    })
    
    jobs = []
    for job in METIERS:
      jobs.append({
        'type': u'checkbox',
        'name': job,
        'value': job
      })
    fieldsets.append({
      'legend': u'Métiers',
      'inputs': jobs,
    })
    
    return fieldsets
    
  def read_categories(self):
    categories = []

    for role in ROLES:
      add_role = self.request.get_all(role)
      if not add_role:
        categories.append(role)
    
    for country, codes in sorted(PAYS.items()):
        add_country = self.request.get_all(country)
        if not add_country:
          categories = categories + codes
    
    for job in METIERS:
      add_job = self.request.get_all(job)
      if not add_job:
        categories.append(job)

    return categories
    
  def get(self):
    fieldsets = self.read_fieldsets()
        
    template_values = {
      'fieldsets': fieldsets,
    }
    
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.headers['Content-Type'] = "text/html;charset=UTF-8"
    self.response.out.write(template.render(path, template_values))

  def post(self):
    categories = self.read_categories()
    request = Request()
    request.categories = categories
    key = request.put()
    
    self.redirect("/feed/" + str(key.id()) + ".xml")

class Feed(webapp.RequestHandler):
  def filter_items_by_category(self, categories):
    url = AFJV_URL
    dom = parse(url)
    items = []
    for item in dom.getElementsByTagName('item'):
      add_item = True
      for category in item.getElementsByTagName('category'):
        if category.firstChild.data.strip() in categories:
          add_item = False
          break
      if add_item:
        items.append({
          'title': cgi.escape(item.getElementsByTagName('title')[0].firstChild.data),
          'link': cgi.escape(item.getElementsByTagName('link')[0].firstChild.data),
          'description': cgi.escape(item.getElementsByTagName('description')[0].firstChild.data),
          'pubDate': item.getElementsByTagName('pubDate')[0].firstChild.data,
          'category0': cgi.escape(item.getElementsByTagName('category')[0].firstChild.data),
          'category1': cgi.escape(item.getElementsByTagName('category')[1].firstChild.data),
          'category2': cgi.escape(item.getElementsByTagName('category')[2].firstChild.data),
          'guid': item.getElementsByTagName('guid')[0].firstChild.data
        })
    return items

  def get(self):
    m = re.search(r"\/feed\/(?P<id>\d+)\.xml", self.request.path)
    id = m.group('id')
    request = Request.get_by_id(int(id))
    
    items = []    
    items = self.filter_items_by_category(request.categories)

    channels = []
    channels.append({
      'title': u'Emploi et stage des industries multimédia et jeux vidéo',
      'description': u'Les offres d\'emploi et de stage récentes en multimédia et jeux vidéo : chef de produit, chef de projet, game / level designer, infographiste, programmeur, testeur, web designer, etc.'
    })
    
    template_values = {
      'channels': channels,
      'items': items,
    }
    
    path = os.path.join(os.path.dirname(__file__), "feed.xml")
    self.response.headers['Content-Type'] = "text/xml;charset=UTF-8"
    self.response.out.write(template.render(path, template_values))

apps_binding = []
apps_binding.append(('/', MainPage))
apps_binding.append((r'/feed/.*', Feed))
application = webapp.WSGIApplication(apps_binding, debug=False)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
