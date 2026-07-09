from flask import Flask,url_for,request,redirect,render_template,session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime,timezone
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
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
    name=db.Column(db.String(200))
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
    grade=db.Column(db.Integer,nullable=True)
class assignments(db.Model):
    assignment_id=db.Column(db.Integer,primary_key=True)
    course_code = db.Column(db.Integer, db.ForeignKey('courses.code'),nullable=False)
    date = db.Column(db.Date, nullable=False)
    grade=db.Column(db.Integer,nullable=True)
@app.route('/',methods=['GET','POST'])
def index():
    success=False
    if request.method == 'POST':
        
    
        register=request.form['register']
        Course=request.form['course']
        if register=='course':
            new_task=courses(code=Course)
            success=True
        if register=='assignment':
            success=True
            task_date=request.form['deadline']
            task_content=request.form['content']
            new_task=assignments(assignment_id=task_content,course_code=Course,date=task_date)
        if register=='exam':
            success=True
            task_content=request.form['content']
            task_date=request.form['deadline']
            new_task=exams(exam_id=task_content,course_code=Course,date=task_date)
        if success :
            db.session.add(new_task)
            db.session.commit()
            return redirect('/')
        else:
            return 'there was an error'
    else:
        return render_template('frontpage.html')

def staff_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_staff'):
            return redirect(url_for('staff_login'))
        return f(*args, **kwargs)
    return decorated
@app.route('/newstudentpage')
def newstudentpage():
    return render_template('newstudentpage.html')

@app.route("/newstudent",methods=['GET','POST'])
def register():
    if request.method=='POST':
        
        student_name=request.form['name']
        new_student=student(name=student_name)
        try:
            db.session.add(new_student)
            db.session.commit()

            return redirect(url_for('success',new_id=new_student.id))
        except:
            return 'error adding student'
    return render_template('enter.html')



@app.route('/success')
def success():
    new_id=request.args.get('new_id')
    return render_template('success.html',new_id=new_id)


@app.route('/backdoor')
@staff_required
def backdoor():
    added=request.args.get('added')
    return render_template('backdoor.html',added=added)

@app.route('/entering',methods=['POST'])
def entering():
    if request.method=='POST':
        s_id=request.form['id']
        found=student.query.get(s_id)
        if found:    
            return redirect(url_for('registering',s_id=s_id))
        else:
            return redirect(url_for('enter_page',error='notfound'))
@app.route('/enter')
def enter_page():
    error=request.args.get('error')
    return render_template('enter.html',error=error)    


@app.route('/addcourse',methods=['GET','POST'])
@staff_required
def addcourse():

    if request.method=='POST':
        course_id=request.form['coursecode']
        course_name=request.form['coursename']

        addedcourse=courses(code=course_id,name=course_name)
        
        db.session.add(addedcourse)
        db.session.commit()
        return redirect(url_for('backdoor', added='course'))
        
    return render_template('backdoor.html')



@app.route('/addassignment',methods=['GET','POST'])
@staff_required
def addassignment():
    if request.method=='POST':
        course_id=request.form['coursecode']
        assignment_id=request.form['assignmentid']
        date=request.form['date']
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        newassignment=assignments(course_code=course_id,assignment_id=assignment_id,date=date_obj)
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
        date=request.form['date']
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        newexam=exams(course_code=course_id,exam_id=exam_id,date=date_obj)
        try:
            db.session.add(newexam)
            db.session.commit()
            return redirect(url_for('backdoor', added='exam'))
        except:
            return 'error'
    return render_template('backdoor.html')



@app.route('/registering/<int:s_id>',methods=['GET'])
def registering(s_id):
    try:
        all_courses=courses.query.all()
        registered_codes=[r.course_code for r in registered.query.filter_by(student_id=s_id).all()]
        return render_template('client.html',courses=all_courses,s_id=s_id,registered_codes=registered_codes)
    except:
        return 'error'



@app.route('/registercourse/<int:s_id>/<int:coursecode>',methods=['POST'])
def courseregister(s_id,coursecode):
    existing=registered.query.filter_by(student_id=s_id,course_code=coursecode).first()
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













