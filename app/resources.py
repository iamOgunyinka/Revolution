from email_service import sendMail
from status import generateStatus
from flask import render_template, jsonify, request
from flask_mail import Message, Mail
from flask_restful import Resource
from functools import wraps
from models import RegisteredUsers
from datetime import timedelta, datetime
from threading import RLock
import os, Queue

ONE_HOUR 				= 60 * 60
TWENTY_FOUR_HOURS 		= ONE_HOUR * 24
endUserExpiryInterval 	= ONE_HOUR * 12
developerExpiryInterval = ONE_HOUR * 12

## The mapped values below are not really used in code but are kept for documentation of error messages
statusMessageMap = { 0 : u'Error', 1 : u'OK' }
errorMessageMap  = { 0 : u'Invalid application token',
					1 : u'Login attempt failed',
					2 : u'Registration failed',
					3 : u'Invalid request body, specify HTTP header \'Accept\' as \'application/json\'',
					4 : u'Account needs verification',
					5 : u'Username or email not specified',
					6 : u'Username or email already registered, try a new one or login',
					7 : u'Other registration parameters may have been omitted',
					8 : u'Invalid or expired application token',
					9 : u'Invalid user or application token',
					10: u'Username, email or password may have been omitted',
					11: u'Username with email combination is incorrectly supplied',
					12: u'Password does not match',
					13: u'User has already been confirmed',
					15: u'Invalid or insufficient argument in query string',
					16: u'Could not understand the request sent, please check the manual and resend request.',
					17: u'You need to be logged in. Send a POST request containing your username and password',
					18: u'Unable to save data into the database'
				}
okMessageMap     = { 0 : 'Login successful',
					 1 : 'Registration successful, check your email for account verification',
					 2 : 'Your account successfully confirmed',
					 3 : 'Data saved successfully'
				   }

statusCodes = { 'codes': statusMessageMap,
        'error messages': errorMessageMap,
        'success messages': okMessageMap 
        }

def sendConfirmationMessage( user, appToken ):
	email = user.email
	token = RegisteredUsers.generateConfirmationToken( email, endUserExpiryInterval, appToken )
	
	print "Confirmation token is %s" % token
	fromMail = 'Admin@T.R.Investment'
	body = render_template( 'end_user_confirm.txt', name = user.fullname, appName = 'The Revolution Investment', linkUrl = token )
	sendMail( fromMail, email, subject = '[T.R. Investment] Confirm your account', messageBody = body )

def getCurrentTime():
	return datetime.utcnow() + timedelta( 0, ONE_HOUR )

def getPreviousDate():
	return datetime.utcnow() - timedelta( 0, TWENTY_FOUR_HOURS )

class SynchronizedDatabaseSession():
	db = None
	db_queue = None
	lock = None
	
	def __init__( self, db = None):
		self.db = db
		self.db_queue = Queue.Queue()
		self.lock = RLock()

	def initDb( db ):
		self.db = db

	def queueDbTransaction( transaction ):
		self.db_queue.put( transaction )
	
	def queueDbTransactionAsync( transaction, callback ):
		self.db_queue.put( { 'ts': transaction, 'cb': callback } )
