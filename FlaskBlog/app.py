from flask import Flask, render_template, flash, redirect, url_for, session, logging, request, jsonify
from flask_mysqldb import MySQL
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, PasswordField, HiddenField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from flask_wtf.csrf import CSRFProtect

import secrets
import time


#Pose Captcha modules
import label_image, run_image_test

app = Flask(__name__)
csrf = CSRFProtect(app)

#Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_DB'] = 'flaskblog'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
#init MySQL
mysql = MySQL(app)

#pose captcha verification token and pose
global pose_captcha_token
global pose_captcha_pose
pose_captcha_token = None
random_pose = None

#Function to delete all Images to ensure privacy and no exchange of personal data.
def delete_images():
	import glob, os
	for f in glob.glob("*.jpg"):
	    os.remove(f)

#Home Page
@app.route('/')
def home():
	return render_template('home.html')

#About Page
@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/test', methods=['POST'])
def test():
	start = time.time()
	app.logger.info('Entered /test')
	if 'webcam' in request.files:
		app.logger.info('webcam present.')
		image = request.files['webcam']
		app.logger.info(str(image))
		image.save(image.filename)

		#Logic for code to verify pose
		#pose_captcha/pose.jpg is generated
		# run_image_test.generate_pose_image(image.filename)
		pose_generated = run_image_test.generate_pose_image(image.filename)
		app.logger.info('pose_generated = ' + str(pose_generated))
		if pose_generated:
			global pose_captcha_token
			global random_pose
			# pose, score = label_image.get_label('smile.jpg')
			pose, score = label_image.get_label('pose.jpg')
			app.logger.info('random_pose = ' + random_pose + ', pose detected = ' + pose + ', score = '+ str(score))
			# if score >= 0.9 and pose == pose_captcha_token['pose']:
			if score >= 0.98 and pose == random_pose:
				pose_captcha_token = secrets.token_urlsafe(16)
				end = time.time()
				app.logger.info('\nOverall /test Time (1-image): {:.3f}s\n'.format(end-start))
				delete_images()				
				return jsonify({'image': image.filename, 'human' : 'True', 'token' : pose_captcha_token})

	end = time.time()
	delete_images()
	app.logger.info('\nOverall /test Time (1-image): {:.3f}s\n'.format(end-start))
	image = "fail"
	return jsonify({'image': image, 'human' : 'False', 'pose' : pose_generated})
	 
#Registration Form Class
class RegisterForm(FlaskForm):
	name = StringField('Name', [
		validators.Length(min=4,max=50), 
		validators.DataRequired(message='Enter Name')
		])
	username = StringField('Username', [
		validators.Length(min=4,max=30),
		validators.DataRequired(message='Enter Username')
		])
	email = StringField('Email',[
		validators.Email(message='Check Email'),
		validators.DataRequired(message='Enter Email')
		])
	password = PasswordField('Password',[
		validators.Length(min=6),
		validators.DataRequired(message='Enter Password'),
		])
	confirm = PasswordField('Confirm Password',[
		validators.Length(min=6),
		validators.DataRequired(message='Enter Confirm Password'),
		validators.EqualTo('password', message='Passwords do not match')
		])
	hidden = HiddenField('*Confirm you are a human with Pose Captcha for Registration.',[validators.DataRequired(message='Pose Captcha not verified.')])
	def validate_hidden(form, field):
		if field.data == "False":
			raise validators.ValidationError('Verification failed, please try again. Resubmit or refresh page.')
		if pose_captcha_token is None:
			raise validators.ValidationError('Pose Captcha not verified.')


#User Registration
@app.route('/register', methods=['GET','POST'])
def register():
	global pose_captcha_token
	global random_pose

	random_pose = secrets.choice(open('retrained_labels.txt').read().splitlines())
	form = RegisterForm(request.form)
	token = form.hidden.data
	if token == "False" or token == "" or token is None or pose_captcha_token is None:
		human = False
	else:
		#Token Verification, independent of session.
		encrypted_secret_token = sha256_crypt.encrypt(token+app.secret_key)
		secret_token = pose_captcha_token+app.secret_key
		human = sha256_crypt.verify(secret_token, encrypted_secret_token)
		app.logger.info(human)
		if human is False:
			flash('Pose Captcha not verified or verification failed. Rogue data found or injected.', 'danger')
			pose_captcha_token = None

	#POST request handled only when form is validated and pose verification is valid, i.e. registration done by a human.
	if request.method == 'POST' and form.validate() and human:
		password = sha256_crypt.encrypt(str(form.password.data))

		#MySQL Cursor
		cur = mysql.connection.cursor()

		#Execute INSERT
		cur.execute("INSERT into users(name, username, email, password) VALUES(%s, %s, %s, %s)",
			(form.name.data,form.username.data,form.email.data,password))

		#Commit DB and close connection
		mysql.connection.commit()
		cur.close()

		flash("You are now Registered and ready to log in", "success")
		pose_captcha_token = None

		return redirect(url_for('login'))	

	app.logger.info(human)
	return render_template('register.html',form=form, human=human, pose=random_pose)

