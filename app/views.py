from flask import Blueprint
from flask import abort, request, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_uploads import UploadSet, UploadNotAllowed, IMAGES
from models import RegisteredUsers, GetHelpTransaction, ProvideHelpTransaction, MatchedTransaction
from models import CompletedTransactions, db
from resources import sendConfirmationMessage, endUserExpiryInterval, statusCodes, getCurrentTime
from resources import SynchronizedDatabaseSession
from status import generateStatus, sendDictMessage
from sqlalchemy_searchable import search
from datetime import datetime, time, date
import os


auth = Blueprint( 'auth', __name__ )
api =  Blueprint( 'revol', __name__ )
login_manager = LoginManager()
synced_session = SynchronizedDatabaseSession()

login_manager.session_protection = 'strong'
login_manager.login_view = 'revol.loginHandler'
APP_TOKEN = os.environ.get( 'APP_TOKEN' )
AMOUNT = 10000
uploaded_photos = UploadSet( 'photos', IMAGES )

@login_manager.user_loader
def loadUsers( email ):
	return RegisteredUsers.query.filter_by( email = email ).first()

@api.app_errorhandler( 404 )
def pageNotFound( e ):
	return generateStatus( status_code = 0, reason = 11, optional_detail = str( e ) )

@api.app_errorhandler( 405 )
def methodNotAllowed( e ):
	return generateStatus( status_code = 0, reason = 405, optional_detail = str( e ) )

@api.app_errorhandler( 400 )
def badRequest( e ):
	return generateStatus( status_code = 0, reason = 400, optional_detail = str( e ) )

@api.app_errorhandler( 500 )
def internalServerError( e ):
	return sendDictMessage( { 'Error': 'Internal server error' } )

@api.route( '/revol/register', methods=['POST'] )
def registerationHandler():
	data = request.get_json()
	if data == None:
		return generateStatus( status_code = 0, reason = 3 )
	
	email = data.get( 'email' )
	if ( email == None or len( email ) < 8 ):
		return generateStatus( status_code = 0, reason = 5 )
		
	# Todo - validate email.
	email_exists = RegisteredUsers.query.filter_by( email = email ).first()
	
	if( email_exists is not None ):
		return generateStatus( status_code = 0, reason = 6 )
	
	password = data.get( 'password' )
	fullname = data.get( 'name' )
	city = data.get( 'city' )
	state = data.get( 'state' )
	mobileNumber = data.get( 'mobile' )
	bankName = data.get( 'bank_name' )
	accountName = data.get( 'account_name' )
	accountNumber = data.get( 'account_number' )
	
	passwordIsEmpty 	= password == None or len( password ) < 4
	fullnameIsEmpty 	= fullname == None or len( fullname ) == 0
	cityIsEmpty 		= city == None or len( city ) == 0
	stateIsEmpty 		= state == None or len( state ) == 0
	cellNumberIsEmpty 	= mobileNumber == None or len( str( mobileNumber ) ) == 0 
	bankNameIsEmpty 	= bankName == None or len( bankName ) == 0 
	accoutNameIsEmpty 	= accountName == None or len( accountName ) == 0 
	accountNumberIsEmpty = accountNumber == None or len( str( accountNumber ) ) == 0
	
	if( passwordIsEmpty or fullnameIsEmpty or cityIsEmpty or stateIsEmpty or cellNumberIsEmpty \
		or bankNameIsEmpty or accountNumberIsEmpty or accoutNameIsEmpty ):
		return generateStatus( status_code = 0, reason = 7 )

	passwordHash = RegisteredUsers.generatePasswordHash( password )
	
	newUser = RegisteredUsers( isConfirmed = False, isBlacklisted = False, email = email, passwordHash = passwordHash, \
		fullname = fullname, city = city, stateOfResidence = state, phone = mobileNumber, bankName = bankName, \
		accountName = accountName, accountNumber = accountNumber, dateOfRegistration = getCurrentTime() )
	
	
	#~ anchor_id = synced_session.addDbTransaction( newUser )
	#~ sendConfirmationMessage( newUser, APP_TOKEN )
	#~ return generateStatus( status_code = 1, reason = 1, anchor = anchor_id )
	
	db.session.add( newUser )
	db.session.commit()
	sendConfirmationMessage( newUser, APP_TOKEN )
	return generateStatus( status_code = 1, reason = 1 )


