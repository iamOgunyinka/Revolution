from flask_mail import Mail, Message
from flask import current_app
from threading import Thread

mail = Mail()

def asyncSendMail( app, message, toMail ):
	with app.app_context():
		try:
			mail.send( message )
		except:
			print "Unable to send mail to %r" % toMail

def sendMail( fromMail, toMail, subject, messageBody ):
	app = current_app._get_current_object()
	message = Message( subject, sender = fromMail, recipients = [ toMail ] )
	message.body = messageBody
	thr = Thread( target = asyncSendMail, args = [ app, message, toMail ] )
	thr.start()
	return thr
