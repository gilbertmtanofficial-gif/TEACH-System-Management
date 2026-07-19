from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import random
import csv
import pandas as pd
from io import StringIO

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('TEACH_SECRET_KEY', 'dev-secret-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///classroom.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

#Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='teacher')
    def set_password(self, plain_password): self.password_hash = generate_password_hash(plain_password)
    def check_password(self, plain_password): return check_password_hash(self.password_hash, plain_password)

class Classroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    students = db.relationship('Student', backref='classroom', lazy=True, cascade="all, delete-orphan")

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    points = db.Column(db.Integer, default=0)
    class_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=False)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    is_archived = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

#Auth Helpers
def is_authorized(): return 'user_id' in session

#ROUTES
@app.route('/')
def home():
    if not is_authorized(): return redirect(url_for('login_view'))
    u_id = session['user_id']
    
    selected_class_id = request.args.get('class_id')
    all_classrooms = Classroom.query.filter_by(user_id=u_id).order_by(Classroom.name).all()
    active_docs = Document.query.filter_by(user_id=u_id, is_archived=False).all()
    
    top_students = []
    if selected_class_id:
        cls = Classroom.query.filter_by(id=selected_class_id, user_id=u_id).first()
        if cls:
            top_students = Student.query.filter_by(class_id=selected_class_id).order_by(Student.points.desc()).limit(5).all()

    return render_template('index.html', classrooms=all_classrooms, selected_class_id=selected_class_id, top_students=top_students, documents=active_docs)

@app.route('/login', methods=['GET', 'POST'])
def login_view():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            session['user_id'], session['username'] = user.id, user.username
            return redirect(url_for('home'))
        flash('Invalid Credentials', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(username=request.form.get('username')).first():
            flash('Taken', 'error'); return redirect(url_for('register'))
        u = User(username=request.form.get('username'))
        u.set_password(request.form.get('password'))
        db.session.add(u); db.session.commit(); return redirect(url_for('login_view'))
    return render_template('register.html')

@app.route('/logout')
def logout_view():
    session.clear(); return redirect(url_for('login_view'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if not is_authorized(): return redirect(url_for('login_view'))
    current_u_id = session['user_id']

    if request.method == 'POST' and 'file' in request.files:
        file = request.files.get('file')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_doc = Document(filename=filename, user_id=current_u_id)
            db.session.add(new_doc)
            db.session.commit()
            flash('File uploaded successfully!', 'success')
            return redirect(url_for('settings'))
    active_docs = Document.query.filter_by(user_id=current_u_id, is_archived=False).all()
    archived_docs = Document.query.filter_by(user_id=current_u_id, is_archived=True).all()
    
    return render_template('settings.html', active_docs=active_docs, archived_docs=archived_docs)

@app.route('/lib_action', methods=['POST'])
def lib_action():
    if not is_authorized(): return jsonify({'status': 'unauthorized'}), 401
    data = request.get_json()
    action = data.get('action')
    
    for d_id in data.get('ids', []):
        doc = Document.query.get(d_id)
        if doc:
            if action == 'archive':
                doc.is_archived = True
            elif action == 'restore':
                doc.is_archived = False
            elif action == 'delete':
                try: os.remove(os.path.join(app.config['UPLOAD_FOLDER'], doc.filename))
                except: pass
                db.session.delete(doc)
    
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/manage_behavior/<int:class_id>')
def view_behavior_management(class_id):
    if not is_authorized(): return redirect(url_for('login_view'))
    c = Classroom.query.get_or_404(class_id); s = Student.query.filter_by(class_id=class_id).all()
    return render_template('behavior.html', classroom=c, students=s)

@app.route('/update_points/<int:student_id>/<string:action>/<int:value>')
def apply_individual_points(student_id, action, value):
    s = Student.query.get_or_404(student_id)
    if action == 'add': s.points += value
    else: s.points = max(0, s.points - value)
    db.session.commit(); return redirect(url_for('view_behavior_management', class_id=s.class_id))

@app.route('/global_update/<int:class_id>/<string:action>/<int:value>')
def apply_global_points(class_id, action, value):
    students = Student.query.filter_by(class_id=class_id).all()
    for s in students:
        if action == 'add': s.points += value
        else: s.points = max(0, s.points - value)
    db.session.commit(); return redirect(url_for('view_behavior_management', class_id=class_id))

@app.route('/roster')
def roster():
    if not is_authorized(): return redirect(url_for('login_view'))
    return render_template('roster.html', classrooms=Classroom.query.all())

@app.route('/add_class_record', methods=['POST'])
def add_class_record():
    if not is_authorized(): return redirect(url_for('login_view'))
    name = request.form.get('class_name')
    if name: 
        new_cls = Classroom(name=name, user_id=session['user_id'])
        db.session.add(new_cls)
        db.session.commit()
    return redirect(url_for('roster'))

@app.route('/add_student_record', methods=['POST'])
def add_student_record():
    db.session.add(Student(name=request.form.get('name'), gender=request.form.get('gender'), class_id=request.form.get('class_id')))
    db.session.commit(); return redirect(url_for('roster'))

@app.route('/move_student_record', methods=['POST'])
def move_student_record():
    if not is_authorized(): return redirect(url_for('login_view'))
    s_id = request.form.get('student_id')
    new_c_id = request.form.get('new_class_id')
    if s_id and new_c_id:
        student = Student.query.get(s_id)
        if student: student.class_id = new_c_id; db.session.commit()
    return redirect(url_for('roster'))

@app.route('/delete_student_record/<int:student_id>')
def delete_student_record(student_id):
    if not is_authorized(): return redirect(url_for('login_view'))
    s = Student.query.get_or_404(student_id); db.session.delete(s); db.session.commit()
    return redirect(url_for('roster'))

@app.route('/delete_class_record/<int:class_id>')
def delete_class_record(class_id):
    if not is_authorized(): return redirect(url_for('login_view'))
    target = Classroom.query.get_or_404(class_id); db.session.delete(target); db.session.commit()
    return redirect(url_for('roster'))

@app.route('/pick_name/<int:class_id>')
def pick_name(class_id):
    students_in_db = Student.query.filter_by(class_id=class_id).all()
    name = random.choice(students_in_db).name if students_in_db else 'None'
    return jsonify({'name': name})

@app.route('/export_roster/<class_id>')
def export_roster(class_id):
    if not is_authorized(): return redirect(url_for('login_view'))
    try:
        c_id = int(class_id)
        classroom = Classroom.query.get_or_404(c_id)
        students_query = Student.query.filter_by(class_id=c_id).all()

        # PANDAS Data Manipulation
        raw_data = [{'Student Name': s.name, 'Gender': s.gender, 'Current Points': s.points, 'Class': classroom.name} for s in students_query]
        df = pd.DataFrame(raw_data)
        df_sorted = df.sort_values(by='Student Name')
        csv_output = df_sorted.to_csv(index=False)

        output = make_response(csv_output)
        output.headers["Content-Disposition"] = f"attachment; filename=Roster_{classroom.name}.csv"
        output.headers["Content-type"] = "text/csv"
        return output
    except Exception as e:
        print(f"Pandas Error: {e}")
        return redirect(url_for('home'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)