@api.route( '/revol/confirm_reg', methods = ['POST', 'GET'] )
def userConfirmationHandler():
	if( request.method == 'GET' ):
		#e.g. http://URL/revol/confirm_reg?code=aiody-syrw.sdreiure
		code = request.args.get( 'code' )
		result = RegisteredUsers.confirmUserWithToken( endUserExpiryInterval, code, APP_TOKEN )
		if( result[0] == True ):
			return generateStatus( status_code = 1, reason = result[1] )
		else:
			return generateStatus( status_code = 0, reason = result[1] )
	
	# else -> reconfirm user
	data = request.get_json()
	if data == None:
		return generateStatus( status_code = 0, reason = 3 )
	
	email = data.get( 'email' )
	if ( email is None or len( email ) == 0 ):
		return generateStatus( status_code = 0, reason = 10 )
	email_exists = RegisteredUsers.query.filter_by( email = email ).first()
	
	if( email_exists is None ):
		return generateStatus( status_code = 0, reason = 10 )
	if( user.isConfirmed == True ):
		return generateStatus( status_code = 0, reason = 13 )
	
	sendConfirmationMessage( user, APP_TOKEN )
	return generateStatus( status_code = 1, reason = 1 )

@api.route( '/revol/login', methods=['POST'] )
def loginHandler():
	data = request.json
	if( data == None ):
		return generateStatus( status_code = 0, reason = 3 )
	
	email = data.get( 'email' )
	password = data.get( 'password' )
	user = RegisteredUsers.query.filter_by( email = email ).first()
	
	## Does the user exist at all or is he blacklisted?
	if user is None or user.confirmPassword( password ) is not True:
		return generateStatus( status_code = 0, reason = 1 )
	
	if not user.isConfirmed:
		return generateStatus( status_code = 0, reason = 4 )
	
	reuseSession = False
	login_user( user, reuseSession )
	return generateStatus( status_code = 1, reason = 0 )

@api.route( '/revol/logout' )
@login_required
def logoutHandler():
	logout_user()
	return generateStatus( status_code = 1, reason = 10 )


@api.route( '/revol/cph/<email>', methods = ['POST', 'GET'] )
@login_required
def provideHelpHandler( email ):
	user = db.session.query( RegisteredUsers ).filter_by( email = email ).first()
	if( user == None or user.isConfirmed is False ):
		return generateStatus( status_code = 0, reason = 102 )
		
	if request.method == 'GET':
		created_ph = db.session.query( ProvideHelpTransaction ).filter_by( email = email ).first()
		if( created_ph == None ):
			#no ph has been created
			return generateStatus( status_code = 1, reason = 103 )
		return ProvidedHelp.phToJson( created_ph )
	
	created_ph = db.session.query( ProvideHelpTransaction ).filter_by( email = email ).first()
	if created_ph is not None: #ph request is already available
		return generateStatus( status_code = 0, reason = 104 )
	
	current_dtime = getCurrentTime()
	ph_request = ProvideHelpTransaction( email = email, amount = AMOUNT, timeCreated = current_dtime )
	try:
		db.session.add( ph_request )
		db.session.commit()
	except:
		#unable to add PH Request
		return generateStatus( status_code = 0, reason = 105 )
	return generateStatus( status_code = 1, reason = 2 )

@api.route( '/revol/cgh/<email>' )
@login_required
def getHelpHandler( email ):
	user = db.session.query( RegisteredUsers ).filter_by( email = email ).first()
	if( user is None or user.isConfirmed is False or user.isBlacklisted is True ):
		return generateStatus( status_code = 0, reason = 102 )
	gh_request = db.session.query( GetHelpTransaction ).filter_by( email = email ).first()
	return GetHelp.ghToJson( gh_request )

