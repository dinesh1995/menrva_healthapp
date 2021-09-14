from flask import Flask, jsonify, request, Response, abort, render_template, redirect, url_for, flash, session
from datetime import datetime, timedelta
import requests
import pdb
import json
import uuid
from flask_bcrypt import Bcrypt
import os


app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = "test1234"

auth_token = ''

def get_auth_token(force=False):
# 	global auth_token
# 	if auth_token == '' or force:
# 		auth_url = "https://04f17b24-94cd-447b-82ef-1b391e99778e-us-east1.apps.astra.datastax.com/api/rest/v1/auth"
# 		auth_headers = {'Content-type': 'application/json'}
# 		auth_data = {"username":os.environ.get('db_username'),"password":os.environ.get('db_password')}
# 		response = requests.post(auth_url, headers=auth_headers, json=auth_data)
# 		auth_token = response.json()['authToken']
# 	return auth_token
	return os.environ.get('db_token')

def cassandra_request(type, url, data={}, params=""):
	base_url = "https://04f17b24-94cd-447b-82ef-1b391e99778e-us-east1.apps.astra.datastax.com"
	url = base_url + url
	try:
		headers = {'Content-type': 'application/json','x-cassandra-token': get_auth_token()}
		response = requests.request(type, url, headers=headers, json=data, params=params)
		if response.status_code == 401:
			headers = {'Content-type': 'application/json','x-cassandra-token': get_auth_token(True)}
			response = requests.request(type, url, headers=headers, json=data, params=params)
		if type != 'DELETE':
				response = response.json()
		return response
	except Exception as e:
		print("DB Error - " + str(e))
		abort(Response(status=500, response=json.dumps({"db_connection_error":"Error in connecting with Datastax Astra DB. Try again after sometime"}), mimetype='application/json'))

#########################
### API Methods begin ###
#########################

# Create Patient (User Singup)
# {
# 	"name": "Patient5",
# 	"email": "patient5@test.com",
# 	"password": "test1234",
# 	"phone_number": "123456789",
# 	"age": 40,
# 	"gender": "Female",
# 	"profession": "Test",
# 	"city": "India",
# 	"patient_details": [{
# 			"key":"Have you ever suffered from suicidal thoughts?",
# 			"value":"No"
# 		},{ "key":"Are you suffering from panic attack",
# 			"value":"Sometimes"
# 		},{	"key":"Are you spiritual",
# 			"value":"Yes"
#		},{ "key":"Is your financial condition bothering you?",
# 			"value":"Yes it does"	
# 		}
# 	]
# }
@app.route('/api/users/patient', methods=['POST'])
def create_patient():
	request.json['id'] = str(uuid.uuid1())
	request.json['type'] = "patient"
	request.json['password'] = bcrypt.generate_password_hash(request.json['password']).decode("utf-8")
	patient_url = "/api/rest/v2/keyspaces/healthapp_keyspace/users"
	response = cassandra_request('POST', patient_url, request.json)
	patient_url = "/api/rest/v2/keyspaces/healthapp_keyspace/users/" + response['id']
	headers = {'Content-type': 'application/json','x-cassandra-token': get_auth_token()}
	response = cassandra_request('GET', patient_url)
	del response['data'][0]['doctor_details']
	return response

# Update patient - Sample payload
# {
# 	"name":"patient edited"
# }
@app.route('/api/users/patient/<user_id>', methods=['PUT'])
def update_patient(user_id):
	patient_url = "/api/rest/v2/keyspaces/healthapp_keyspace/users/" + user_id
	response = cassandra_request('PATCH', patient_url, request.json)
	patient_url = "/api/rest/v2/keyspaces/healthapp_keyspace/users/" + user_id
	headers = {'Content-type': 'application/json','x-cassandra-token': get_auth_token()}
	response = cassandra_request('GET', patient_url)
	del response['data'][0]['doctor_details']
	return response

