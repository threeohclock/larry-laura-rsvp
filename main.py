#!/usr/bin/env python

import os
from datetime import datetime
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from appengine_utilities import sessions


template.register_template_library('django.contrib.humanize.templatetags.humanize')

DEBUGGING = False
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
ORDINALS = ('First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth', 'Seventh', 'Eighth')

JQUERY_DATE_FORMAT = '%m/%d/%Y'
JsDate = lambda pydate: pydate.strftime(JQUERY_DATE_FORMAT)

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

class RequestHandler(webapp.RequestHandler):
  def WriteTemplate(self, filename, kwargs):
    self.response.out.write(template.render(os.path.join(TEMPLATE_DIR, filename), kwargs))

  def DEBUG(self, msg):
    if not DEBUGGING:
      return
    self.response.out.write('DEBUG: ' + msg + '<br />')

  def ERROR(self, msg, filename='error.html', template_vars={}):
    template_vars['errormessage'] = msg
    self.WriteTemplate(filename, template_vars)

  def NAVERROR(self):
    self.WriteTemplate('get_keyword.html', {'errormessage': 'Sorry, browsing directly to that page is not supported.  Please re-enter your secret word.'})

  def get(self):
    self.NAVERROR()

def GetSession():
  return sessions.Session(writer="cookie")

def GetUserFromSession():
  sess = GetSession()
  party = Party.get_by_id(sess['party_key_id'])
  if not party:
    self.ERROR('Failure trying to look up your account from your session, please re-enter your secret word', 'get_keyword.html')
  return party

class PopulateTestData(RequestHandler):
  def get(self):
    foo = Party(name='Test Party 1',
                secret='foo',
                email='datavortex+foo@gmail.com')
    bar = Party(name='Test Party 2',
                secret='bar',
                email='datavortex+bar@gmail.com')
    baz = Party(name='Test Party 3',
                secret='baz',
                email='datavortex+baz@gmail.com',
                size=5,
                people_names=['Person One','Person Two'])
    foo.put()
    bar.put()
    baz.put()
    self.DEBUG('Created test data.')


class LandingWithoutKeyword(RequestHandler):
  """Initial Page that prompts for secret word. """
  def get(self):
    self.WriteTemplate('get_keyword.html', {})

class SecretWord(RequestHandler):
  def get(self):
    """Gets secret word from URL."""
    secret = self.request.path.lstrip('/').strip().lower()
    self.DEBUG('secret: "%s"' % secret)
    self.HandleSecretWord(secret)

  def post(self):
    """Get the secret word from a form."""
    secret = self.request.get('keyword').strip().lower()
    self.DEBUG('secret: "%s"' % secret)
    self.HandleSecretWord(secret)

  def HandleSecretWord(self, secret_word):
    if not secret_word:
      self.ERROR('Your secret word cannot be blank!', 'get_keyword.html')
      return
    parties = db.GqlQuery("SELECT * FROM Party WHERE secret = :1 LIMIT 2", secret_word)
    matched = parties.count()
    if matched > 1:
      self.ERROR('Got more than one wedding party matched for the secret word %s: %s' % (secret_word, [p.name for p in parties]))
      return
    if not matched:
      self.ERROR('Sorry, that does not appear to be a valid secret word.  Please try again.', 'get_keyword.html')
      return
    party = parties.get()
    sess = GetSession()
    sess['party_key_id'] = party.key().id()
    template_vars = {'name': party.name}
    self.DEBUG('Is coming type: %s' % party.is_coming)
    if party.is_coming is not None:
      if party.is_coming:
        template_vars['coming'] = True
      else:
        template_vars['not_coming'] = True
    self.WriteTemplate('is_coming.html', template_vars)

class YesOrNo(RequestHandler):
   def post(self):
    """Handle yes and no responses."""
    coming = self.request.get('coming')
    self.DEBUG('coming: "%s"' % coming)
    party = GetUserFromSession()
    if coming == 'no':
      party.is_coming = False
      party.put()
      self.WriteTemplate('notcoming.html', {})
      return
    if coming == 'yes':
      party.is_coming = True
      party.put()
      template_vars = {'size': party.size,
                       'names': party.people_names,
                       '1to8': map(None, ORDINALS, party.people_names)}
      self.WriteTemplate('party_detail.html', template_vars)
      return
    self.ERROR('Please select either yes or no!', 'is_coming.html', {'name': party.name})

class PartyDetails(RequestHandler):
  def post(self):
    """Get count of guests and guest names."""
    party = GetUserFromSession()
    party.size = int(self.request.get('coming'))
    names = [self.request.get('name%s' % n).strip() for n in range(1, party.size+1)]
    party.people_names = names
    party.put()
    self.DEBUG('Coming count: "%s"<br>Names are: %s' % (party.size, party.people_names))
    template_vars = {'room': party.room_number, 'hotel': party.hotel_name}
    if party.arrival_date and party.departure_date:
      template_vars['arrival'] = JsDate(party.arrival_date)
      template_vars['departure'] = JsDate(party.departure_date)
    self.WriteTemplate('trip_detail.html', template_vars)

class TripDetails(RequestHandler):
  def post(self):
    """Get count of guests and guest names."""
    party = GetUserFromSession()
    room = self.request.get('roomnumber')
    hotel = self.request.get('hotelname')
    try:
      party.arrival_date = datetime.strptime(self.request.get('from'), JQUERY_DATE_FORMAT).date()
      party.departure_date = datetime.strptime(self.request.get('to'), JQUERY_DATE_FORMAT).date()
    except:
      template_vars = {'room': room, 'hotel': hotel}
      if party.arrival_date:
        template_vars['arrival'] = JsDate(party.arrival_date)
      if party.departure_date:
        template_vars['departure'] = JsDate(party.departure_date)
      self.DEBUG('Template vars: %s' % template_vars)
      self.ERROR('Sorry, I didn\'t understand those arrival and departure dates.  Please use the selection widgets, or enter them in a MM/DD/YYYY format.', 'trip_detail.html', template_vars)
      return

    if party.arrival_date > party.departure_date:
      template_vars = {'room': room, 'hotel': hotel}
      self.ERROR('The departure date (%s) cannot be before the arrival date (%s)!' % (JsDate(party.departure_date), JsDate(party.arrival_date)), 'trip_detail.html', template_vars)
      return

    if room:
      party.room_number = int(room)
      party.hotel_name = None
    elif hotel:
      party.room_number = None
      party.hotel_name =  hotel
    else:
      template_vars = {'room': party.room_number, 'hotel': party.hotel_name}
      if party.arrival_date and party.departure_date:
        template_vars['arrival'] = JsDate(party.arrival_date)
        template_vars['departure'] = JsDate(party.departure_date)
      self.ERROR('Please select a room at Ana y Jose, type in a different hotel, or select one from the list.', 'trip_detail.html', template_vars)
      return
    # party.put()
    self.DEBUG('Arrival date: %s<br>Departure date: %s<br>Room number: %s<br>Hotel name: %s' % (party.arrival_date, party.departure_date, party.room_number, party.hotel_name))
 

def main():
   application = webapp.WSGIApplication([('/', LandingWithoutKeyword),
                                         ('/test', PopulateTestData),
                                         ('/secretword', SecretWord),
                                         ('/yesorno', YesOrNo),
                                         ('/partydetail', PartyDetails),
                                         ('/tripdetail', TripDetails),
                                         ('/.{1,10}', SecretWord)],
                                        debug=DEBUGGING)
   util.run_wsgi_app(application)


if __name__ == '__main__':
    main()