import os, sqlite3
from pathlib import Path
from functools import wraps
from datetime import date, datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "college.db"
UPLOAD_DIR = BASE / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf","png","jpg","jpeg","doc","docx","ppt","pptx","txt","mp4","webm","zip"}
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-before-deployment")
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

def db():
    conn=sqlite3.connect(DB_PATH)
    conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'student',
          student_no TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS courses(
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, code TEXT NOT NULL,
          description TEXT DEFAULT '', teacher_id INTEGER, semester TEXT DEFAULT 'Semester 1',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(teacher_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS enrollments(
          user_id INTEGER NOT NULL, course_id INTEGER NOT NULL, PRIMARY KEY(user_id,course_id),
          FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS resources(
          id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER NOT NULL, title TEXT NOT NULL,
          description TEXT DEFAULT '', filename TEXT, link TEXT, created_by INTEGER,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(course_id) REFERENCES courses(id),
          FOREIGN KEY(created_by) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS assignments(
          id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER NOT NULL, title TEXT NOT NULL,
          description TEXT DEFAULT '', due_date TEXT, created_by INTEGER,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(course_id) REFERENCES courses(id),
          FOREIGN KEY(created_by) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS submissions(
          id INTEGER PRIMARY KEY AUTOINCREMENT, assignment_id INTEGER NOT NULL, student_id INTEGER NOT NULL,
          text_answer TEXT DEFAULT '', filename TEXT, submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
          marks REAL, feedback TEXT, UNIQUE(assignment_id,student_id),
          FOREIGN KEY(assignment_id) REFERENCES assignments(id), FOREIGN KEY(student_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS attendance(
          id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, course_id INTEGER NOT NULL,
          class_date TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('Present','Absent','Late')),
          marked_by INTEGER, UNIQUE(student_id,course_id,class_date),
          FOREIGN KEY(student_id) REFERENCES users(id), FOREIGN KEY(course_id) REFERENCES courses(id)
        );
        CREATE TABLE IF NOT EXISTS exams(
          id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER NOT NULL, title TEXT NOT NULL,
          exam_date TEXT, total_marks REAL DEFAULT 100, description TEXT DEFAULT '',
          FOREIGN KEY(course_id) REFERENCES courses(id)
        );
        CREATE TABLE IF NOT EXISTS results(
          id INTEGER PRIMARY KEY AUTOINCREMENT, exam_id INTEGER NOT NULL, student_id INTEGER NOT NULL,
          marks REAL NOT NULL DEFAULT 0, feedback TEXT DEFAULT '',
          UNIQUE(exam_id,student_id), FOREIGN KEY(exam_id) REFERENCES exams(id),
          FOREIGN KEY(student_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS announcements(
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, message TEXT NOT NULL,
          created_by INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(created_by) REFERENCES users(id)
        );
        """)
        if not c.execute("SELECT id FROM users WHERE email=?",("admin@raisonilearn.local",)).fetchone():
            c.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                      ("College Administrator","admin@raisonilearn.local",generate_password_hash("ChangeMe123!"),"admin"))
        if not c.execute("SELECT id FROM users WHERE email=?",("teacher@raisonilearn.local",)).fetchone():
            c.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                      ("Demo Teacher","teacher@raisonilearn.local",generate_password_hash("Teacher123!"),"teacher"))
        if not c.execute("SELECT id FROM users WHERE email=?",("student@raisonilearn.local",)).fetchone():
            sid=c.execute("INSERT INTO users(name,email,password_hash,role,student_no) VALUES(?,?,?,?,?)",
                      ("Yogesh Nimbalkar","student@raisonilearn.local",generate_password_hash("Student123!"),"student","BCA-2026-001")).lastrowid
        else: sid=c.execute("SELECT id FROM users WHERE email=?",("student@raisonilearn.local",)).fetchone()["id"]
        tid=c.execute("SELECT id FROM users WHERE email=?",("teacher@raisonilearn.local",)).fetchone()["id"]
        if c.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0:
            seed=[
              ("Data Structures & Algorithms","BCA501","Learn arrays, linked lists, trees, graphs and algorithms.","BCA Semester 5"),
              ("Database Management System","BCA502","Relational databases, SQL, normalization and transactions.","BCA Semester 5"),
              ("Web Development","BCA503","Build responsive websites with HTML, CSS and JavaScript.","BCA Semester 5"),
              ("Operating System","BCA504","Processes, memory management, files and scheduling.","BCA Semester 5"),
              ("Computer Networks","BCA505","Networking concepts, protocols and network security.","BCA Semester 5"),
              ("Software Engineering","BCA506","Requirements, design, testing and software project practices.","BCA Semester 5")]
            for title,code,desc,sem in seed:
                cid=c.execute("INSERT INTO courses(title,code,description,teacher_id,semester) VALUES(?,?,?,?,?)",(title,code,desc,tid,sem)).lastrowid
                c.execute("INSERT OR IGNORE INTO enrollments(user_id,course_id) VALUES(?,?)",(sid,cid))
            ids=[r["id"] for r in c.execute("SELECT id FROM courses ORDER BY id").fetchall()]
            c.executemany("INSERT INTO assignments(course_id,title,description,due_date,created_by) VALUES(?,?,?,?,?)",[
                (ids[1],"DBMS Assignment 2","Write SQL queries and explain normalization.","2026-10-14",tid),
                (ids[2],"Web Development Project","Submit a responsive multi-page website.","2026-10-17",tid),
                (ids[0],"Data Structures Practical","Implement stack and queue operations.","2026-10-20",tid)])
            c.executemany("INSERT INTO exams(course_id,title,exam_date,total_marks,description) VALUES(?,?,?,?,?)",[
                (ids[1],"DBMS Mid-Term Exam","2026-10-20",50,"Chapters 1–4"),
                (ids[0],"Data Structures Quiz","2026-10-24",25,"Stacks, queues and linked lists")])
            c.execute("INSERT INTO announcements(title,message,created_by) VALUES(?,?,?)",
                      ("Welcome to Raisoni Learn","Demo portal is ready. Check your assignments and timetable regularly.",tid))
            for idx,cid in enumerate(ids[:4]):
                c.execute("INSERT INTO attendance(student_id,course_id,class_date,status,marked_by) VALUES(?,?,?,?,?)",
                          (sid,cid,"2026-10-09","Present" if idx<3 else "Absent",tid))

def current_user():
    if "user_id" not in session: return None
    with db() as c:
        return c.execute("SELECT id,name,email,role,student_no FROM users WHERE id=?",(session["user_id"],)).fetchone()

@app.context_processor
def inject_user():
    return {"current":current_user(), "today":date.today().isoformat()}

def login_required(fn):
    @wraps(fn)
    def wrapper(*args,**kwargs):
        if not current_user():
            flash("Please sign in to continue.","warning")
            return redirect(url_for("login"))
        return fn(*args,**kwargs)
    return wrapper

def roles(*allowed):
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args,**kwargs):
            if current_user()["role"] not in allowed:
                abort(403)
            return fn(*args,**kwargs)
        return wrapper
    return deco

def allowed_file(name):
    return "." in name and name.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    if not current_user():
        return render_template("index.html")
    return redirect(url_for("dashboard"))

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form.get("name","").strip()
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        if not name or not email or len(password)<8:
            flash("Enter your name and email. Password must be at least 8 characters.","error")
        else:
            try:
                with db() as c:
                    c.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'student')",
                              (name,email,generate_password_hash(password)))
                flash("Account created. You can sign in now.","success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That email is already registered.","error")
    return render_template("auth.html",mode="register")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        with db() as c: user=c.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
        if user and check_password_hash(user["password_hash"],password):
            session.clear(); session["user_id"]=user["id"]
            flash("Welcome back, "+user["name"].split()[0]+"!","success")
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.","error")
    return render_template("auth.html",mode="login")

@app.route("/logout")
def logout():
    session.clear(); flash("You have been signed out.","success"); return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    u=current_user()
    with db() as c:
        if u["role"]=="student":
            courses=c.execute("""SELECT c.*, (SELECT COUNT(*) FROM resources r WHERE r.course_id=c.id) resource_count
                FROM courses c JOIN enrollments e ON e.course_id=c.id WHERE e.user_id=? ORDER BY c.title""",(u["id"],)).fetchall()
            assignments=c.execute("""SELECT a.*,c.title course_title,s.id submission_id FROM assignments a
                JOIN courses c ON c.id=a.course_id JOIN enrollments e ON e.course_id=c.id AND e.user_id=?
                LEFT JOIN submissions s ON s.assignment_id=a.id AND s.student_id=? ORDER BY a.due_date LIMIT 5""",(u["id"],u["id"])).fetchall()
            exams=c.execute("""SELECT ex.*,c.title course_title FROM exams ex JOIN courses c ON c.id=ex.course_id
                JOIN enrollments e ON e.course_id=c.id WHERE e.user_id=? ORDER BY ex.exam_date LIMIT 4""",(u["id"],)).fetchall()
            total=c.execute("SELECT COUNT(*) FROM attendance WHERE student_id=?",(u["id"],)).fetchone()[0]
            present=c.execute("SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='Present'",(u["id"],)).fetchone()[0]
            attendance=round(present*100/total) if total else 0
        else:
            courses=c.execute("SELECT c.*,u.name teacher_name FROM courses c LEFT JOIN users u ON u.id=c.teacher_id ORDER BY c.title").fetchall()
            assignments=c.execute("SELECT a.*,c.title course_title,NULL submission_id FROM assignments a JOIN courses c ON c.id=a.course_id ORDER BY a.due_date LIMIT 5").fetchall()
            exams=c.execute("SELECT ex.*,c.title course_title FROM exams ex JOIN courses c ON c.id=ex.course_id ORDER BY ex.exam_date LIMIT 4").fetchall()
            attendance=0
        announcements=c.execute("SELECT a.*,u.name author FROM announcements a LEFT JOIN users u ON u.id=a.created_by ORDER BY a.created_at DESC LIMIT 4").fetchall()
    return render_template("dashboard.html",courses=courses,assignments=assignments,exams=exams,attendance=attendance,announcements=announcements)

@app.route("/courses")
@login_required
def courses():
    u=current_user()
    with db() as c:
        if u["role"]=="student":
            rows=c.execute("""SELECT c.*,u.name teacher_name,EXISTS(SELECT 1 FROM enrollments e WHERE e.course_id=c.id AND e.user_id=?) enrolled
                FROM courses c LEFT JOIN users u ON u.id=c.teacher_id ORDER BY c.title""",(u["id"],)).fetchall()
        else:
            rows=c.execute("SELECT c.*,u.name teacher_name,1 enrolled FROM courses c LEFT JOIN users u ON u.id=c.teacher_id ORDER BY c.title").fetchall()
    return render_template("courses.html",courses=rows)

@app.post("/courses/<int:course_id>/enroll")
@roles("student")
def enroll(course_id):
    with db() as c:
        if not c.execute("SELECT id FROM courses WHERE id=?",(course_id,)).fetchone(): abort(404)
        c.execute("INSERT OR IGNORE INTO enrollments(user_id,course_id) VALUES(?,?)",(current_user()["id"],course_id))
    flash("Course added to your classroom.","success"); return redirect(url_for("courses"))

@app.route("/course/<int:course_id>")
@login_required
def course_detail(course_id):
    u=current_user()
    with db() as c:
        course=c.execute("SELECT c.*,u.name teacher_name FROM courses c LEFT JOIN users u ON u.id=c.teacher_id WHERE c.id=?",(course_id,)).fetchone()
        if not course: abort(404)
        enrolled=c.execute("SELECT 1 FROM enrollments WHERE user_id=? AND course_id=?",(u["id"],course_id)).fetchone()
        if u["role"]=="student" and not enrolled: abort(403)
        resources=c.execute("SELECT * FROM resources WHERE course_id=? ORDER BY created_at DESC",(course_id,)).fetchall()
        assignments=c.execute("SELECT * FROM assignments WHERE course_id=? ORDER BY due_date",(course_id,)).fetchall()
    return render_template("course_detail.html",course=course,resources=resources,assignments=assignments)

@app.route("/assignments")
@login_required
def assignments():
    u=current_user()
    with db() as c:
        if u["role"]=="student":
            rows=c.execute("""SELECT a.*,c.title course_title,s.id submission_id,s.marks FROM assignments a
              JOIN courses c ON c.id=a.course_id JOIN enrollments e ON e.course_id=c.id AND e.user_id=?
              LEFT JOIN submissions s ON s.assignment_id=a.id AND s.student_id=? ORDER BY a.due_date""",(u["id"],u["id"])).fetchall()
        else:
            rows=c.execute("""SELECT a.*,c.title course_title,COUNT(s.id) submission_count FROM assignments a
              JOIN courses c ON c.id=a.course_id LEFT JOIN submissions s ON s.assignment_id=a.id
              GROUP BY a.id ORDER BY a.due_date""").fetchall()
        course_rows=c.execute("SELECT id,title FROM courses ORDER BY title").fetchall()
    return render_template("assignments.html",assignments=rows,courses=course_rows)

@app.post("/assignments/create")
@roles("admin","teacher")
def create_assignment():
    title=request.form.get("title","").strip(); cid=request.form.get("course_id",type=int)
    if not title or not cid: flash("Assignment title and course are required.","error")
    else:
        with db() as c: c.execute("INSERT INTO assignments(course_id,title,description,due_date,created_by) VALUES(?,?,?,?,?)",
          (cid,title,request.form.get("description","").strip(),request.form.get("due_date") or None,current_user()["id"]))
        flash("Assignment created.","success")
    return redirect(url_for("assignments"))

@app.post("/assignments/<int:aid>/submit")
@roles("student")
def submit_assignment(aid):
    u=current_user(); answer=request.form.get("text_answer","").strip(); f=request.files.get("file")
    filename=None
    if f and f.filename:
        if not allowed_file(f.filename): flash("Unsupported file type.","error"); return redirect(url_for("assignments"))
        filename=f"{u['id']}_{aid}_{secure_filename(f.filename)}"; f.save(UPLOAD_DIR/filename)
    with db() as c:
        a=c.execute("""SELECT a.id FROM assignments a JOIN enrollments e ON e.course_id=a.course_id
                    WHERE a.id=? AND e.user_id=?""",(aid,u["id"])).fetchone()
        if not a: abort(403)
        c.execute("""INSERT INTO submissions(assignment_id,student_id,text_answer,filename,submitted_at)
          VALUES(?,?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(assignment_id,student_id) DO UPDATE SET
          text_answer=excluded.text_answer,filename=COALESCE(excluded.filename,submissions.filename),submitted_at=CURRENT_TIMESTAMP""",
          (aid,u["id"],answer,filename))
    flash("Assignment submitted successfully.","success"); return redirect(url_for("assignments"))

@app.route("/exams")
@login_required
def exams():
    u=current_user()
    with db() as c:
        if u["role"]=="student":
            rows=c.execute("""SELECT ex.*,c.title course_title,r.marks FROM exams ex JOIN courses c ON c.id=ex.course_id
                JOIN enrollments e ON e.course_id=c.id AND e.user_id=? LEFT JOIN results r ON r.exam_id=ex.id AND r.student_id=?
                ORDER BY ex.exam_date""",(u["id"],u["id"])).fetchall()
        else:
            rows=c.execute("SELECT ex.*,c.title course_title FROM exams ex JOIN courses c ON c.id=ex.course_id ORDER BY ex.exam_date").fetchall()
        cr=c.execute("SELECT id,title FROM courses ORDER BY title").fetchall()
    return render_template("exams.html",exams=rows,courses=cr)

@app.post("/exams/create")
@roles("admin","teacher")
def create_exam():
    title=request.form.get("title","").strip(); cid=request.form.get("course_id",type=int)
    total=request.form.get("total_marks",type=float) or 100
    if not title or not cid: flash("Exam title and course are required.","error")
    else:
        with db() as c: c.execute("INSERT INTO exams(course_id,title,exam_date,total_marks,description) VALUES(?,?,?,?,?)",
          (cid,title,request.form.get("exam_date") or None,total,request.form.get("description","")))
        flash("Exam created.","success")
    return redirect(url_for("exams"))

@app.route("/attendance",methods=["GET","POST"])
@roles("admin","teacher")
def attendance():
    with db() as c:
        students=c.execute("SELECT id,name,student_no FROM users WHERE role='student' ORDER BY name").fetchall()
        courses=c.execute("SELECT id,title FROM courses ORDER BY title").fetchall()
        if request.method=="POST":
            cid=request.form.get("course_id",type=int); day=request.form.get("class_date") or date.today().isoformat()
            for s in students:
                status=request.form.get(f"status_{s['id']}")
                if status in ("Present","Absent","Late"):
                    c.execute("""INSERT INTO attendance(student_id,course_id,class_date,status,marked_by) VALUES(?,?,?,?,?)
                    ON CONFLICT(student_id,course_id,class_date) DO UPDATE SET status=excluded.status,marked_by=excluded.marked_by""",
                    (s["id"],cid,day,status,current_user()["id"]))
            flash("Attendance saved.","success"); return redirect(url_for("attendance"))
        records=c.execute("""SELECT a.class_date,a.status,u.name student_name,c.title course_title
          FROM attendance a JOIN users u ON u.id=a.student_id JOIN courses c ON c.id=a.course_id
          ORDER BY a.class_date DESC LIMIT 30""").fetchall()
    return render_template("attendance.html",students=students,courses=courses,records=records)

@app.route("/results",methods=["GET","POST"])
@roles("admin","teacher")
def results():
    with db() as c:
        if request.method=="POST":
            exam_id=request.form.get("exam_id",type=int); student_id=request.form.get("student_id",type=int)
            marks=request.form.get("marks",type=float)
            exam=c.execute("SELECT total_marks FROM exams WHERE id=?",(exam_id,)).fetchone()
            if not exam or marks is None or marks<0 or marks>exam["total_marks"]:
                flash("Check the exam and marks. Marks cannot exceed total marks.","error")
            else:
                c.execute("""INSERT INTO results(exam_id,student_id,marks,feedback) VALUES(?,?,?,?)
                    ON CONFLICT(exam_id,student_id) DO UPDATE SET marks=excluded.marks,feedback=excluded.feedback""",
                    (exam_id,student_id,marks,request.form.get("feedback","")))
                flash("Result saved.","success")
            return redirect(url_for("results"))
        exams=c.execute("SELECT ex.*,c.title course_title FROM exams ex JOIN courses c ON c.id=ex.course_id ORDER BY ex.exam_date").fetchall()
        students=c.execute("SELECT id,name FROM users WHERE role='student' ORDER BY name").fetchall()
        rows=c.execute("""SELECT r.*,u.name student_name,ex.title exam_title,ex.total_marks,c.title course_title
          FROM results r JOIN users u ON u.id=r.student_id JOIN exams ex ON ex.id=r.exam_id
          JOIN courses c ON c.id=ex.course_id ORDER BY ex.exam_date DESC""").fetchall()
    return render_template("results.html",exams=exams,students=students,results=rows)

@app.route("/resources",methods=["GET","POST"])
@login_required
def resources():
    u=current_user()
    if request.method=="POST":
        if u["role"] not in ("admin","teacher"): abort(403)
        title=request.form.get("title","").strip(); cid=request.form.get("course_id",type=int)
        f=request.files.get("file"); link=request.form.get("link","").strip(); filename=None
        if f and f.filename:
            if not allowed_file(f.filename): flash("Unsupported file type.","error"); return redirect(url_for("resources"))
            filename=f"{u['id']}_{int(datetime.now().timestamp())}_{secure_filename(f.filename)}"; f.save(UPLOAD_DIR/filename)
        if not title or not cid or (not filename and not link):
            flash("Provide a title, course, and either a file or URL.","error")
        else:
            with db() as c: c.execute("INSERT INTO resources(course_id,title,description,filename,link,created_by) VALUES(?,?,?,?,?,?)",
              (cid,title,request.form.get("description",""),filename,link or None,u["id"]))
            flash("Resource added.","success")
        return redirect(url_for("resources"))
    with db() as c:
        if u["role"]=="student":
            rows=c.execute("""SELECT r.*,c.title course_title FROM resources r JOIN courses c ON c.id=r.course_id
              JOIN enrollments e ON e.course_id=c.id AND e.user_id=? ORDER BY r.created_at DESC""",(u["id"],)).fetchall()
        else: rows=c.execute("SELECT r.*,c.title course_title FROM resources r JOIN courses c ON c.id=r.course_id ORDER BY r.created_at DESC").fetchall()
        courses=c.execute("SELECT id,title FROM courses ORDER BY title").fetchall()
    return render_template("resources.html",resources=rows,courses=courses)

@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    # Uploads are only available to signed-in users; production should also check course enrollment.
    return send_from_directory(UPLOAD_DIR,filename,as_attachment=True)

@app.route("/announcements",methods=["GET","POST"])
@login_required
def announcements():
    if request.method=="POST":
        if current_user()["role"] not in ("admin","teacher"): abort(403)
        title=request.form.get("title","").strip(); message=request.form.get("message","").strip()
        if title and message:
            with db() as c: c.execute("INSERT INTO announcements(title,message,created_by) VALUES(?,?,?)",(title,message,current_user()["id"]))
            flash("Announcement published.","success")
        else: flash("Title and message are required.","error")
        return redirect(url_for("announcements"))
    with db() as c: rows=c.execute("SELECT a.*,u.name author FROM announcements a LEFT JOIN users u ON u.id=a.created_by ORDER BY a.created_at DESC").fetchall()
    return render_template("announcements.html",announcements=rows)

@app.route("/admin",methods=["GET","POST"])
@roles("admin")
def admin():
    if request.method=="POST":
        action=request.form.get("action")
        if action=="role":
            uid=request.form.get("user_id",type=int); role=request.form.get("role")
            if role in ("student","teacher","admin") and uid!=current_user()["id"]:
                with db() as c: c.execute("UPDATE users SET role=? WHERE id=?",(role,uid))
                flash("User role updated.","success")
        elif action=="course":
            title=request.form.get("title","").strip(); code=request.form.get("code","").strip()
            teacher=request.form.get("teacher_id",type=int) or None
            if title and code:
                with db() as c: c.execute("INSERT INTO courses(title,code,description,teacher_id,semester) VALUES(?,?,?,?,?)",
                    (title,code,request.form.get("description",""),teacher,request.form.get("semester","Semester 1")))
                flash("Course created.","success")
            else: flash("Course title and code are required.","error")
        return redirect(url_for("admin"))
    with db() as c:
        users=c.execute("SELECT id,name,email,role,student_no,created_at FROM users ORDER BY created_at DESC").fetchall()
        courses=c.execute("SELECT c.*,u.name teacher_name FROM courses c LEFT JOIN users u ON u.id=c.teacher_id ORDER BY c.id DESC").fetchall()
        teachers=c.execute("SELECT id,name FROM users WHERE role IN ('teacher','admin') ORDER BY name").fetchall()
        stats={"users":c.execute("SELECT COUNT(*) FROM users").fetchone()[0],"courses":c.execute("SELECT COUNT(*) FROM courses").fetchone()[0],
        "assignments":c.execute("SELECT COUNT(*) FROM assignments").fetchone()[0],"exams":c.execute("SELECT COUNT(*) FROM exams").fetchone()[0]}
    return render_template("admin.html",users=users,courses=courses,teachers=teachers,stats=stats)

@app.route("/profile",methods=["GET","POST"])
@login_required
def profile():
    u=current_user()
    if request.method=="POST":
        name=request.form.get("name","").strip()
        if name:
            with db() as c: c.execute("UPDATE users SET name=? WHERE id=?",(name,u["id"]))
            flash("Profile updated.","success"); return redirect(url_for("profile"))
        flash("Name cannot be blank.","error")
    with db() as c: full=c.execute("SELECT * FROM users WHERE id=?",(u["id"],)).fetchone()
    return render_template("profile.html",profile=full)

@app.errorhandler(403)
def forbidden(e): return render_template("error.html",code=403,message="You do not have permission to view this page."),403
@app.errorhandler(404)
def not_found(e): return render_template("error.html",code=404,message="We could not find that page."),404

init_db()
if __name__=="__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG")=="1",host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
