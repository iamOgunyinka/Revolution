from flask import jsonify

def generateStatus( status_code, reason, optional_detail = None ):
	if( optional_detail is None ):
		return jsonify( { 'status' : status_code, 'reason' : reason } )
	return jsonify( { 'status' : status_code, 'reason' : reason, 'detail' : optional_detail } )

def sendDictMessage( jsonMessage ):
	return jsonify( jsonMessage )
