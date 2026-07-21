from flask import Flask,url_for,request,redirect,render_template,session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime,timezone,date
from werkzeug.security import generate_password_hash,check_password_hash
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from functools import wraps
import os
PASS_MARK = 50

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
    program_id=db.Column(db.String(255), db.ForeignKey('program.id'))
class courses(db.Model):
    code=db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(200))   
    capacity = db.Column(db.Integer, nullable=True)
class registered(db.Model):
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), primary_key=True)
    course_code = db.Column(db.Integer, db.ForeignKey('courses.code'), primary_key=True)
    grade = db.Column(db.Integer, nullable=True)
    
class exams(db.Model):
    exam_id=db.Column(db.Integer,primary_key=True)
    course_code = db.Column(db.Integer, db.ForeignKey('courses.code'),nullable=False)
    date=db.Column(db.Date,nullable=False)
    name = db.Column(db.String(200))
    weight=db.Column(db.Integer,nullable=False)
class assignments(db.Model):
    assignment_id=db.Column(db.Integer,primary_key=True)
    course_code = db.Column(db.Integer, db.ForeignKey('courses.code'),nullable=False)
    name = db.Column(db.String(200))
    date = db.Column(db.Date, nullable=False)
    weight=db.Column(db.Integer,nullable=False)
class program(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))

class program_courses(db.Model):
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), primary_key=True)
    course_code = db.Column(db.Integer, db.ForeignKey('courses.code'), primary_key=True)

class exam_grades(db.Model):
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.exam_id'), primary_key=True)
    grade = db.Column(db.Integer)

class assignment_grades(db.Model):
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.assignment_id'), primary_key=True)
    grade = db.Column(db.Integer)
class prerequisites(db.Model):
    course_code = db.Column(db.Integer, db.ForeignKey('courses.code'), primary_key=True)
    required_course = db.Column(db.Integer, db.ForeignKey('courses.code'), primary_key=True)
    
def weight_ok(coursecode, new_weight):
    total = 0
    for e in exams.query.filter_by(course_code=coursecode).all():
        total += e.weight
    for a in assignments.query.filter_by(course_code=coursecode).all():
        total += a.weight
    return total + int(new_weight) <= 100

def in_program(s_id, coursecode):
    me = student.query.get(s_id)
    return program_courses.query.filter_by(program_id=me.program_id, course_code=coursecode).first() is not None

def already_registered(s_id, coursecode):
    return registered.query.filter_by(student_id=s_id, course_code=coursecode).first() is not None

def has_capacity(coursecode):
    course = courses.query.get(coursecode)
    if course.capacity is None:
        return True
    return registered.query.filter_by(course_code=coursecode).count() < course.capacity
def compute_course_results(s_id,coursecode):
    course_exams=exams.query.filter_by(course_code=coursecode).all()
    course_assignments=assignments.query.filter_by(course_code=coursecode).all()
    exam_grade_map={e.exam_id:e.grade for e in exam_grades.query.filter_by(student_id=s_id).all()}
    assignment_grade_map={a.assignment_id:a.grade for a in assignment_grades.query.filter_by(student_id=s_id).all()}
    grades=[]
    for e in course_exams:
        g=exam_grade_map.get(e.exam_id)
        if g is None:
            return
        grades.append(g)
    for a in course_assignments:
        g=assignment_grade_map.get(a.assignment_id)
        if g is None:
            return
        grades.append(g)
    if not grades:
        return
    result=sum(grades)/len(grades)
    row=registered.query.filter_by(student_id=s_id,course_code=coursecode).first()
    if row:
        row.grade=result
    
def meets_prereqs(s_id,coursecode):
    required_courses=prerequisites.query.filter_by(course_code=coursecode).all()
    for r in required_courses:
        a=r.required_course
        k=registered.query.filter_by(student_id=s_id,course_code=a).first()
        if k is None or k.grade is None or k.grade < PASS_MARK:
            return False
    return True        
def password_ok(pw):
    if len(pw) < 8:
        return False
    if not any(c.isupper() for c in pw):
        return False
    if not any(c.isdigit() for c in pw):
        return False
    return True

@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('student_id'):
        return redirect(url_for('options'))
    if session.get('is_staff'):
        return redirect(url_for('staff_entry'))
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
    return render_template('enter.html')

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
    programs=program.query.all()
    return render_template('newstudentpage.html',programs=programs)

