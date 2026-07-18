from flask import Flask,url_for,request,redirect,render_template,session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime,timezone
from werkzeug.security import generate_password_hash,check_password_hash
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from functools import wraps
import os

load_dotenv()
STAFF_PASSWORD_HASH = os.getenv('STAFF_PASSWORD_HASH')
app=Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///test.db'
db = SQLAlchemy(app)
class student(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    fname=db.Column(db.String(200))
    lname=db.Column(db.String(200))
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    program_id=db.Column(db.string(255), db.ForeignKey('program.id'))
class courses(db.Model):
    code=db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(200))   
class registered(db.Model):
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), primary_key=True)
    course_code = db.Column(db.Integer, db.ForeignKey('courses.code'), primary_key=True)
    
class exams(db.Model):
    exam_id=db.Column(db.Integer,primary_key=True)
    course_code = db.Column(db.Integer, db.ForeignKey('courses.code'),nullable=False)
    date=db.Column(db.Date,nullable=False)
    name = db.Column(db.String(200))
    grade=db.Column(db.Integer,nullable=True)
class assignments(db.Model):
    assignment_id=db.Column(db.Integer,primary_key=True)
    course_code = db.Column(db.Integer, db.ForeignKey('courses.code'),nullable=False)
    name = db.Column(db.String(200))
    date = db.Column(db.Date, nullable=False)
    grade=db.Column(db.Integer,nullable=True)
    
class program(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))

class program_courses(db.Model):
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), primary_key=True)
    course_code = db.Column(db.Integer, db.ForeignKey('courses.code'), primary_key=True)

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        found=student.query.filter_by(email=request.form['email']).first()
        if found and check_password_hash(found.password_hash,request.form['password']):
            session['student_id']=found.id
            return redirect(url_for('options'))
        return render_template('enter.html',error='invalid credentials')
    return render_template('enter.html')
        

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
        
@app.route('/')
def index():
    return render_template('frontpage.html')

def student_required(f):
    @wraps(f)
    def decorated(*args,**kwargs):
        if not session.get('student_id'):
            return redirect(url_for('login'))
        return f(*args,**kwargs)
    return decorated

