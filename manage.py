#!/usr/bin/env python

from app import api, createApplicationInstance, db, mail, synced_session, uploaded_photos
from app import login_manager, ONE_HOUR, AMOUNT, TWENTY_FOUR_HOURS, getCurrentTime
from app import RegisteredUsers, MatchedTransaction, GetHelpTransaction, ProvideHelpTransaction, getPreviousDate
from threading import Thread, Lock, Condition
from sqlalchemy.orm.mapper import configure_mappers
import logging, os, time
from datetime import datetime, timedelta
from flask import current_app
from flask_uploads import configure_uploads

appInstance = createApplicationInstance()
appInstance.secret_key = os.environ.get( 'SECRET_KEY' )
appInstance.register_blueprint( api )
appInstance.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

appInstance.config['MAIL_SERVER'] = 'smtp.googlemail.com'
appInstance.config['MAIL_PORT'] = 587
appInstance.config['MAIL_USE_TLS'] = True
appInstance.config['MAIL_USERNAME'] = os.environ.get( 'MAIL_USERNAME' )
appInstance.config['MAIL_PASSWORD'] = os.environ.get( 'MAIL_PASSWORD' )
appInstance.config['UPLOADS_DEFAULT_DEST'] = os.environ.get( 'UPLOADED_PHOTOS_DEST' )


def autoGH( app ):
	with app.app_context():
		while( True ):
			ghList = db.session.query( GetHelpTransaction ).all()
			if ghList is not None:
				current_date_time = getCurrentTime()
				for gh_item in ghList:
					time_since_phed = gh_item.timeCreated - current_date_time
					if( time_since_phed.seconds < TWENTY_FOUR_HOURS ):
						pass
					phList = db.session.query( ProvideHelpTransaction ).all()
					if phList is not None and len( phList ) > 1:
						for index in range( 0, 2, 1 ):
							ph_item = phList[index]
							match = MatchedTransaction( sender_email = ph_item.email,
										receiver_email = gh_item.email,
										opened_date = datetime.utcnow(),
										closed_date = getCurrentTime() + timedelta( 0, TWENTY_FOUR_HOURS ),
										transaction_status = MatchedTransaction.PENDING_TRANSACTION )
							db.session.add( match )
							db.session.delete( ph_item )
						db.session.delete( gh_item )
						db.session.commit()
			time.sleep( 10 ) #Perform GH every hour

def createAutoGHThread():
	thread = Thread( target = autoGH, args = [ current_app._get_current_object() ] )
	thread.start()

def adminAutoGH( adminQuery, app ):
	with app.app_context():
		while( True ):
			adminGH = db.session.query( GetHelpTransaction ).filter_by( email = adminQuery.email ).first()
			if adminGH is None:
				adminGH = GetHelpTransaction( email = adminQuery.email, amount = AMOUNT * 2, timeCreated = getPreviousDate() )
				db.session.add( adminGH )
				db.session.commit()
			time.sleep( 10 )

def createAdminAutoGHThread():
	app = current_app._get_current_object()
	with app.app_context():
		admin = db.session.query( RegisteredUsers ).filter_by( registrationNumber = 1 ).first()
		if( admin is None ):
			env = os.environ
			admin = RegisteredUsers( email = env.get( 'ADMIN_EMAIL' ), fullname = env.get( 'ADMIN_NAME' ),
						phone = env.get( 'ADMIN_CELL' ), bankName = env.get( 'ADMIN_BANK_NAME' ),
						accountName = env.get( 'ADMIN_ACCT_NAME' ), isConfirmed = True,
						accountNumber = env.get( 'ADMIN_ACCT_NUMBER' ), dateOfRegistration = getCurrentTime() )
			db.session.add( admin )
			db.session.commit()
		thread = Thread( target = adminAutoGH, args = [ admin, app ] )
		thread.start()
	
def createMatchedTransactionSanitizer( app ):
	with app.app_context():
		while True:
			matched_list = db.session.query( MatchedTransaction ).all()
			if matched_list is not None:
				for matched_item in matched_list:
					#Move confirmed transactions to GetHelp
					if matched_item.transaction_status == MatchedTransaction.COMPLETED_TRANSACTION:
						gh_item = GetHelpTransaction( email = matched_item.sender_email, amount = AMOUNT * 2 )
						db.session.add( gh_item )
						db.session.delete( matched_item )
						db.session.commit()
					elif ( matched_item.closed_date - matched_item.opened_date ).seconds > TWENTY_FOUR_HOURS:
						sender = db.session.query( RegisteredUsers ).filter_by( email = matched_item.sender_email ).first()
						gh_item = GetHelpTransaction( email = matched_item.receiver_email, amount = AMOUNT )
						sender.isBlacklisted = True
						db.session.add( gh_item )
						db.session.add( sender )
						db.session.commit()
			time.sleep( 10 )


def createMatchedTransactionSanitizerThread():
	thread = Thread( target = createMatchedTransactionSanitizer, args = [ current_app._get_current_object() ] )
	thread.start()


@appInstance.before_first_request
def before_first_request():
	db.configure_mappers()
	#~ db.drop_all()
	db.create_all()
	mail.init_app( appInstance )
	login_manager.init_app( appInstance )
	configure_uploads( appInstance, ( uploaded_photos, ))
	createAutoGHThread()
	createAdminAutoGHThread()
	createMatchedTransactionSanitizerThread()

#~ @appInstance.after_request
#~ def afterRequest( a ):
	#~ db.session.commit()
	

if __name__ == '__main__':
	appInstance.run()