@app.route("/newstudent",methods=['GET','POST'])
def register():
    if request.method=='POST':
        student_fname = request.form.get('fname','').strip()
        student_lname = request.form.get('lname','').strip()
        student_email = request.form.get('email','').strip().lower()
        student_program=request.form.get('program_id','')
        password = request.form.get('password','')
        if not password_ok(password):
            return render_template('newstudentpage.html',error='password must be 8+ characters with an uppercase letter and a number',programs=program.query.all())
        
        
        if not student_fname or not student_email or not password or not student_program:
            return render_template('newstudentpage.html', error='all fields required', programs=program.query.all())
        
        student_pass=generate_password_hash(password)
        new_student=student(fname=student_fname,lname=student_lname,email=student_email,password_hash=student_pass,program_id=student_program)
        try:
            db.session.add(new_student)
            db.session.commit()
            return redirect(url_for('success',new_id=new_student.id))
        except IntegrityError:
            db.session.rollback()
            return render_template('newstudentpage.html', error='email already registered', programs=program.query.all())
        except:
            db.session.rollback()
            return 'error adding student'
    return render_template('newstudentpage.html', programs=program.query.all())



@app.route('/success')
def success():
    new_id=request.args.get('new_id')
    return render_template('success.html',new_id=new_id)

@app.route('/staff_entry',methods=['GET','POST'])
@staff_required
def staff_entry():
    return render_template('staff_entry.html')

@app.route('/backdoor')
@staff_required
def backdoor():
    added=request.args.get('added')
    programs=program.query.all()
    all_courses = courses.query.all()
    return render_template('backdoor.html',added=added,programs=programs,courses=all_courses)

@app.route('/gradingpage', methods=['GET',"POST"])
@staff_required
def gradingpage():
    all_courses=courses.query.all()
    chosen=request.values.get('course_code')
    roster=None
    items_exams=None
    items_assignments=None
    graded_exam_ids=set()          
    graded_assignment_ids=set() 
    all_grades = {}
    if chosen:
        student_ids=[r.student_id for r in registered.query.filter_by(course_code=chosen).all()]
        roster=student.query.filter(student.id.in_(student_ids)).all()
        items_exams=exams.query.filter_by(course_code=chosen).all()
        items_assignments=assignments.query.filter_by(course_code=chosen).all()
        for e in items_exams:
            all_grades[f'exam:{e.exam_id}'] = {
                g.student_id: g.grade
                for g in exam_grades.query.filter_by(exam_id=e.exam_id).all()
            }
        for a in items_assignments:
            all_grades[f'assignment:{a.assignment_id}'] = {
                g.student_id: g.grade
                for g in assignment_grades.query.filter_by(assignment_id=a.assignment_id).all()
            }

        exam_ids = [e.exam_id for e in items_exams]
        assignment_ids = [a.assignment_id for a in items_assignments]
        graded_exam_ids = {g.exam_id for g in exam_grades.query.filter(exam_grades.exam_id.in_(exam_ids)).all()}
        graded_assignment_ids = {g.assignment_id for g in assignment_grades.query.filter(assignment_grades.assignment_id.in_(assignment_ids)).all()}
    return render_template('gradingpage.html', courses=all_courses, chosen=chosen,roster=roster, items_exams=items_exams, items_assignments=items_assignments,graded_exam_ids=graded_exam_ids,graded_assignment_ids=graded_assignment_ids,all_grades=all_grades)
@app.route('/gradeitem',methods=['POST'])
@staff_required
def grade_item():
    item=request.form.get('item','')
    if ':' not in item:
        return 'invalid item', 400
    kind,item_id=item.split(':')
    if kind == 'exam':
        course_code = exams.query.get(item_id).course_code
    else:
        course_code = assignments.query.get(item_id).course_code
    for key,value in request.form.items():
        if key.startswith('grade_') and value:
            s_id=int(key[6:])
            if kind== 'exam':
                record=exam_grades.query.filter_by(exam_id=item_id,student_id=s_id).first()
                if record:
                    record.grade=value
                else:
                    new_record=exam_grades(student_id=s_id,exam_id=item_id,grade=value)
                    db.session.add(new_record)
            elif kind=='assignment':
                record=assignment_grades.query.filter_by(assignment_id=item_id,student_id=s_id).first()
                if record:
                    record.grade=value
                else:
                    new_record=assignment_grades(student_id=s_id,assignment_id=item_id,grade=value)
                    db.session.add(new_record)
    db.session.flush()
    for key, value in request.form.items():
        if key.startswith('grade_') and value:
            s_id = int(key[6:])
            compute_course_results(s_id,course_code)
    try:
        db.session.commit()
        return redirect(url_for('gradingpage'))
    except Exception:
        db.session.rollback()
        return 'error saving grades'




