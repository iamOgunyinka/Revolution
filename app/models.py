from itsdangerous import TimedJSONWebSignatureSerializer as TimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy_searchable import make_searchable
from sqlalchemy_utils.types import TSVectorType
import os

db = SQLAlchemy( session_options = { 'expire_on_commit' : False } )
make_searchable()

class RegisteredUsers( UserMixin, db.Model ):
	__tablename__ = 'all_users'
	
	registrationNumber = db.Column( db.Integer, unique = True, index = True, 
									primary_key = True, autoincrement = True )
	email = db.Column( db.UnicodeText, unique = True, index = True )
	passwordHash = db.Column( db.UnicodeText )
	fullname = db.Column( db.UnicodeText )
	city = db.Column( db.Unicode( 100 ) )
	stateOfResidence = db.Column( db.Unicode( 100 ) )
	phone = db.Column( db.Unicode( 15 ), index = True, nullable = False )
	bankName = db.Column( db.UnicodeText, index = True, nullable = False )
	accountNumber = db.Column( db.Unicode( 100 ), index = True, nullable = False )
	accountName = db.Column( db.Unicode( 100 ), index = True, nullable = False )
	dateOfRegistration = db.Column( db.DateTime() )
	isConfirmed = db.Column( db.Boolean, default = False )
	isBlacklisted = db.Column( db.Boolean, default = False )
	
	def __repr__( self ):
		return "<RegisteredUser - ( Registration number: %r ) Email: %r, PasswordHash = %r >"% \
			( self.registrationNumber, self.email, self.passwordHash )
	
	def get_id( self ):
		return self.email
	
	def confirmPassword( self, password ):
		return check_password_hash( self.passwordHash, password )
	
	@staticmethod
	def generatePasswordHash( password ):
		return generate_password_hash( password )
	
		
	@staticmethod
	def generateConfirmationToken( email, expiry, appToken ):
		s = TimedSerializer( os.environ.get( 'END_USERS_SEC' ), expires_in = expiry )
		return s.dumps( { 'endUsers': str( email ), 'appToken' : str( appToken ) } )
		
	@staticmethod
	def confirmUserWithToken( expiry, token, appToken ):
		s = TimedSerializer( os.environ.get( 'END_USERS_SEC' ), expires_in = expiry )
		data_obtained = None
		try:
			data_obtained = s.loads( token )
		except:
			return ( False, 8 )
		
		apptoken_validation = ( appToken == unicode( data_obtained.values()[0] ) )
		fetched_username = db.session.query( RegisteredUsers ).filter_by( email = unicode( data_obtained.values()[1] ) ).first()
		
		if fetched_username is None or apptoken_validation is None:
			return ( False, 8 )
		
		fetched_username.isConfirmed = True
		db.session.add( fetched_username )
		db.session.commit()
		return ( True, 2 )

class HelpTransactionBase():
	GET_HELP_TRANSACTION = 0
	PROVIDE_HELP_TRANSACTION = 1
	
	transaction_id = db.Column( db.Integer, index = True, primary_key = True, autoincrement = True, 
						unique = True )
	email = db.Column( db.UnicodeText, index = True, unique = True )
	amount = db.Column( db.Integer )
	timeCreated = db.Column( db.DateTime(), nullable = False )
	

class ProvideHelpTransaction( HelpTransactionBase, db.Model ):
	__tablename__ = 'ph_table_transactions'
	transaction_type = HelpTransactionBase.PROVIDE_HELP_TRANSACTION
	
	def __repr__( self ):
		return "<Provide Help -- transaction_id: %d, user_email: %r >" % ( self.transaction_id, self.email )

class GetHelpTransaction( HelpTransactionBase, db.Model ):
	__tablename__ = 'gh_table_transactions'
	transaction_type = HelpTransactionBase.GET_HELP_TRANSACTION
	
	def __repr__( self ):
		return "<Get Help -- transaction_id: %d, user_email: %r >" % ( self.transaction_id, self.email )
	
class MatchedTransaction( db.Model ):
	__tablename__ = 'matched_transactions'
	
	PENDING_TRANSACTION = 0
	COMPLETED_TRANSACTION = 1
	CANCELLED_TRANSACTION = 2
	AWAITING_CONFIRMATION_TRANSACTION = 3
	
	transaction_id = db.Column( db.Integer, index = True, primary_key = True, unique = True,
								autoincrement = True )
	sender_email = db.Column( db.UnicodeText, index = True, unique = True )
	receiver_email = db.Column( db.UnicodeText, index = True )
	opened_date = db.Column( db.DateTime(), nullable = False )
	closed_date = db.Column( db.DateTime(), nullable = False )
	uploaded_teller = db.Column( db.UnicodeText, nullable = True )
	transaction_status = db.Column( db.Integer )

class CompletedTransactions( db.Model ):
	__tablename__ = 'completed_transactions'
	transaction_id = db.Column( db.UnicodeText, index = True, primary_key = True, unique = True )
	sender_regId = db.Column( db.UnicodeText, index = True, unique = True )
	receiver_regId = db.Column( db.UnicodeText, index = True )
	transaction_status = db.Column( db.Integer )