@api.route( '/revol/cancelph/<email>', methods = ['POST'] )
@login_required
def cancelPHRequestHandler( email ):
	user = db.session.query( RegisteredUsers ).filter_by( email = email ).first()
	if( user is None or user.isConfirmed is False or user.isBlacklisted is True ):
		return generateStatus( status_code = 0, reason = 102 )
	data = request.get_json()
	if( data is None ):
		return generateStatus( status_code = 0, reason = 0 )
	transaction_id = data.get( 'transaction_id' )
	created_ph = db.session.query( ProvideHelpTransaction ).filter_by( transaction_id = transaction_id ).first()
	if( created_ph is None ):
		return generateStatus( status_code = 0, reason = 12 )
	try:
		db.session.delete( created_ph )
		db.session.commit()
	except:
		return generateStatus( status_code = 0, reason = 124 )
	return generateStatus( status_code = 1, reason = 1 )
	
@api.route( '/revol/confirm_ph/<email>', methods = [ 'POST' ] )
@login_required
def confirmPHRequestHandler( email ):
	user = db.session.query( RegisteredUsers ).filter_by( email = email ).first()
	if( user == None or user.isConfirmed is False or user.isBlacklisted is True ):
		return generateStatus( status_code = 0, reason = 102 )
	data = request.get_json()
	if( data is None ):
		return generateStatus( status_code = 0, reason = 0 )
	transaction_id = data.get( 'transaction_id' )
	matched_transaction = db.session.query( MatchedTransaction ).filter_by( transaction_id = transaction_id ).first()
	if( matched_transaction is None ):
		return generateStatus( status_code = 0, reason = 123 )
		
	if( matched_transaction.receiver_email != email ):
		return generateStatus( status_code = 0, reason = 125 )
	
	if( matched_transaction.transaction_status != MatchedTransaction.AWAITING_CONFIRMATION_TRANSACTION ):
		return generateStatus( status_code = 0, reason = 106 )
	matched_transaction.transaction_status = MatchedTransaction.COMPLETED_TRANSACTION
	try:
		db.session.add( matched_transaction )
		db.session.commit()
	except:
		matched_transaction.transaction_status = MatchedTransaction.PENDING_TRANSACTION	
		return generateStatus( status_code = 0, reason = 124 )
	return generateStatus( status_code = 1, reason = 1 )
	
@api.route( '/revol/open_dispute/<email>', methods = ['POST'] )
@login_required
def openPaymentDispute( email ):
	pass
	
@api.route( '/revol/ipaid/<email>', methods = ['POST'] )
@login_required
def iPaidHandler( email ):
	user = db.session.query( RegisteredUsers ).filter_by( email = email ).first()
	if( user is None or user.isConfirmed is False or user.isBlacklisted is True ):
		return generateStatus( status_code = 0, reason = 102 )
	photo = request.files.get( 'photo' )
	filename = None
	if not photo:
		return generateStatus( status_code = 0, reason = 105 )
	try:
		filename = uploaded_photos.save( photo )
	except UploadNotAllowed:
		return generateStatus( status_code = 0, reason = 106 )
	matched_transaction = db.session.query( MatchedTransaction ).filter_by( sender_email = email ).first()
	if( matched_transaction is None ):
		return generateStatus( status_code = 0, reason = 123 )
		
	if( matched_transaction.sender_email != email ):
		return generateStatus( status_code = 0, reason = 125 )
	
	if( matched_transaction.transaction_status != MatchedTransaction.PENDING_TRANSACTION ):
		return generateStatus( status_code = 0, reason = 107 )
	matched_transaction.transaction_status = MatchedTransaction.AWAITING_CONFIRMATION_TRANSACTION
	matched_transaction.uploaded_teller = filename
	try:
		db.session.add( matched_transaction )
		db.session.commit()
	except:
		matched_transaction.transaction_status = MatchedTransaction.PENDING_TRANSACTION
		return generateStatus( status_code = 0, reason = 108 )
	return generateStatus( 1, reason = 1 )

@api.route( '/revol/dashboard/<email>' )
@login_required
def dashboardHandler( email ):
	user = db.session.query( RegisteredUsers ).filter_by( email = email ).first()
	if( user == None or user.isConfirmed is False or user.isBlacklisted is True ):
		return generateStatus( status_code = 0, reason = 102 )
	all_transactions = db.session.query( CompletedTransactions ).filter_by( email = user.email ).all()
	return CompletedTransactions.toJson( all_transactions )