@app.route('/addcourse',methods=['GET','POST'])
@staff_required
def addcourse():

    if request.method=='POST':
        program_id=request.form.get('program_id','')
        if not program.query.get(program_id):
            return render_template('backdoor.html', error='invalid program',programs=program.query.all())
        course_id=request.form['coursecode']
        course_name=request.form['coursename']
        capacity=request.form.get('capacity') or None

        course_program=program_courses(program_id=program_id,course_code=course_id)
        addedcourse=courses(code=course_id,name=course_name,capacity=capacity)
        try:
            db.session.add(addedcourse)
            db.session.add(course_program)
            db.session.commit()
            return redirect(url_for('backdoor', added='course'))
        except  Exception:
            db.session.rollback()
            return render_template('backdoor.html', error='error adding course',programs=program.query.all(),courses=courses.query.all())

    return render_template('backdoor.html',programs=program.query.all(),courses=courses.query.all())



@app.route('/addassignment',methods=['GET','POST'])
@staff_required
def addassignment():
    
    if request.method=='POST':
        course_id=request.form['coursecode']
        assignment_name=request.form['name']
        date=request.form['date']
        weight=request.form['weight']
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        newassignment=assignments(course_code=course_id,date=date_obj,name=assignment_name,weight=weight)
        if not courses.query.get(course_id):
            return render_template('backdoor.html',error='invalid course',programs=program.query.all(),courses=courses.query.all())
        if not weight_ok(course_id, weight):
            return render_template('backdoor.html', error='weights would exceed 100 for this course',programs=program.query.all(), courses=courses.query.all())
        
        try:
            db.session.add(newassignment)
            db.session.commit()
            return redirect(url_for('backdoor', added='assignment'))
        except Exception:
            db.session.rollback()
            return 'error'
    return render_template('backdoor.html',programs=program.query.all(),courses=courses.query.all())

@app.route('/addexam',methods=['GET','POST'])
@staff_required
def addexam():
    if request.method=='POST':
        course_id=request.form['coursecode']
        exam_name=request.form['name']
        date=request.form['date']
        weight=request.form['weight']
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        newexam=exams(course_code=course_id,name=exam_name,date=date_obj,weight=weight)

        if not courses.query.get(course_id):
            return render_template('backdoor.html',error='invalid course',programs=program.query.all(),courses=courses.query.all())
        if not weight_ok(course_id, weight):
            return render_template('backdoor.html', error='weights would exceed 100 for this course',programs=program.query.all(), courses=courses.query.all())
        try:
            db.session.add(newexam)
            db.session.commit()
            return redirect(url_for('backdoor', added='exam'))
        except Exception:
            db.session.rollback()
            return 'error'
    return render_template('backdoor.html',programs=program.query.all(),courses=courses.query.all())


@app.route('/addprogram',methods=['GET','POST'])
def addprogram():
    if request.method=='POST':
        name=request.form['name']
        
        new=program(name=name)
        try:
            db.session.add(new)
            db.session.commit()
            return redirect(url_for('backdoor',added='program'))
        except Exception:
            return 'error'
    return render_template('backdoor.html',programs=program.query.all(),courses=courses.query.all())

@app.route('/addprereq', methods=['POST'])
@staff_required
def addprereq():
    course_code = request.form.get('course_code','')
    required_course = request.form.get('required_course','')
    if course_code == required_course:
        return render_template('backdoor.html', error="a course can't require itself", programs=program.query.all(), courses=courses.query.all())
    try:
        db.session.add(prerequisites(course_code=course_code, required_course=required_course))
        db.session.commit()
        return redirect(url_for('backdoor', added='prereq'))
    except Exception:
        db.session.rollback()
        return render_template('backdoor.html', error='error adding prerequisite', programs=program.query.all(), courses=courses.query.all())
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
        all_courses=courses.query.join(program_courses).filter(program_courses.program_id == me.program_id).all()

        my_reg = registered.query.filter_by(student_id=s_id).all()
        registered_codes = [r.course_code for r in my_reg if r.grade is None]   
        completed_codes  = [r.course_code for r in my_reg if r.grade is not None] 
        allowed = [c for c in all_courses if c.code not in completed_codes and meets_prereqs(s_id, c.code)]
        return render_template('client.html',courses=allowed,s_id=s_id,registered_codes=registered_codes)
    except:
        return 'error'
@app.route('/mycourses')
@student_required
def my_courses():
    s_id = session.get('student_id')
    rows = registered.query.filter_by(student_id=s_id).all()
    course_lookup = {c.code: c.name for c in courses.query.all()}
    in_progress = [{'course': course_lookup[r.course_code]} for r in rows if r.grade is None]
    completed   = [{'course': course_lookup[r.course_code], 'grade': r.grade,'passed': r.grade >= PASS_MARK} for r in rows if r.grade is not None]
    return render_template('mycourses.html', in_progress=in_progress, completed=completed)

