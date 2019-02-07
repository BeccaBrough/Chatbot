from .models import Participant, Diary, Lottery, Weekly
from rapidsms.apps.base import AppBase
from rapidsms.models import Connection
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from .language import translate as _
from .consent import email_consent

import json
import os
import re
import warnings
import string
import random
import datetime

# Matches <char+>@<char+>.<char+> with only one @.
emailRe = re.compile('^[^@\s]+@[^@\s]+\.[^@\s]+$')

filename = os.path.join(os.path.dirname(__file__), 'steps.json')
with open(filename) as f:
	steps = json.load(f)

class Responder(AppBase):
	def handle(self, msg):
		# Associate the texter with a Participant model.
		try:
			person = Participant.objects.get(identity = msg.connection.identity)
		except ObjectDoesNotExist:
			# We need to create a participant for them.
			person = Participant(identity = msg.connection.identity)
			person.save()

		# TODO: remove this before production. Used for testing only.
		if msg.text.strip() == '!#!deleteme!':
			msg.respond('Deleting your user. Text back to start again.')
			person.step = 'deleteuser'
		elif msg.text.strip() == '!#!consent.check1!':
			person.step = 'consent.check1'
			person.iterations = 0
		elif msg.text.strip() == '!#!gimmeparticipanttypediscount!':
			person.participant_type = 'discount'
			person.save()
			return True
		elif msg.text.strip() == '!#!gimmeparticipanttypetreatment!':
			person.participant_type = 'treatment'
			person.save()
			return True
		elif msg.text.strip() == '!#!lottery.fake!' and msg.connection.identity in ['+16262613981']:
			fake = Participant(identity = '4534534433')
			fake.firstname = 'Personified'
			fake.save()

			yesterday = timezone.now() - datetime.timedelta(days=1)
			lot = Lottery(date_trip = yesterday, date_lottery_ran=yesterday, winner1 = fake.identity)
			lot.save()

			msg.respond('Faked lottery, winner = %s.' % fake.identity)
			return True
		elif msg.text.strip() == '!#!send.consent.check1!' and msg.connection.identity in ['+16262613981', '+16179393824']:
			# Moves people who a) have not received consent info but b) have finished intake
			# To begin the consent process.
			targets = Participant.objects.filter(card_received=None).exclude(intake_done=None)

			for target in targets:
				conn = Connection.objects.get(identity=target.identity)
				target.step = 'consent.check1'
				target.iterations = 1
				target.save()

				respond(msg, target, target=conn)

			msg.respond('Moved %d participants to consent.check1.' % len(targets))

			return True

		elif msg.text.strip()[:19] == '!#!send.individual!' and msg.connection.identity in ['+16262613981', '+16179393824']:
			# !#!send.individual!+16179393824!baseline.health!
			#   !#!send.individual! = [:19]
			#   +16179393824 = [20:31]
			#   baseline.health = [33:-1]
			target = Participant.objects.filter(identity=msg.text.strip()[20:31])
			if len(targets) == 0:
				msg.respond('Participant not found.')
			#Possibly add check to make sure the step is a valid step
			#elif msg.text.strip()[33:-1] IN LIST OF VALID STEPS:
			#	msg.respond('Next step not valid.')
			else
				conn = Connection.objects.get(identity=target.identity)
				target.step = msg.text.strip()[33:-1]
				target.iterations = 1
				target.save()

				respond(msg, target, target=conn)

			msg.respond('Successful.')

			return True
		elif msg.text.strip()[:19] == '!#!send.group!' and msg.connection.identity in ['+16262613981', '+16179393824']:
			# !#!send.group!a!baseline.health!
			# !#!send.group! = [:14]
			# a = [15]
			# baseline.health = [17:-1]

			targets = Participant.objects.filter(send_group_flag=msg.text.strip()[15])

			for target in targets:
				conn = Connection.objects.get(identity=target.identity)
				target.step = msg.text.strip()[17:-1]
				target.iterations = 1
				target.save()

				respond(msg, target, target=conn)

			msg.respond('Moved %d participants.' % len(targets))

			return True

		elif msg.text.strip() == '!#!send.notify!' and msg.connection.identity in ['+16262613981', '+16179393824']:
			# Moves all participants to the notification phase starting with baseline.health
			targets = Participant.objects.filter(baseline_done = None).exclude(participant_type='exclude').exclude(participant_type='unknown')
			for target in targets:
				conn = Connection.objects.get(identity=target.identity)
				target.step = 'baseline.health'
				target.iterations = 1
				target.save()

				respond(msg, target, target=conn)

			msg.respond('Moved %d participants to baseline.health.' % len(targets))

			return True

		elif msg.text.strip() == '!#!send.card.received!' and msg.connection.identity in ['+16262613981', '+16179393824']:
			# Moves participants (except those with existing discount pass) to check if card received
			targets = Participant.objects.exclude(baseline_done = None).filter(card_received2 = None).exclude(participant_type='exclude').exclude(participant_type='unknown').exclude(participant_type='discount')
			for target in targets:
				conn = Connection.objects.get(identity=target.identity)
				target.step = 'card.received'
				target.iterations = 1
				target.save()

				respond(msg, target, target=conn)

			msg.respond('Moved %d participants to card.received.' % len(targets))

			return True

		elif msg.text.strip() == '!#!send.diary!' and msg.connection.identity in ['+16262613981', '+16179393824']:
			# To be triggered at 9am every morning.

			# Check if any lottery is from today; if so, decline to re-run.
			today = timezone.now()
			yesterday = today - datetime.timedelta(days=1)
			todaysLottery = Lottery.objects.filter(date_lottery_ran__year=today.year, date_lottery_ran__month=today.month, date_lottery_ran__day=today.day)
			if len(todaysLottery) > 0:
				msg.respond('Lottery seems to have already been run today (winner1 = %s)... Declining to run.' % todaysLottery[0].winner1)
				return True

			# Run the lottery: grab all diary entries, set their date to the day before,
			# and choose 3 as the winners.
			diaries = Diary.objects.filter(date_trip = None)

			winners = []
			if len(diaries) > 0:
				for diary in diaries:
					diary.date_trip = yesterday
					diary.save()

				while len(winners) < 3 and len(diaries) - len(winners) > 0:
					winner = diaries[random.randint(0, len(diaries) - 1)].identity
					if winner not in winners:
						winners.append(winner)

				winners.sort()

				msg.respond('Found %d winners: %s' % (len(winners), ', '.join(winners)))

				if len(winners) == 3:
					lottery = Lottery(date_trip = yesterday, winner1 = winners[0], winner2 = winners[1], winner3 = winners[2])
					lottery.save()
				else:
					msg.respond('Not saving lottery because it had fewer than 3 winners/diary entries.')

			# First, who has already started the diary? Send them to diary.text
			targets = Participant.objects.exclude(participant_type='exclude').exclude(participant_type='unknown').exclude(diary.started=None)
			for target in targets:
				conn = Connection.objects.get(identity=target.identity)
				# if target has won yesterday's lottery:
				if target.identity in winners:
					target.step = 'diary.winner'
				else:
					target.step = 'diary.text'
				target.iterations = 1
				target.save()

				respond(msg, target, target=conn)
			msg.respond('Moved %d current participants to diary.' % len(targets))

			# Second, who hasn't started diary who is in the study? Send them to diary.text2
			targets = Participant.objects.filter(diary.started=None).exclude(participant_type='exclude').exclude(participant_type='unknown')
			for target in targets:
				conn = Connection.objects.get(identity=target.identity)
				target.step = 'diary.text1'
				target.diary_started = timezone.now()
				target.iterations = 1
				target.save()

				respond(msg, target, target=conn)
			msg.respond('Moved %d new participants to diary.' % len(targets))

			return True

		while True:
			# Act on the previous step's information.
			if person.step == '':
				break

			step = steps[person.step]
			if step['type'] == 'message':
				# Just send a message.
				respond(msg, person)

				person.step = step['next']
			elif step['type'] == 'question':
				# If they haven't been asked the question, ask it.
				if person.iterations == 0:
					person.iterations += 1
					# "message": null tells us to send no message.
					if 'message' not in step or step['message'] != None:
						respond(msg, person)

					break

				# Otherwise, parse their response, possibly giving them an error and another try.
				# Trim whitespace, make lowercase (so comparisons are case-insensitive).
				response = msg.text.strip()

				if len(response) > 511:
					respond(msg, person, step = 'error.response_too_long')

					person.iterations += 1
					if person.iterations > 3:
							respond(msg, person, step = 'error.help')

					break

				# Check the response type.
				if step['response']['type'] == 'enum':
					# Retrieve possible answer values for a given language.
					possibles = map(lambda s: 'response.%s' % s, step['response']['values'])
					possibles = map(lambda k: _(k, person.language).split('|'), possibles)
					# Flatten.
					possiblesFlattened = [item for sublist in possibles for item in sublist]

					# Lowercase, remove periods and commas.
					sanitizedResponse = response.lower().replace('.', '').replace(',', '')
					if sanitizedResponse not in possiblesFlattened:
						# Retrieve first response from each list.
						possiblesFirst = ', '.join(map(lambda arr: arr[0], possibles))
						respond(msg, person, step = 'question.bad.enum', placeholders = {'{possibles}': possiblesFirst})

						person.iterations += 1
						if person.iterations > 3:
							respond(msg, person, step = 'error.help')

						break

					# Set response to the language-agnostic response.
					for value in step['response']['values']:
						if sanitizedResponse in  _('response.%s' % value, person.language).split('|'):
							response = value
							break
				# Email can either be an email or "negative" (as it is optional).
				elif step['response']['type'] == 'email':
					# Retrieve possible 'no' values for their language.
					possibles = _('response.negative', person.language).split('|')

					if response.lower() in possibles:
						response = 'negative'
					elif not emailRe.match(response.lower()):
						respond(msg, person, step = 'question.bad.enum', placeholders = {'{possibles}': 'your email, "no"'})

						person.iterations += 1
						if person.iterations > 3:
							respond(msg, person, step = 'error.help')

						break
				elif step['response']['type'] == 'diary':
					diary = Diary(identity = person.identity, text = response)
					diary.save()
				elif step['response']['type'] == 'weekly':
					weekly = Weekly(identity = person.identity, questiontype = step['response']['tag'], response = response)
					weekly.save()
				elif step['response']['type'] == 'helpme':
					helpme = Weekly(identity = person.identity, step=person.step, response = response)
					helpme.save()

				# Could be 'string', but we don't need to change on that.

				if 'store' in step['response']:
					# Save the response to the model.
					setattr(person, step['response']['store'], response)

				# Next could be specific to the message.
				if type(step['next']) is dict:
					person.step = step['next'][response.lower()]
				else:
					person.step = step['next']

				person.iterations = 0
			elif step['type'] == 'set':
				for var in step['values']:
					val = step['values'][var]

					if step['values'][var] == ':now':
						val = timezone.now()

					setattr(person, var, val)

				person.step = step['next']
			elif step['type'] == 'fork':
				# Fork could be unrelated to the database, if so, it's "check".
				if 'check' in step:
					if step['check'] == ':issunday':
						issunday = 'affirmative' if (timezone.now().weekday() == 6) else 'negative'
						person.step = step['next'][issunday]
					else:
						warnings.warn('Unexpected check type %s' % step['check'])
						person.step = 'error'

					break

				# Send the connection to a different step depending on a database property.
				value = person[step['value']]

				if ':email' in step['next'] and emailRe.match(value):
					value = ':email'

				if value in step['next']:
					person.step = step['next'][value]
				else:
					warnings.warn('Expected value "%s" at step %s' % (value, person.step))
					person.step = 'error'

			elif step['type'] == 'deleteuser':
				person.delete()

				return True

			elif step['type'] == 'sendemail':
				email_consent(person)

				person.step = step['next']

			elif step['type'] == 'passthrough':
				person.step = step['next']

			else:
				warnings.warn('Use of unimplemented module type %s' % step['type'])
				person.step = step['next']

		person.save()

		return True

def respond(msg, person, step = None, placeholders = dict(), target = None):
	if step is None:
		step = person.step

		if 'message' in steps[person.step]:
			placeholders = placeholders.copy()
			placeholders.update(steps[person.step]['message'])

	text = _(step, person.language)

	for key in placeholders:
		value = placeholders[key]
		# $expression means we need to retrieve it from the database.
		if value.startswith('$'):
			value = person[value[1:]]
		elif value == '^winner':
			# Retrieve the first winner of the last lottery.
			try:
				latest = Lottery.objects.latest('date_lottery_ran')
				value = Participant.objects.get(identity = latest.winner1).firstname
			except:
				value = 'Brendan'
		elif value == '^yesterdaydow':
			value = _('dow.%d' % (timezone.now() - datetime.timedelta(days=1)).weekday(), person.language)
		elif value == '^ratembta':
			value = Weekly.objects.filter(identity=person.identity, questiontype='ratembta').order_by('-id')[0].response

		text = string.replace(text, key, value)

	if target is None:
		msg.respond(text)
	else:
		msg.respond(text, connections = [target])

