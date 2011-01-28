#!/usr/bin/env python

import os
import confirmation_mail
from datetime import datetime
from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from appengine_utilities import sessions


template.register_template_library('django.contrib.humanize.templatetags.humanize')

DEBUGGING = True
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
ORDINALS = ('First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth', 'Seventh', 'Eighth')
FOOD_CHOICES = ('Steak', 'Fish', 'Vegetarian')

ROOMS = {0: 'We are staying elsewhere',
         1: 'Amanecer',
         2: 'Brisa del Mar',
         3: 'Nube',
         4: 'Lluvia',
         5: 'Sol',
         6: 'Luna',
         7: 'Tulum',
         8: 'Palmera',
         9: 'Caracol',
        10: 'Coral',
        11: "Sian Ka'an",
        12: 'Ana',
        13: 'Atardecer',
        14: 'Jose',
        15: 'Carpinteria',
        16: 'Casa de Patron',
        17: 'Estrella del Mar',
        18: 'Agua de Mar',
        19: 'Encantada',
        20: 'Capricho',
        22: 'Arena',
        23: 'Coba Villa'}

JQUERY_DATE_FORMAT = '%m/%d/%Y'
JsDate = lambda pydate: pydate.strftime(JQUERY_DATE_FORMAT)
Names = lambda party: [p.name for p in party.people]

class Party(db.Model):
  name = db.StringProperty(required=True)
  secret = db.StringProperty(required=True)
  email = db.EmailProperty(required=True)
  is_coming = db.BooleanProperty()
  size = db.IntegerProperty()
  room_number = db.IntegerProperty()
  notes = db.TextProperty()
  creation_date = db.DateTimeProperty(auto_now=True)
  modified_date = db.DateTimeProperty(auto_now_add=True)
  confirmed_once = db.BooleanProperty()

class Person(db.Model):
  name = db.StringProperty(required=True)
  meal = db.StringProperty(choices=set(FOOD_CHOICES))
  party = db.ReferenceProperty(Party, collection_name='people')
  hidden_worlds = db.BooleanProperty()
  creation_date = db.DateTimeProperty(auto_now=True)
  modified_date = db.DateTimeProperty(auto_now_add=True)

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

def PrettyList(unpretty_list):
  if not unpretty_list:
    return ''
  if len(unpretty_list) == 1:
    return unpretty_list[0]
  elif len(unpretty_list) == 2:
    return ' and '.join(unpretty_list)
  else:
    end_of_list = ', %s and %s' % (unpretty_list.pop(-2), unpretty_list.pop())
    return ', '.join(unpretty_list) + end_of_list

class PopulateTestData(RequestHandler):
  def get(self):
    foo = Party(name='Test Party 1',
                secret='foo',
                email='datavortex+test@gmail.com').put()
    bar = Party(name='Test Party 2',
                secret='bar',
                size=2,
                email='datavortex+test@gmail.com').put()
    baz = Party(name='Test Party 3',
                secret='baz',
                email='datavortex+test@gmail.com',
                size=5).put()
    Person(name='Person One', meal='Steak', party=baz).put()
    Person(name='Person Two', meal='Fish', hidden_worlds=False, party=baz).put()
    Person(name='Person Three', meal='Vegetarian', hidden_worlds=True, party=baz).put()
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
                       '1to8': map(None, ORDINALS, party.people)}
      self.WriteTemplate('party_detail.html', template_vars)
      return
    self.ERROR('Please select either yes or no!', 'is_coming.html', {'name': party.name})

class PartyDetails(RequestHandler):
  def post(self):
    """Get count of guests and guest names."""
    party = GetUserFromSession()
    party.size = int(self.request.get('coming'))
    party.put()  # This needs to happen before adding new guests

    guests = {}  # No dictionary comprehensions in appengine's python 2.x
    for guest_number in range(1, party.size+1):
      if self.request.get('hiddenworlds%s' % guest_number):
        hiddenworlds = True
      else:
        hiddenworlds = False
      guests[self.request.get('name%s' % guest_number).strip()] = (
          self.request.get('meal%s' % guest_number), hiddenworlds)
    # Sets help decide if we should do an update, delete, and/or add
    existing_guests = set(Names(party))
    new_guests = set(guests.keys())

    # First delete existing guests that weren't on the form
    [p.delete() for p in party.people.filter('name IN', list(existing_guests - new_guests))]
    # Now that they're gone, update whoever is left
    for guest in party.people:
      guest.meal = guests[guest.name][0]
      guest.hidden_worlds = guests[guest.name][1]
      guest.put()
    # And add the new people:
    for guest in new_guests.difference(existing_guests):
      Person(name=guest, meal=guests[guest][0], hidden_worlds=guests[guest][1], party=party).put()

    template_vars = {'roomnumber': party.room_number, 'notes': party.notes, 'rooms': ROOMS}
    self.WriteTemplate('trip_detail.html', template_vars)
    self.DEBUG('Coming count: "%s"<br>Names are: %s' % (party.size, Names(party)))
    for guest in party.people:
      self.DEBUG('PERSON: Name: %s, Meal: %s, Hidden Worlds: %s' % (guest.name, guest.meal, guest.hidden_worlds))

class TripDetails(RequestHandler):
  def post(self):
    """Get room number and notes block."""
    party = GetUserFromSession()
    room = self.request.get('roomnumber')
    party.notes = self.request.get('notes')

    if room:
      party.room_number = int(room)
    if party.room_number:
      room = ROOMS[party.room_number]
    else:
      room = False

    if party.confirmed_once:
      subject = "Your RSVP to Our Wedding Was Updated"
    else:
      subject = "Confirmation of Your RSVP to Our Wedding"
    party.confirmed_once = True

    party.put()

    self.DEBUG('Room number: %s<br />Notes: "%s"' % (party.room_number, party.notes))
    #if not DEBUGGING:

    # Create the body of the message (a plain-text and an HTML version).
    template_vars = {'party': party,
                     'people': PrettyList([p.name for p in party.people]),
                     'room': room,
                     'hidden_worlds': PrettyList([p.name.split()[0] for p in party.people if p.hidden_worlds]),
                     'meals': PrettyList(list(set([p.meal.lower() for p in party.people])))}
    text = template.render(os.path.join(TEMPLATE_DIR, 'email_confirmation.txt'), template_vars)
    html = template.render(os.path.join(TEMPLATE_DIR, 'email_confirmation.html'), template_vars)
    mail.send_mail(sender='Larry and Laura <11-11-11@larryandlaura.us>',
                   to='%s <%s>' % (party.name, party.email),
                   subject=subject,
                   body=text,
                   html=html)
    self.WriteTemplate('confirmation.html', {'party': party})

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