@app.route('/dashboard')
@student_required
def dashboard():
    s_id=session.get('student_id')
    course_codes=[r.course_code for r in registered.query.filter_by(student_id=s_id).all()]
    student_exams= exams.query.filter(exams.course_code.in_(course_codes)).all()
    student_assignments=assignments.query.filter(assignments.course_code.in_(course_codes)).all()
    course_lookup = {c.code: c.name for c in courses.query.filter(courses.code.in_(course_codes)).all()}
    exam_grade_lookup = {g.exam_id: g.grade for g in exam_grades.query.filter_by(student_id=s_id).all()}
    assign_grade_lookup = {g.assignment_id: g.grade for g in assignment_grades.query.filter_by(student_id=s_id).all()}


    all_items=[{'type':'exam','name':e.name,'date':e.date,'grade':exam_grade_lookup.get(e.exam_id),'course':course_lookup[e.course_code]} for e in student_exams]
    all_items+=[{'type':'assignment','name':e.name,'date':e.date,'grade':assign_grade_lookup.get(e.assignment_id),'course':course_lookup[e.course_code]} for e in student_assignments]
    all_items.sort(key= lambda x: x['date'])


    today = date.today()

    graded_exams = [i for i in all_items if i['type']=='exam' and i['grade'] is not None]
    graded_assignments = [i for i in all_items if i['type']=='assignment' and i['grade'] is not None]

    upcoming_exams = [i for i in all_items if i['type']=='exam' and i['grade'] is None and i['date'] >= today]
    upcoming_assignments = [i for i in all_items if i['type']=='assignment' and i['grade'] is None and i['date'] >= today]

    awaiting_exams = [i for i in all_items if i['type']=='exam' and i['grade'] is None and i['date'] < today]
    awaiting_assignments = [i for i in all_items if i['type']=='assignment' and i['grade'] is None and i['date'] < today]
    return render_template('dashboard.html',upcoming_exams=upcoming_exams,upcoming_assignments=upcoming_assignments,graded_assignments=graded_assignments,graded_exams=graded_exams,s_id=s_id,awaiting_exams=awaiting_exams,awaiting_assignments=awaiting_assignments)

@app.route('/registercourse/<int:coursecode>',methods=['POST'])
@student_required
def courseregister(coursecode):
    s_id=session.get('student_id')
    if not in_program(s_id,coursecode):
        return 'not in ur program', 403
    if already_registered(s_id,coursecode):    
        return 'already registered'
    if not has_capacity(coursecode):
        return 'course full',403
    if not meets_prereqs(s_id,coursecode):
        return 'prerequisites not met', 403
    new_register=registered(student_id=s_id,course_code=coursecode)
    try:
        db.session.add(new_register)
        db.session.commit()
        return 'success'
    except Exception as e:
        print(e)
        return 'error'
@app.route('/results')
@student_required
def results():
    s_id = session.get('student_id')
    rows = registered.query.filter_by(student_id=s_id).all()
    course_lookup = {c.code: c.name for c in courses.query.all()}
    in_progress = [{'course': course_lookup[r.course_code]} for r in rows if r.grade is None]
    results = [{'course': course_lookup[r.course_code], 'grade': r.grade, 'passed': r.grade >= PASS_MARK} for r in rows if r.grade is not None]
    return render_template('results.html', results=results,in_progress=in_progress)


@app.route('/staff-login',methods=['GET','POST'])
def staff_login():
    if session.get('is_staff'):
        return redirect(url_for('staff_entry'))
    if request.method=='POST':    
        entered=request.form['password']
        if check_password_hash(STAFF_PASSWORD_HASH,entered):
            session['is_staff']=True
            return redirect(url_for('staff_entry'))
        else:
            return render_template('staff-login.html', error='wrong password')
    return render_template('staff-login.html')

@app.route('/profile')
@student_required
def profile():
    s_id = session.get('student_id')
    me = student.query.get(s_id)
    program_name = program.query.get(me.program_id).name if me.program_id else None
    return render_template('profile.html', student=me, program_name=program_name)

@app.route('/coursesoverview')
@staff_required
def courses_overview():
    all_courses = courses.query.all()
    summary = []
    for c in all_courses:
        total = (sum(e.weight for e in exams.query.filter_by(course_code=c.code).all())+ sum(a.weight for a in assignments.query.filter_by(course_code=c.code).all()))
        summary.append({'course': c.name, 'code': c.code,'total_weight': total, 'complete': total == 100})
    return render_template('coursesoverview.html', summary=summary)

@app.route('/coursedetail/<int:code>')
@staff_required
def course_detail(code):
    course = courses.query.get(code)
    if not course:
        return 'no such course', 404
    c_exams = exams.query.filter_by(course_code=code).all()
    c_assignments = assignments.query.filter_by(course_code=code).all()
    total = sum(e.weight for e in c_exams) + sum(a.weight for a in c_assignments)
    return render_template('coursedetail.html', course=course,exams=c_exams, assignments=c_assignments,total_weight=total, complete=(total == 100))



if __name__=="__main__":

    with app.app_context():
        db.create_all()
    app.run(debug=True)