def staff_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_staff'):
            return redirect(url_for('staff_login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/newstudentpage')
def newstudentpage():
    programs=programs.query.all()
    return render_template('newstudentpage.html',programs=programs)

@app.route("/newstudent",methods=['GET','POST'])
def register():
    if request.method=='POST':
        student_fname = request.form.get('fname','').strip()
        student_lname = request.form.get('lname','').strip()
        student_email = request.form.get('email','').strip().lower()
        student_program=request.form.get('program_id','')
        password = request.form.get('password','')
        if not student_fname or not student_email or not password or not student_program:
            return render_template('newstudentpage.html', error='all fields required')
        
        student_pass=generate_password_hash(password)
        new_student=student(fname=student_fname,lname=student_lname,email=student_email,password_hash=student_pass,program_id=student_program)
        try:
            db.session.add(new_student)
            db.session.commit()
            return redirect(url_for('success',new_id=new_student.id))
        except IntegrityError:
            db.session.rollback()
            return render_template('newstudentpage.html', error='email already registered')
        except:
            db.session.rollback()
            return 'error adding student'
    return render_template('newstudentpage.html')



@app.route('/success')
def success():
    new_id=request.args.get('new_id')
    return render_template('success.html',new_id=new_id)


@app.route('/backdoor')
@staff_required
def backdoor():
    added=request.args.get('added')
    programs=program.query.all()
    return render_template('backdoor.html',added=added,programs=programs)
   


@app.route('/addcourse',methods=['GET','POST'])
@staff_required
def addcourse():

    if request.method=='POST':
        program_id=request.form.get('program_id','')
        if not program.query.get(program_id):
            return render_template('backdoor.html', error='invalid program',programs=program.query.all())
        course_id=request.form['coursecode']
        course_name=request.form['coursename']

        course_program=program_courses(program_id=program_id,course_code=course_id)
        addedcourse=courses(code=course_id,name=course_name)
        try:
            db.session.add(course_program)
            db.session.add(addedcourse)
            db.session.commit()
            return redirect(url_for('backdoor', added='course'))
        except  Exception:
            db.session.rollback()
            return render_template('backdoor.html', error='error adding course', programs=program.query.all())

    return render_template('backdoor.html',programs=program.query.all())



@app.route('/addassignment',methods=['GET','POST'])
@staff_required
def addassignment():
    if request.method=='POST':
        course_id=request.form['coursecode']
        assignment_id=request.form['assignmentid']
        assignment_name=request.form['name']
        date=request.form['date']
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        newassignment=assignments(course_code=course_id,assignment_id=assignment_id,date=date_obj,name=assignment_name)
        try:
            db.session.add(newassignment)
            db.session.commit()
            return redirect(url_for('backdoor', added='assignment'))
        except:
            return 'error'
    return render_template('backdoor.html')

@app.route('/addexam',methods=['GET','POST'])
@staff_required
def addexam():
    if request.method=='POST':
        course_id=request.form['coursecode']
        exam_id=request.form['examid']
        exam_name=request.form['name']
        date=request.form['date']
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        newexam=exams(course_code=course_id,name=exam_name,exam_id=exam_id,date=date_obj)
        try:
            db.session.add(newexam)
            db.session.commit()
            return redirect(url_for('backdoor', added='exam'))
        except:
            return 'error'
    return render_template('backdoor.html')


@app.route('/options')
@student_required
def options():
    s_id=session.get('student_id')
    return render_template('options.html', s_id=s_id)


@app.route('/registering',methods=['GET'])
@student_required
def registering():
    s_id=session.get('student_id')
    try:
        me=student.query.get(s_id)
        allowed=courses.query.join(program_courses).filter(program_courses.program_id == me.program_id).all()
        registered_codes=[r.course_code for r in registered.query.filter_by(student_id=s_id).all()]
        return render_template('client.html',courses=allowed,s_id=s_id,registered_codes=registered_codes)
    except:
        return 'error'

@app.route('/dashboard')
@student_required
def dashboard():
    s_id=session.get('student_id')
    course_codes=[r.course_code for r in registered.query.filter_by(student_id=s_id).all()]
    student_exams= exams.query.filter(exams.course_code.in_(course_codes)).all()
    student_assignments=assignments.query.filter(assignments.course_code.in_(course_codes)).all()
    course_lookup = {c.code: c.name for c in courses.query.filter(courses.code.in_(course_codes)).all()}
    all_items=[{'type':'exam','name':e.name,'date':e.date,'grade':e.grade,'course':course_lookup[e.course_code]} for e in student_exams]
    all_items+=[{'type':'assignment','name':e.name,'date':e.date,'grade':e.grade,'course':course_lookup[e.course_code]} for e in student_assignments]
    all_items.sort(key= lambda x: x['date'])
    upcoming_exams=[i for i in all_items if i['type']=='exam' and  i['grade'] is None]
    upcoming_assignments=[i for i in all_items if i['type']=='assignment' and  i['grade'] is None]
    graded_exams=[i for i in all_items if i['type']=='exam' and  i['grade'] is not None]
    graded_assignments=[i for i in all_items if i['type']=='assignment' and i['grade'] is not None]
    return render_template('dashboard.html',upcoming_exams=upcoming_exams,upcoming_assignments=upcoming_assignments,graded_assignments=graded_assignments,graded_exams=graded_exams,s_id=s_id)

@app.route('/registercourse/<int:coursecode>',methods=['POST'])
@student_required
def courseregister(coursecode):
    s_id=session.get('student_id')
    me=student.query.get(s_id)
    allowed=program_courses.query.filter_by(program_id=me.program_id,course_code=coursecode).first()
    existing=registered.query.filter_by(student_id=s_id,course_code=coursecode).first()
    if not allowed:
        return 'not in ur program', 403
    if existing:    
        return 'already registered'
    new_register=registered(student_id=s_id,course_code=coursecode)
    try:
        db.session.add(new_register)
        db.session.commit()
        return 'success'
    except Exception as e:
        print(e)
        return 'error'
    

@app.route('/staff-login',methods=['GET','POST'])
def staff_login():
    if session.get('is_staff'):
        return redirect(url_for('backdoor'))
    if request.method=='POST':    
        entered=request.form['password']
        if check_password_hash(STAFF_PASSWORD_HASH,entered):
            session['is_staff']=True
            return redirect(url_for('backdoor'))
        else:
            return render_template('staff-login.html', error='wrong password')
    return render_template('staff-login.html')




if __name__=="__main__":

    with app.app_context():
        db.create_all()
    app.run(debug=True)













