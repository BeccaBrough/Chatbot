from django.conf import settings

import smtplib
import os

from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from email.header import Header

from .language import translate as _


cache_server = None
def connect_smtp():
	global cache_server

	# Check if the server is still open.
	if cache_server is not None:
		try:
			if cache_server.noop()[0] == 250:
				return cache_server
		except:
			# smtplib.SMTPServerDisconnected
			pass

	# Authenticate ourselves to Gmail.
	cache_server = smtplib.SMTP('smtp.gmail.com', 587)
	cache_server.ehlo()
	cache_server.starttls()
	cache_server.login(settings.GMAIL_EMAIL, settings.GMAIL_PASSWORD)

	return cache_server

def email_consent(person):
	mail = MIMEMultipart()
	mail['From'] = settings.GMAIL_EMAIL
	mail['To'] = person.email
	mail['Date'] = formatdate(localtime=True)
	mail['Subject'] = Header('MIT Research Survey Information', 'UTF-8')

	with open(os.path.join(os.path.dirname(__file__), _('file.consent_htm', person.language))) as f:
		mail.attach(MIMEText(f.read(), 'html', _charset='UTF-8'))

	consent = os.path.join(os.path.dirname(__file__), _('file.consent', person.language))
	with open(consent, 'rb') as file:
		part = MIMEApplication(file.read(), Name = basename(consent))

	part['Content-Disposition'] = 'attachment; filename="%s"' % basename(consent)
	mail.attach(part)

	connect_smtp().sendmail(settings.GMAIL_EMAIL, person.email, mail.as_string())