#Check if User is Logged in
def isLoggedIn(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash("Unauthorized, please Login.", "danger")
			return redirect(url_for('login'))
	return wrap

#User Login
@app.route('/login', methods=['GET','POST'])
def login():
	if request.method == 'POST':
		#Get Form Fields
		username = request.form['username']
		cur = mysql.connection.cursor()
		password = request.form['password']

		#Create Cursor

		#Execute SELECT
		result = cur.execute("SELECT * FROM users WHERE username = %s", [username])
		
		if result > 0:
			app.logger.info("SELECT executed with result")
			
			#Get Hash
			pwd = cur.fetchone()['password']

			#Verify Hash
			if sha256_crypt.verify(password, pwd):
				#Verification True
				session['logged_in'] = True
				session['username'] = username
				
				app.logger.info('PASSWORD MATCH')
				flash("Successful Login !","success")
				return redirect(url_for('dashboard'))
			else:
				#Verification False
				app.logger.info('PASSWORD NOT MATCHED')
				flash("Wrong Password!","danger")
		else:
			app.logger.info('NO USER MATCH')
			flash("INVALID USER","danger")
		
		#Close Connection
		cur.close()

	return render_template('login.html')

#Logout 
@app.route('/logout')
@isLoggedIn
def logout():
	session.clear()
	flash("You are now Logged out.", "success")
	return redirect(url_for('home'))

#Dashboard
@app.route('/dashboard')
@isLoggedIn
def dashboard():
	#MySQL Cursor
	cur = mysql.connection.cursor()

	#Execute SELECT
	result = cur.execute("SELECT * FROM articles WHERE author = %s",[session['username']])
	app.logger.info("ARTICLES PRESENT result = %d",result)

	#Get Articles
	articles = cur.fetchall()

	if articles: 
		app.logger.info("ARTICLES PRESENT")
		return render_template('dashboard.html', articles=articles)
	else:
		app.logger.info("NO ARTICLES")
		flash('No Articles written.','danger')
		return render_template('dashboard.html', articles=articles)
	
	#Close connection
	cur.close()

#Article Form Class
class ArticleForm(FlaskForm):
	title = StringField('Title', [
		validators.Length(min=1,max=200), 
		validators.DataRequired(message='Enter Title')
		])
	body = TextAreaField('Body', [
		validators.Length(min=30),
		validators.DataRequired(message='Enter Body')
		])

#Articles
@app.route('/articles')
def articles():
	#MySQL Cursor
	cur = mysql.connection.cursor()

	#Execute SELECT
	result = cur.execute("SELECT * FROM articles")
	app.logger.info("ARTICLES PRESENT result = %d",result)

	#Get Articles
	articles = cur.fetchall()

	if articles: 
		app.logger.info("ARTICLES PRESENT")
		return render_template('articles.html', articles=articles)
	else:
		app.logger.info("NO ARTICLES")
		flash('No Articles written.','danger')
		return render_template('articles.html', articles=articles)
	
	#Close connection
	cur.close()

#Single Article
@app.route('/article/<string:id>')
def article(id):
	#MySQL Cursor
	cur = mysql.connection.cursor()

	#Execute SELECT
	result = cur.execute("SELECT * FROM articles WHERE id=%s",[id])

	#Get Article
	article = cur.fetchone()

	if articles: 
		app.logger.info("ARTICLES PRESENT")
		return render_template('article.html', article=article)
	else:
		app.logger.info("NO ARTICLES")
		flash('No Articles written.','danger')
		return render_template('article.html', article=article)
	
	#Close connection
	cur.close()

#Add Article
@app.route('/add_article', methods=['GET','POST'])
@isLoggedIn
def add_article():
	form = ArticleForm(request.form,body="<p>&nbsp;</p>")
	if request.method == 'POST' and form.validate():
		title = form.title.data
		body = form.body.data

		#MySQL Cursor
		cur = mysql.connection.cursor()

		#Execute INSERT
		cur.execute("INSERT into articles(author, title, body) VALUES(%s, %s, %s)",
			(session['username'],title,body))

		#Commit DB and close connection
		mysql.connection.commit()
		cur.close()

		flash("Article created", "success")

		return redirect(url_for('dashboard'))	

	return render_template('add_article.html', form=form)

#Edit Article
@app.route('/edit_article/<string:id>', methods=['GET','POST'])
@isLoggedIn
def edit_article(id):
	#MySQL Cursor
	cur = mysql.connection.cursor()

	#Get article by id 
	result = cur.execute("SELECT * from articles WHERE id=%s AND author=%s", (id,session['username']))
	if result == 0:
		cur.close()
		flash("You are not authorized to edit that article.","danger")
		return redirect(url_for('dashboard'))

	article = cur.fetchone()

	#Form 
	form = ArticleForm(request.form)

	#Populate Form 
	form.title.data = article['title']
	form.body.data = article['body']

	if request.method == 'POST' and form.validate():
		title = request.form['title']
		body = request.form['body']

		#MySQL Cursor
		cur = mysql.connection.cursor()

		#Execute INSERT
		cur.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s and author=%s",
			(title,body,id,session['username']))

		#Commit DB and close connection
		mysql.connection.commit()
		cur.close()

		flash("Article Edited and Updated.", "success")

		return redirect(url_for('dashboard'))	

	return render_template('edit_article.html', form=form)

#Delete Article
@app.route('/delete_article/<string:id>', methods=['GET','POST'])
@isLoggedIn
def delete_article(id):
	#MySQL Cursor
	cur = mysql.connection.cursor()

	#Get article by id 
	result = cur.execute("SELECT * from articles WHERE id=%s AND author=%s", (id,session['username']))
	if result == 0:
		cur.close()
		flash("You are not authorized to delete that article.","danger")
		return redirect(url_for('dashboard'))	

	#Delete Article
	cur.execute("DELETE from articles WHERE id=%s AND author=%s", (id,session['username']))

	#Commit DB and close connection
	mysql.connection.commit()
	cur.close()

	flash('Article Deleted.', 'success')

	return redirect(url_for('dashboard'))

if __name__ == "__main__":	
	app.secret_key = secrets.token_urlsafe(16)
	app.run(debug=False)
