from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import db

from resources import endUserExpiryInterval, developerExpiryInterval
import os

def createApplicationInstance():
	app = Flask( __name__ )
	app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get( 'DATABASE_URI' )
	app.config['SQLACHEMY_COMMIT_ON_TEARDOWN'] = True
	
	db.init_app( app )
	return app

from models import RegisteredUsers, GetHelpTransaction, ProvideHelpTransaction, MatchedTransaction, CompletedTransactions
from views import api, login_manager, AMOUNT, synced_session, uploaded_photos
from email_service import mail
from resources import ONE_HOUR, TWENTY_FOUR_HOURS, endUserExpiryInterval, getCurrentTime, getPreviousDate