# Create Doctor (Will be added by admin)
# {
# 	"name": "Doctor1",
# 	"email": "doctor1@test.com",
# 	"password": "test1234",
# 	"phone_number": "123456789",
# 	"age": 40,
# 	"gender": "Male",
# 	"profession": "Test",
# 	"city": "India",
# 	"doctor_details": [{
# 			"key":"Specialization",
# 			"value":"Phyciatrist"
# 		},{ "key":"Experience",
# 			"value":"10 years"	
# 		}
# 	]
# }
@app.route('/api/users/doctor', methods=['POST'])
def create_doctor():
	request.json['id'] = str(uuid.uuid1())
	request.json['type'] = "doctor"
	request.json['password'] = bcrypt.generate_password_hash(request.json['password']).decode("utf-8")
	doctor_url = "/api/rest/v2/keyspaces/healthapp_keyspace/users"
	response = cassandra_request('POST', doctor_url, request.json)
	doctor_url = "/api/rest/v2/keyspaces/healthapp_keyspace/users/" + response['id']
	response = cassandra_request('GET', doctor_url)
	del response['data'][0]['patient_details']
	return response

# Update doctor - Sample payload
# {
# 	"name":"doctor edited"
# }
@app.route('/api/users/doctor/<user_id>', methods=['PUT'])
def update_doctor(user_id):
	doctor_url = "/api/rest/v2/keyspaces/healthapp_keyspace/users/" + user_id
	response = cassandra_request('PATCH', doctor_url, request.json)
	doctor_url = "/api/rest/v2/keyspaces/healthapp_keyspace/users/" + user_id
	response = cassandra_request('GET', doctor_url)
	del response['data'][0]['patient_details']
	return response

# View all users
@app.route('/api/users')
def users():
	users_url = "/api/rest/v1/keyspaces/healthapp_keyspace/tables/users/rows"
	response = cassandra_request('GET', users_url)
	for index, data in enumerate(response['rows']):
		if data['type'] == "patient":
			del response['rows'][index]['doctor_details']
		else:
			del response['rows'][index]['patient_details']
	return response

# View single user - Can be patient or doctor
@app.route('/api/user/<user_id>')
def view_user(user_id):
	users_url = "/api/rest/v2/keyspaces/healthapp_keyspace/users/" + user_id
	response = cassandra_request('GET', users_url)
	if response['data'][0]['type'] == "patient":
		del response['data'][0]['doctor_details']
	else:
		del response['data'][0]['patient_details']
	return response

# View All Doctors
@app.route('/api/users/doctors', methods=['GET'])
def doctors():
	find_doctors_url = "/api/rest/v2/keyspaces/healthapp_keyspace/users"
	query_data = {'type': {'$eq': "doctor"}}
	response = cassandra_request('GET', find_doctors_url, {}, {'where':json.dumps(query_data)})
	for index, data in enumerate(response['data']):
		del response['data'][index]['patient_details']
	return response

# View All Patients
@app.route('/api/users/patients', methods=['GET'])
def patients():
	find_patients_url = "/api/rest/v2/keyspaces/healthapp_keyspace/users"
	query_data = {'type': {'$eq': "patient"}}
	response = cassandra_request('GET', find_patients_url, {}, {'where':json.dumps(query_data)})
	for index, data in enumerate(response['data']):
		del response['data'][index]['doctor_details']
	return response


# Login User - Both patient and doctor
# {
# 	"email":"test1@test.com",
# 	"password":"test1234"
# }
@app.route('/api/users/login', methods=['POST'])
def users_login():
	user_email = request.json['email']
	user_password = request.json['password']
	find_user_url = "/api/rest/v2/keyspaces/healthapp_keyspace/users"
	query_data = {'email': {'$eq': user_email}}
	response = cassandra_request('GET', find_user_url, {}, {'where':json.dumps(query_data)})
	if response['count'] == 1:
		if bcrypt.check_password_hash(response['data'][0]['password'],user_password):
			user_url = "/api/rest/v2/keyspaces/healthapp_keyspace/users/" + response['data'][0]['id']
			response = cassandra_request('GET', user_url)
			if response['data'][0]['type'] == "patient":
				del response['data'][0]['doctor_details']
			else:
				del response['data'][0]['patient_details']
			response['data'][0]['success'] = 'Valid user'
			return response['data'][0], 200
		else:
			return {"error":"Password is wrong"}, 403
	else:
		return {"error":"Email not found"}, 403


