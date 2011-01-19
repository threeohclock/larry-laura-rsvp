#!/usr/bin/env python

import os
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from appengine_utilities import sessions

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
def GetTemplatePath(filename):
  return os.path.join(template_dir, filename)

class Party(db.Model):
  name = db.StringProperty(required=True)
  secret = db.StringProperty(required=True)
  email = db.EmailProperty(required=True)
  is_coming = db.BooleanProperty()
  size = db.IntegerProperty()
  people_names= db.StringListProperty()
  room_number = db.IntegerProperty()
  hotel_name = db.StringProperty()
  arrival_date = db.DateProperty()
  departure_date = db.DateProperty()
  chicken = db.IntegerProperty()
  fish = db.IntegerProperty()
  hidden_worlds = db.IntegerProperty()
  tulum_ruins = db.IntegerProperty()
  tulum_ruins_time = db.DateTimeProperty()
  notes = db.TextProperty()
  date = db.DateTimeProperty(auto_now_add=True)

class PopulateTestData(webapp.RequestHandler):
  def get(self):
    foo = Party(name='Test Party 1', secret='foo', email='datavortex+foo@gmail.com')
    bar = Party(name='Test Party 2', secret='bar', email='datavortex+bar@gmail.com')
    foo.put()
    bar.put()
    self.response.out.write('Created test data.')
    

class LandingWithoutKeyword(webapp.RequestHandler):
  """Initial Page that prompts for secret word. """
  def get(self):
    path = GetTemplatePath('get_keyword.html')
    self.response.out.write(template.render(path, {}))

class SecretWord(webapp.RequestHandler):
  def get(self):
    """Gets secret word from URL."""
    secret = self.request.path.lstrip('/').strip().lower()
    self.response.out.write('DEBUG: secret: "%s"<br>' % secret)
    self.HandleSecretWord(secret)

  def post(self):
    """Get the secret word from a form."""
    secret = self.request.get('keyword').strip().lower()
    self.response.out.write('DEBUG: secret: "%s"<br>' % secret)
    self.HandleSecretWord(secret)

  def HandleSecretWord(self, secret_word):
    if not secret_word:
      self.response.out.write('DEBUG: Secret word cannot be blank!<br>')
      return
    parties = db.GqlQuery("SELECT * FROM Party WHERE secret = :1 LIMIT 2", secret_word)
    matched = parties.count()
    if matched > 1:
      self.response.out.write('ERROR: Got more than one secret word match: %s' % [p.name for p in parties])
      return
    if not matched:
      self.response.out.write('ERROR: No parties with that secret word found.')
      return    
    party = parties.get()
    self.response.out.write(template.render(GetTemplatePath('is_coming.html'), {'name': party.name}))
   
class YesOrNo(webapp.RequestHandler):      
   def post(self):
    """Handle yes and no responses."""
    coming = self.request.get('coming')
    self.response.out.write('DEBUG: coming: "%s"<br>' % coming)
    if coming == 'no':
      return
    if coming == 'yes':
      return
    self.response.out.write('DEBUG: coming was not yes or no!<br>')
    

def main():
    application = webapp.WSGIApplication([('/', LandingWithoutKeyword),
                                          ('/test', PopulateTestData),
                                          ('/secretword', SecretWord),
                                          ('/yesorno', YesOrNo),
                                          ('/.{1,10}', SecretWord)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
