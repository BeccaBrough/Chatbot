from django.db import models

class Participant(models.Model):
	identity = models.CharField(max_length=128,
		help_text='Phone number')
	step = models.CharField(max_length=128, default = 'beginning',
		help_text='Next step in chatbot steps')
	iterations = models.IntegerField(default=0)

	# Information about the user.
	LANGUAGE_CHOICES = (
		('??', 'unknown'),
		('EN', 'english'),
		('ES', 'spanish'),
		('ZH', 'chinese'),
		('VI', 'vietnamese')
	)
	language = models.CharField(max_length=10, default='??', choices = LANGUAGE_CHOICES)

	dtaflag = models.CharField(max_length=11, default = '')
	address = models.CharField(max_length=128, default = '')
	firstname = models.CharField(max_length=128, default = '')
	lastname = models.CharField(max_length=128, default = '')
	email = models.CharField(max_length=128, default = '')
	dtacard = models.CharField(max_length=128, default='')
	gender = models.CharField(max_length=128, default = '')
	intake_done = models.DateTimeField(null=True)

	# Uses a discount charlie card.
	uses_discount_card = models.CharField(max_length=11, default = '')
	# Monthly t-pass from employer.
	uses_corporate_card = models.CharField(max_length=11, default = '')
	# Free rides from program e.g. job training.
	uses_free_rides = models.CharField(max_length=11, default = '')
	# How they usually pay for charlie card.
	charlietype = models.CharField(max_length=128, default = '')

	# consent received actually
	card_received = models.DateTimeField(null=True)
	consent_q1 = models.CharField(max_length=11, default='')
	consent_q2 = models.CharField(max_length=11, default='')
	consent_q3 = models.CharField(max_length=11, default='')

	dem_age = models.CharField(max_length=128, default='')
	dem_work = models.CharField(max_length=128, default='')
	dem_race = models.CharField(max_length=128, default='')
	dem_dependents = models.CharField(max_length=11, default='')
	dem_single_parent = models.CharField(max_length=11, default='')

	baseline_health =  models.CharField(max_length=15, default='')
	baseline_stress = models.CharField(max_length=15, default='')
	baseline_stress2 = models.CharField(max_length=15, default='')
	baseline_transit = models.CharField(max_length=15, default='')
	baseline_done = models.DateTimeField(null=True)

	# the real card received
	card_received2 = models.DateTimeField(null=True)
	card_serials = models.CharField(max_length=128, default='')

	# For reference only.
	PARTICIPANT_TYPES = [
		'unknown',
		'control',
		'treatment',
		'discount',
		'extra',
		'exclude'
	]
	participant_type = models.CharField(max_length=15, default='unknown')

	def __getitem__(self, item):
		return getattr(self, item)

class Diary(models.Model):
	identity = models.CharField(max_length=128)
	# Timestamp for the entry AUTOMATICALLY
	date_log = models.DateTimeField(auto_now=True)
	# Date of the trip being referenced
	date_trip = models.DateTimeField(null=True)

	# User diary response
	text = models.CharField(max_length=128)

	# Added manually if needed to "delete" the entry without actually deleting it
	invalid = models.CharField(max_length=11, default='')
	# Added manually if a note about the diary entry is needed.
	comments = models.CharField(max_length=128, default = '')

	def __getitem__(self, item):
		return getattr(self, item)

# One run of the lottery will contain 3 winners.
class Lottery(models.Model):
	# Date of the trip being referenced
	date_trip = models.DateTimeField(null=True)
	# Automatic timestamp.
	date_lottery_ran = models.DateTimeField(auto_now=True)
	# Timestamp for when the $5 is mailed
	date_mailed = models.DateTimeField(null=True)

	# Stores identity.
	winner1 = models.CharField(max_length=128, null=True)
	winner2 = models.CharField(max_length=128, null=True)
	winner3 = models.CharField(max_length=128, null=True)

	def __getitem__(self, item):
		return getattr(self, item)

class Weekly(models.Model):
	identity = models.CharField(max_length=128)
	# Timestamp for the entry
	timestamp = models.DateTimeField(auto_now_add=True)

	# Either obstacles, ratembta, or elaborate.
	questiontype = models.CharField(max_length=128)

	response = models.CharField(max_length=128)

	def __getitem__(self, item):
		return getattr(self, item)