# Book Appointments - Sample payload
# {
# 	"patient_id": "f7b7efe1-765a-44f5-a125-87afac0cdc4e",
# 	"doctor_id": "27e50a8c-03eb-4cb3-a3c2-74cea7faa84a",
# 	"start_time": "2021-01-04T18:25:43Z",
# 	"end_time": "2021-01-04T19:25:43Z"
# }
@app.route('/api/book_appointment', methods=['POST'])
def book_appointment():
	request.json['id'] = str(uuid.uuid1())
	appointments_url = "/api/rest/v2/keyspaces/healthapp_keyspace/appointments"
	response = cassandra_request('POST', appointments_url, request.json)
	appointments_url = "/api/rest/v2/keyspaces/healthapp_keyspace/appointments/" + response['id']
	response = cassandra_request('GET', appointments_url)
	response['data'][0]['start_time'] = (datetime.fromtimestamp(response['data'][0]['start_time']['epochSecond']) - timedelta(hours=5, minutes=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
	response['data'][0]['end_time'] = (datetime.fromtimestamp(response['data'][0]['end_time']['epochSecond']) - timedelta(hours=5, minutes=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
	response['success'] = 'Appointment created successfully'
	return response

# View Appointments of a doctor
@app.route('/api/view_appointment/doctor/<user_id>', methods=['GET'])
def view_appointment_doctor(user_id):
	appointments_url = "/api/rest/v2/keyspaces/healthapp_keyspace/appointments"
	query_data = {'doctor_id': {'$eq': user_id}}
	response = cassandra_request('GET', appointments_url, {}, {'where':json.dumps(query_data)})
	for index, data in enumerate(response['data']):
		response['data'][index]['start_time'] = (datetime.fromtimestamp(response['data'][index]['start_time']['epochSecond']) - timedelta(hours=5, minutes=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
		response['data'][index]['end_time'] = (datetime.fromtimestamp(response['data'][index]['end_time']['epochSecond']) - timedelta(hours=5, minutes=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
	return response

# View Appointments of a patient
@app.route('/api/view_appointment/patient/<user_id>', methods=['GET'])
def view_appointment_patient(user_id):
	appointments_url = "/api/rest/v2/keyspaces/healthapp_keyspace/appointments"
	query_data = {'patient_id': {'$eq': user_id}}
	response = cassandra_request('GET', appointments_url, {}, {'where':json.dumps(query_data)})
	for index, data in enumerate(response['data']):
		response['data'][index]['start_time'] = (datetime.fromtimestamp(response['data'][index]['start_time']['epochSecond']) - timedelta(hours=5, minutes=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
		response['data'][index]['end_time'] = (datetime.fromtimestamp(response['data'][index]['end_time']['epochSecond']) - timedelta(hours=5, minutes=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
	return response

# Delete Appointments
@app.route('/api/delete_appointment/<id>', methods=['DELETE'])
def delete_appointment(id):
	appointments_url = "/api/rest/v2/keyspaces/healthapp_keyspace/appointments/"+id
	response = cassandra_request('DELETE', appointments_url)
	if response.status_code == 204:
		return {"success":"Appointment deleted"}, 204
	else:
		return {"error":"Error in deleting appointment"}, 500


# Add medicine - Sample payload
# {
# 	"name" : "BP Tablet",
# 	"patient_id": "f7b7efe1-765a-44f5-a125-87afac0cdc4e",
# 	"doctor_id": "27e50a8c-03eb-4cb3-a3c2-74cea7faa84a",
#	"quantity": "1",
# 	"intake_day_time": ["Mon-21:00","Tue-21:00","Thur-12:00","Fri-12:00"]
# }
@app.route('/api/add_medicine', methods=['POST'])
def add_medicine():
	request.json['id'] = str(uuid.uuid1())
	medicines_url = "/api/rest/v2/keyspaces/healthapp_keyspace/medicines"
	response = cassandra_request('POST', medicines_url, request.json)
	medicines_url = "/api/rest/v2/keyspaces/healthapp_keyspace/medicines/" + response['id']
	response = cassandra_request('GET', medicines_url)
	return response

# View all medicines of a patient
@app.route('/api/medicines/patient/<user_id>', methods=['GET'])
def view_medicines_patient(user_id):
	medicines_url = "/api/rest/v2/keyspaces/healthapp_keyspace/medicines"
	query_data = {'patient_id': {'$eq': user_id}}
	response = cassandra_request('GET', medicines_url, {}, {'where':json.dumps(query_data)})
	return response

# View medicines of a patient at specific day and time - Sample payload
# GET - http://127.0.0.1:5000/api/medicines/patient/f7b7efe1-765a-44f5-a125-87afac0cdc4e/notify?day_time=Mon-21:00
@app.route('/api/medicines/patient/<user_id>/notify', methods=['GET'])
def view_medicines_patient_notify(user_id):
	day_time = request.args['day_time']
	medicines_url = "/api/rest/v2/keyspaces/healthapp_keyspace/medicines"
	#query_data = {'patient_id': {'$eq': user_id}, 'intake_day_time': {'$contains':day_time}}
	query_data = {'patient_id': {'$eq': user_id}}
	response = cassandra_request('GET', medicines_url, {}, {'where':json.dumps(query_data)})
	notify = {"notify" : []}
	if response["data"]:
		for data in response["data"]:
			if day_time in data['intake_day_time']:
				notify["notify"].append({"name":data["name"],"quantity":data["quantity"],"day_time":day_time})
	return notify, 200


########################
### UI Methods begin ###
########################
@app.errorhandler(403)
def forbidden(e):
    return render_template("login.html"), 403

def check_auth(session):
	if 'user' not in session or session['user'] == None:
		flash("Please login to access that page!","error")
		abort(403)
	return cassandra_request('GET', "/api/rest/v2/keyspaces/healthapp_keyspace/users/" + session['user'])['data'][0]


@app.route('/', methods=['GET'])
def ui_default():
	return redirect(url_for('ui_login'))


@app.route('/ui/login', methods=['GET','POST'])
def ui_login():
	if request.method == 'GET':
		return render_template("login.html")
	if request.method == 'POST':
		user_email = request.form['email']
		user_password = request.form['psw']
		find_user_url = "/api/rest/v2/keyspaces/healthapp_keyspace/users"
		query_data = {'email': {'$eq': user_email}}
		response = cassandra_request('GET', find_user_url, {}, {'where':json.dumps(query_data)})
		if response['count'] == 1:
			if bcrypt.check_password_hash(response['data'][0]['password'],user_password):
				session['user'] = response['data'][0]['id']
				flash("Welcome "+response['data'][0]['name']+" !","success")
				return redirect(url_for('ui_home'))
			else:
				flash("Password is wrong!","error")
				return redirect(request.referrer)
		else:
			flash("Email not found!","error")
			return redirect(request.referrer)


@app.route('/ui/login_guest_patient', methods=['GET'])
def ui_login_guest_patient():
	session['user'] = 'c648964a-5933-11eb-aa2d-c6be8aa34a8b'
	response = cassandra_request('GET', "/api/rest/v2/keyspaces/healthapp_keyspace/users/" + session['user'])
	flash("Welcome "+response['data'][0]['name']+" !","success")
	return redirect(url_for('ui_home'))


@app.route('/ui/login_guest_doctor', methods=['GET'])
def ui_login_doctor_patient():
	session['user'] = 'ee51d980-5933-11eb-aa2d-c6be8aa34a8b'
	response = cassandra_request('GET', "/api/rest/v2/keyspaces/healthapp_keyspace/users/" + session['user'])
	flash("Welcome "+response['data'][0]['name']+" !","success")
	return redirect(url_for('ui_home'))


@app.route('/ui/register', methods=['GET','POST'])
def ui_register():
	if request.method == 'GET':
		return render_template("register.html")
	if request.method == 'POST':
		user_name = request.form['name']
		user_email = request.form['email']
		user_password = request.form['password']
		phone_num = request.form['phone_num']
		age = request.form['age']
		gender = request.form['gender']
		profession = request.form['profession']
		city = request.form['city']
		answer_1 = request.form['answer_1']
		answer_2 = request.form['answer_2']
		answer_3 = request.form['answer_3']
		answer_4 = request.form['answer_4']
		patient_details = [{
			"key": "Have you ever suffered from suicidal thoughts?",
			"value": answer_1
		},{
			"key": "Are you suffering from panic attack?",
			"value": answer_2
		},{
			"key": "Are you spiritual?",
			"value": answer_3
		},{
			"key": "Is your financial condition bothering you?",
			"value": answer_4
		}]

		request_data = {
			"id": str(uuid.uuid1()),
			"name": user_name,
			"email": user_email,
			"phone_number": phone_num,
			"age": age,
			"gender": gender,
			"profession": profession,
			"city": city,
			"patient_details": patient_details,
			"type": "patient"
		}
		request_data['password'] = bcrypt.generate_password_hash(user_password).decode("utf-8")
		patient_url = "/api/rest/v2/keyspaces/healthapp_keyspace/users"
		response = cassandra_request('POST', patient_url, request_data)
		if 'id' in response:
			flash("Account created successfully! Please login to continue","success")
			return redirect(url_for('ui_login'))
		else:
			flash("Error in account creation! Try again after sometime","error")
			return redirect(url_for('ui_login'))
		

@app.route('/ui/logout', methods=['GET'])
def ui_logout():
	session.pop('user', None)
	return render_template("login.html")


@app.route('/ui/home', methods=['GET'])
def ui_home():
	current_user = check_auth(session)
	return render_template("home.html", current_user=current_user)


@app.route('/ui/user/<id>', methods=['GET'])
def ui_user(id):
	current_user = check_auth(session)
	user_data = cassandra_request('GET', "/api/rest/v2/keyspaces/healthapp_keyspace/users/" + id)['data'][0]
	if user_data['type'] == 'patient':
		medicines_url = "/api/rest/v2/keyspaces/healthapp_keyspace/medicines"
		query_data = {'patient_id': {'$eq': user_data['id']}}
		user_data['medicines'] = cassandra_request('GET', medicines_url, {}, {'where':json.dumps(query_data)})['data']
	return render_template("user.html", current_user=current_user, user_data=user_data, view='users')


@app.route('/ui/doctors_list', methods=['GET'])
def ui_doctors_list():
	current_user = check_auth(session)
	find_doctors_url = "/api/rest/v2/keyspaces/healthapp_keyspace/users"
	query_data = {'type': {'$eq': "doctor"}}
	response = cassandra_request('GET', find_doctors_url, {}, {'where':json.dumps(query_data)})
	return render_template("doctors_list.html",current_user=current_user, data=response, view='doctors_list')


@app.route('/ui/book_appointment', methods=['POST'])
def ui_book_appointment():
	current_user = check_auth(session)
	apmt_data = str(request.get_data().decode('utf-8')).strip().replace('\n', '').replace(',', '').replace('%2F','-').replace('%3A',':')
	from_date = apmt_data.split('from_date=')[1].split('&')[0]
	from_time = apmt_data.split('from_time=')[1].split('&')[0]
	to_date = apmt_data.split('to_date=')[1].split('&')[0]
	to_time = apmt_data.split('to_time=')[1].split('&')[0]

	start_time = from_date+"T"+from_time+":00Z"
	end_time = to_date+"T"+to_time+":00Z"
	patient_id = str(session['user'])
	doctor_id = apmt_data.split('doctor_id=')[1].split('&')[0]
	request_data = {
		"patient_id": patient_id,
		"doctor_id": doctor_id,
		"start_time": start_time,
		"end_time": end_time
	}
	request_data['id'] = str(uuid.uuid1())
	appointments_url = "/api/rest/v2/keyspaces/healthapp_keyspace/appointments"
	response = cassandra_request('POST', appointments_url, request_data)
	if 'id' in response:
		return {'success': 'true'}
	else:
		return {'success': 'false'}


@app.route('/ui/appointments', methods=['GET'])
def ui_appointments():
	current_user = check_auth(session)
	appointments_url = "/api/rest/v2/keyspaces/healthapp_keyspace/appointments"
	if current_user['type'] == 'patient':
		query_data = {'patient_id': {'$eq': current_user['id']}}
	else:
		query_data = {'doctor_id': {'$eq': current_user['id']}}
	response = cassandra_request('GET', appointments_url, {}, {'where':json.dumps(query_data)})
	upcoming_apmts = []
	archived_apmts = []
	if current_user['type'] == 'patient':
		for index, v in enumerate(response['data']):
			response['data'][index]['start_time_data'] = (datetime.fromtimestamp(response['data'][index]['start_time']['epochSecond']) - timedelta(hours=5, minutes=30)).strftime('%a %d %b\'%y - %H:%M%p')
			response['data'][index]['end_time_data'] = (datetime.fromtimestamp(response['data'][index]['end_time']['epochSecond']) - timedelta(hours=5, minutes=30)).strftime('%a %d %b\'%y - %H:%M%p')
			response['data'][index]['doctor_name'] = cassandra_request('GET', "/api/rest/v2/keyspaces/healthapp_keyspace/users/" + response['data'][index]['doctor_id'])['data'][0]['name']
			if (datetime.fromtimestamp(response['data'][index]['start_time']['epochSecond']) - timedelta(hours=5, minutes=30)) > datetime.now():
				upcoming_apmts.append(response['data'][index])
			else:
				archived_apmts.append(response['data'][index])
	else:
		for index, v in enumerate(response['data']):
			response['data'][index]['start_time_data'] = (datetime.fromtimestamp(response['data'][index]['start_time']['epochSecond']) - timedelta(hours=5, minutes=30)).strftime('%a %d %b\'%y - %H:%M%p')
			response['data'][index]['end_time_data'] = (datetime.fromtimestamp(response['data'][index]['end_time']['epochSecond']) - timedelta(hours=5, minutes=30)).strftime('%a %d %b\'%y - %H:%M%p')
			response['data'][index]['patient_name'] = cassandra_request('GET', "/api/rest/v2/keyspaces/healthapp_keyspace/users/" + response['data'][index]['patient_id'])['data'][0]['name']
			if (datetime.fromtimestamp(response['data'][index]['start_time']['epochSecond']) - timedelta(hours=5, minutes=30)) > datetime.now():
				upcoming_apmts.append(response['data'][index])
			else:
				archived_apmts.append(response['data'][index])
	return render_template('appointments.html', current_user=current_user, view='appointments', data=response['data'], upcoming_apmts=upcoming_apmts, archived_apmts=archived_apmts)


@app.route('/ui/add_medicine', methods=['POST'])
def ui_add_medicine():
	current_user = check_auth(session)
	medcine_data = str(request.get_data().decode('utf-8')).strip().replace('\n', '').replace(',', '').replace('%2F','-').replace('%3A',':').replace('+',' ')
	intake_daytime = []
	daytime_data = medcine_data.split('intake_day_time%5B%5D=')
	for index,daytime_val in enumerate(daytime_data):
		if index == 0:
			continue
		intake_daytime.append(daytime_val.split('&')[0])

	name = medcine_data.split('name=')[1].split('&')[0]
	patient_id = medcine_data.split('patient_id=')[1].split('&')[0]
	quantity = medcine_data.split('quantity=')[1].split('&')[0]
	doctor_id = session['user']

	request_data = {
		'id': str(uuid.uuid1()),
		'name': name,
		'patient_id': patient_id,
		'doctor_id': doctor_id,
		'quantity': quantity,
		'intake_day_time': intake_daytime

	}
	medicines_url = "/api/rest/v2/keyspaces/healthapp_keyspace/medicines"
	response = cassandra_request('POST', medicines_url, request_data)
	if 'id' in response:
		return {'success': 'true'}
	else:
		return {'success': 'false'}


@app.route('/ui/medicines', methods=['GET'])
def ui_medicines():
	current_user = check_auth(session)
	medicines_url = "/api/rest/v2/keyspaces/healthapp_keyspace/medicines"
	query_data = {'patient_id': {'$eq': session['user']}}
	response = cassandra_request('GET', medicines_url, {}, {'where':json.dumps(query_data)})
	for index, value in enumerate(response['data']):
		response['data'][index]['doctor_name'] = cassandra_request('GET', "/api/rest/v2/keyspaces/healthapp_keyspace/users/" + response['data'][index]['doctor_id'])['data'][0]['name']
		response['data'][index]['intake_time'] = response['data'][index]['intake_day_time'][0].split('-')[1]
		response['data'][index]['intake_day_time_str'] = ""
		for ele in response['data'][index]['intake_day_time']:
			response['data'][index]['intake_day_time_str'] += ele
	return render_template('medicines.html', current_user=current_user, view='medicines', data=response['data'])


if __name__ == "__main__":
    app.run(port=5000,debug=True)
