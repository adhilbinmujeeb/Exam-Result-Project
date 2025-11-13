import streamlit as st
import mysql.connector
from mysql.connector import Error
import pandas as pd
import hashlib

# Database Configuration
import os

# Try to get from Streamlit secrets first, then environment variables, then defaults
try:
    DB_CONFIG = {
        'host': st.secrets.get('DB_HOST', os.getenv('DB_HOST', 'maglev.proxy.rlwy.net')),
        'user': st.secrets.get('DB_USER', os.getenv('DB_USER', 'root')),
        'password': st.secrets.get('DB_PASSWORD', os.getenv('DB_PASSWORD', 'qLLqcPiRVSWiTfbYWtXBMWexuOzQxmtN')),
        'database': st.secrets.get('DB_NAME', os.getenv('DB_NAME', 'railway')),
        'port': int(st.secrets.get('DB_PORT', os.getenv('DB_PORT', 59270)))
    }
except:
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', 'root'),
        'database': os.getenv('DB_NAME', 'exam_management'),
        'port': int(os.getenv('DB_PORT', 3306))
    }

# Grading System - Pure Functions
def calculate_grade(score, total_marks):
    """Calculate letter grade based on percentage"""
    if total_marks == 0:
        return 'F'
    percentage = (score / total_marks) * 100
    if percentage >= 90:
        return 'A'
    elif percentage >= 80:
        return 'B'
    elif percentage >= 70:
        return 'C'
    elif percentage >= 60:
        return 'D'
    else:
        return 'F'

def determine_pass_fail(grade):
    """Determine pass/fail status based on grade"""
    return 'Pass' if grade in ['A', 'B', 'C', 'D'] else 'Fail'

# Database Connection
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        st.error(f"Database connection error: {e}")
        return None

# Password hashing
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Initialize Database
def init_database():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        
        # Create USERS table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS USERS (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role ENUM('admin', 'teacher', 'student') NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                phone VARCHAR(20)
            )
        """)
        
        # Create STUDENT table (roll_number as PK)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS STUDENT (
                roll_number INT PRIMARY KEY,
                user_id INT UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                date_of_birth DATE,
                FOREIGN KEY (user_id) REFERENCES USERS(user_id) ON DELETE CASCADE
            )
        """)
        
        # Create TEACHER table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS TEACHER (
                teacher_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT UNIQUE NOT NULL,
                specialization VARCHAR(100),
                FOREIGN KEY (user_id) REFERENCES USERS(user_id) ON DELETE CASCADE
            )
        """)
        
        # Create COURSE table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS COURSE (
                course_id INT AUTO_INCREMENT PRIMARY KEY,
                course_code VARCHAR(20) UNIQUE NOT NULL,
                course_name VARCHAR(100) NOT NULL,
                teacher_id INT,
                FOREIGN KEY (teacher_id) REFERENCES TEACHER(teacher_id) ON DELETE SET NULL
            )
        """)
        
        # Create EXAM table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS EXAM (
                exam_id INT AUTO_INCREMENT PRIMARY KEY,
                course_id INT NOT NULL,
                exam_title VARCHAR(100) NOT NULL,
                total_marks INT NOT NULL,
                FOREIGN KEY (course_id) REFERENCES COURSE(course_id) ON DELETE CASCADE
            )
        """)
        
        # Create ENROLLMENT table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ENROLLMENT (
                enrollment_id INT AUTO_INCREMENT PRIMARY KEY,
                roll_number INT NOT NULL,
                course_id INT NOT NULL,
                FOREIGN KEY (roll_number) REFERENCES STUDENT(roll_number) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES COURSE(course_id) ON DELETE CASCADE,
                UNIQUE KEY unique_enrollment (student_id, course_id)
            )
        """)
        
        # Create EXAM_ATTEMPT table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS EXAM_ATTEMPT (
                attempt_id INT AUTO_INCREMENT PRIMARY KEY,
                exam_id INT NOT NULL,
                roll_number INT NOT NULL,
                score_obtained FLOAT,
                FOREIGN KEY (exam_id) REFERENCES EXAM(exam_id) ON DELETE CASCADE,
                FOREIGN KEY (roll_number) REFERENCES STUDENT(roll_number) ON DELETE CASCADE
            )
        """)
        
        # Create EXAM_RESULT table (NEW)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS EXAM_RESULT (
                result_id INT AUTO_INCREMENT PRIMARY KEY,
                attempt_id INT UNIQUE NOT NULL,
                letter_grade VARCHAR(2) NOT NULL,
                status VARCHAR(10) NOT NULL,
                FOREIGN KEY (attempt_id) REFERENCES EXAM_ATTEMPT(attempt_id) ON DELETE CASCADE
            )
        """)
        
        # Insert default admin if not exists
        cursor.execute("SELECT * FROM USERS WHERE username = 'admin'")
        if not cursor.fetchone():
            admin_pass = hash_password('admin123')
            cursor.execute("""
                INSERT INTO USERS (username, password_hash, role, full_name) 
                VALUES ('admin', %s, 'admin', 'System Administrator')
            """, (admin_pass,))
        
        conn.commit()
        cursor.close()
        conn.close()

# Authentication
def authenticate(username, password, role):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        hashed_pass = hash_password(password)
        cursor.execute("""
            SELECT * FROM USERS WHERE username = %s AND password_hash = %s AND role = %s
        """, (username, hashed_pass, role))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    return None

# Student Functions
def get_student_by_user_id(user_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.*, u.full_name, u.phone 
            FROM STUDENT s
            JOIN USERS u ON s.user_id = u.user_id
            WHERE s.user_id = %s
        """, (user_id,))
        student = cursor.fetchone()
        cursor.close()
        conn.close()
        return student
    return None

def get_student_enrollments(roll_number):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT e.enrollment_id, c.course_code, c.course_name,
                   u.full_name as teacher_name
            FROM ENROLLMENT e
            JOIN COURSE c ON e.course_id = c.course_id
            LEFT JOIN TEACHER t ON c.teacher_id = t.teacher_id
            LEFT JOIN USERS u ON t.user_id = u.user_id
            WHERE e.student_id = %s
        """, (roll_number,))
        enrollments = cursor.fetchall()
        cursor.close()
        conn.close()
        return enrollments
    return []

def get_student_exam_attempts(roll_number):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ea.*, e.exam_title, e.total_marks, 
                   c.course_code, c.course_name,
                   er.letter_grade, er.status
            FROM EXAM_ATTEMPT ea
            JOIN EXAM e ON ea.exam_id = e.exam_id
            JOIN COURSE c ON e.course_id = c.course_id
            LEFT JOIN EXAM_RESULT er ON ea.attempt_id = er.attempt_id
            WHERE ea.student_id = %s
            ORDER BY ea.attempt_id DESC
        """, (roll_number,))
        attempts = cursor.fetchall()
        cursor.close()
        conn.close()
        return attempts
    return []

def get_student_overall_grades(roll_number):
    """Calculate overall course grades from exam results"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        # Get all enrollments
        cursor.execute("""
            SELECT e.enrollment_id, e.course_id, c.course_code, c.course_name
            FROM ENROLLMENT e
            JOIN COURSE c ON e.course_id = c.course_id
            WHERE e.student_id = %s
        """, (roll_number,))
        enrollments = cursor.fetchall()
        
        grades = []
        for enrollment in enrollments:
            # Get all completed exam attempts with results
            cursor.execute("""
                SELECT ea.score_obtained, e.total_marks, er.letter_grade
                FROM EXAM_ATTEMPT ea
                JOIN EXAM e ON ea.exam_id = e.exam_id
                LEFT JOIN EXAM_RESULT er ON ea.attempt_id = er.attempt_id
                WHERE ea.student_id = %s AND e.course_id = %s 
                AND ea.score_obtained IS NOT NULL
            """, (roll_number, enrollment['course_id']))
            attempts = cursor.fetchall()
            
            if attempts:
                total_score = sum(a['score_obtained'] for a in attempts)
                avg_total_marks = sum(a['total_marks'] for a in attempts) / len(attempts)
                
                # Calculate overall grade
                overall_grade = calculate_grade(total_score / len(attempts), avg_total_marks)
                overall_status = determine_pass_fail(overall_grade)
                
                grades.append({
                    'course_code': enrollment['course_code'],
                    'course_name': enrollment['course_name'],
                    'total_score': total_score,
                    'exams_completed': len(attempts),
                    'overall_grade': overall_grade,
                    'status': overall_status
                })
        
        cursor.close()
        conn.close()
        return grades
    return []

# Teacher Functions
def get_teacher_by_user_id(user_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT t.*, u.full_name, u.phone 
            FROM TEACHER t
            JOIN USERS u ON t.user_id = u.user_id
            WHERE t.user_id = %s
        """, (user_id,))
        teacher = cursor.fetchone()
        cursor.close()
        conn.close()
        return teacher
    return None

def get_teacher_courses(teacher_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM COURSE WHERE teacher_id = %s
        """, (teacher_id,))
        courses = cursor.fetchall()
        cursor.close()
        conn.close()
        return courses
    return []

def get_course_exams(course_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM EXAM WHERE course_id = %s ORDER BY exam_id DESC
        """, (course_id,))
        exams = cursor.fetchall()
        cursor.close()
        conn.close()
        return exams
    return []

def get_exam_attempts(exam_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ea.*, s.roll_number, s.name, e.total_marks,
                   er.letter_grade, er.status
            FROM EXAM_ATTEMPT ea
            JOIN STUDENT s ON ea.student_id = s.roll_number
            JOIN EXAM e ON ea.exam_id = e.exam_id
            LEFT JOIN EXAM_RESULT er ON ea.attempt_id = er.attempt_id
            WHERE ea.exam_id = %s
            ORDER BY s.name
        """, (exam_id,))
        attempts = cursor.fetchall()
        cursor.close()
        conn.close()
        return attempts
    return []

def update_exam_attempt_and_result(attempt_id, score, total_marks):
    """Update exam attempt score and create/update result"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Update score
            cursor.execute("""
                UPDATE EXAM_ATTEMPT 
                SET score_obtained = %s
                WHERE attempt_id = %s
            """, (score, attempt_id))
            
            # Calculate grade and status
            letter_grade = calculate_grade(score, total_marks)
            status = determine_pass_fail(letter_grade)
            
            # Insert or update result
            cursor.execute("""
                INSERT INTO EXAM_RESULT (attempt_id, letter_grade, status)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    letter_grade = %s, status = %s
            """, (attempt_id, letter_grade, status, letter_grade, status))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            st.error(f"Error updating attempt: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
    return False

def create_exam(course_id, exam_title, total_marks):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO EXAM (course_id, exam_title, total_marks)
                VALUES (%s, %s, %s)
            """, (course_id, exam_title, total_marks))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            st.error(f"Error creating exam: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
    return False

def create_exam_attempt(exam_id, roll_number):
    """Create a new exam attempt for a student"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO EXAM_ATTEMPT (exam_id, student_id, score_obtained)
                VALUES (%s, %s, NULL)
            """, (exam_id, roll_number))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            st.error(f"Error creating exam attempt: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
    return False

# Admin Functions
def add_student(username, password, full_name, phone, roll_number, name, date_of_birth):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            hashed_pass = hash_password(password)
            cursor.execute("""
                INSERT INTO USERS (username, password_hash, role, full_name, phone)
                VALUES (%s, %s, 'student', %s, %s)
            """, (username, hashed_pass, full_name, phone))
            user_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO STUDENT (roll_number, user_id, name, date_of_birth)
                VALUES (%s, %s, %s, %s)
            """, (roll_number, user_id, name, date_of_birth))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            st.error(f"Error adding student: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
    return False

def add_teacher(username, password, full_name, phone, specialization):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            hashed_pass = hash_password(password)
            cursor.execute("""
                INSERT INTO USERS (username, password_hash, role, full_name, phone)
                VALUES (%s, %s, 'teacher', %s, %s)
            """, (username, hashed_pass, full_name, phone))
            user_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO TEACHER (user_id, specialization)
                VALUES (%s, %s)
            """, (user_id, specialization))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            st.error(f"Error adding teacher: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
    return False

def add_course(course_code, course_name, teacher_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO COURSE (course_code, course_name, teacher_id)
                VALUES (%s, %s, %s)
            """, (course_code, course_name, teacher_id))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            st.error(f"Error adding course: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
    return False

def enroll_student(roll_number, course_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO ENROLLMENT (student_id, course_id)
                VALUES (%s, %s)
            """, (roll_number, course_id))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            st.error(f"Error enrolling student: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
    return False

def get_all_teachers():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT t.teacher_id, t.specialization, 
                   u.full_name, u.username
            FROM TEACHER t
            JOIN USERS u ON t.user_id = u.user_id
            ORDER BY u.full_name
        """)
        teachers = cursor.fetchall()
        cursor.close()
        conn.close()
        return teachers
    return []

def get_all_students():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.roll_number, s.name, s.date_of_birth,
                   u.full_name, u.phone, u.username
            FROM STUDENT s
            JOIN USERS u ON s.user_id = u.user_id
            ORDER BY s.roll_number
        """)
        students = cursor.fetchall()
        cursor.close()
        conn.close()
        return students
    return []

def get_all_courses():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.*, u.full_name as teacher_name 
            FROM COURSE c
            LEFT JOIN TEACHER t ON c.teacher_id = t.teacher_id
            LEFT JOIN USERS u ON t.user_id = u.user_id
            ORDER BY c.course_code
        """)
        courses = cursor.fetchall()
        cursor.close()
        conn.close()
        return courses
    return []

def get_all_results():
    """Get all exam results"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.roll_number, s.name, c.course_code, c.course_name,
                   e.exam_title, ea.score_obtained, e.total_marks,
                   er.letter_grade, er.status
            FROM EXAM_RESULT er
            JOIN EXAM_ATTEMPT ea ON er.attempt_id = ea.attempt_id
            JOIN STUDENT s ON ea.student_id = s.roll_number
            JOIN EXAM e ON ea.exam_id = e.exam_id
            JOIN COURSE c ON e.course_id = c.course_id
            ORDER BY s.roll_number, c.course_code
        """)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results
    return []

# Streamlit UI
def main():
    st.set_page_config(page_title="Exam Management System", layout="wide")
    
    # Initialize database
    init_database()
    
    # Session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.role = None
    
    # Login Page
    if not st.session_state.logged_in:
        st.title("🎓 Exam Management System")
        st.caption("With EXAM_RESULT Table - Roll Number as Primary Key")
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.subheader("Login")
            role = st.selectbox("Select Role", ["student", "teacher", "admin"])
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Login", use_container_width=True):
                user = authenticate(username, password, role)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.session_state.role = role
                    st.rerun()
                else:
                    st.error("Invalid credentials!")
            
            st.info("Default Admin: username=`admin`, password=`admin123`")
    
    # Student Dashboard
    elif st.session_state.role == "student":
        st.title("📚 Student Dashboard")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"Welcome, {st.session_state.user['full_name']}")
        with col2:
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.session_state.role = None
                st.rerun()
        
        st.markdown("---")
        
        student = get_student_by_user_id(st.session_state.user['user_id'])
        
        if student:
            # Student Details
            st.subheader("📋 Student Details")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Roll Number", student['roll_number'])
            col2.metric("Name", student['name'])
            col3.metric("Full Name", student['full_name'])
            col4.metric("Phone", student['phone'] or 'N/A')
            
            st.markdown("---")
            
            # Tabs for different views
            tab1, tab2, tab3 = st.tabs(["📚 My Courses", "📝 Exam Attempts", "🎯 Overall Grades"])
            
            with tab1:
                st.subheader("Enrolled Courses")
                enrollments = get_student_enrollments(student['roll_number'])
                if enrollments:
                    df = pd.DataFrame(enrollments)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("You are not enrolled in any courses yet.")
            
            with tab2:
                st.subheader("My Exam Attempts & Results")
                attempts = get_student_exam_attempts(student['roll_number'])
                if attempts:
                    df = pd.DataFrame(attempts)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.caption("✨ Letter Grade and Status from EXAM_RESULT table")
                else:
                    st.info("No exam attempts recorded yet.")
            
            with tab3:
                st.subheader("Overall Course Grades")
                grades = get_student_overall_grades(student['roll_number'])
                if grades:
                    df = pd.DataFrame(grades)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.caption("✨ Overall grades calculated from all exam results")
                else:
                    st.info("No grades available yet.")
    
    # Teacher Dashboard
    elif st.session_state.role == "teacher":
        st.title("👨‍🏫 Teacher Dashboard")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"Welcome, {st.session_state.user['full_name']}")
        with col2:
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.session_state.role = None
                st.rerun()
        
        st.markdown("---")
        
        teacher = get_teacher_by_user_id(st.session_state.user['user_id'])
        
        if teacher:
            st.info(f"Specialization: {teacher['specialization']}")
            
            courses = get_teacher_courses(teacher['teacher_id'])
            
            if courses:
                st.subheader("📚 Your Courses")
                course_names = [f"{c['course_code']} - {c['course_name']}" for c in courses]
                selected_course = st.selectbox("Select Course", course_names)
                
                if selected_course:
                    course_id = [c['course_id'] for c in courses if f"{c['course_code']} - {c['course_name']}" == selected_course][0]
                    
                    st.markdown("---")
                    
                    tab1, tab2, tab3 = st.tabs(["📝 Exams", "➕ Create Exam", "✏️ Add Attempt"])
                    
                    with tab1:
                        st.subheader("Course Exams")
                        exams = get_course_exams(course_id)
                        
                        if exams:
                            for exam in exams:
                                with st.expander(f"{exam['exam_title']} - {exam['total_marks']} marks"):
                                    
                                    st.markdown("#### Student Attempts & Results")
                                    attempts = get_exam_attempts(exam['exam_id'])
                                    
                                    if attempts:
                                        for attempt in attempts:
                                            col1, col2, col3 = st.columns([2, 2, 1])
                                            
                                            with col1:
                                                st.write(f"**{attempt['name']}** ({attempt['roll_number']})")
                                                if attempt.get('letter_grade'):
                                                    status_color = "🟢" if attempt['status'] == 'Pass' else "🔴"
                                                    st.caption(f"{status_color} Grade: {attempt['letter_grade']} | Status: {attempt['status']}")
                                                else:
                                                    st.caption("⏳ Not graded yet")
                                            
                                            with col2:
                                                current_score = attempt['score_obtained'] if attempt['score_obtained'] else 0
                                                new_score = st.number_input(
                                                    "Score",
                                                    min_value=0.0,
                                                    max_value=float(exam['total_marks']),
                                                    value=float(current_score),
                                                    key=f"score_{attempt['attempt_id']}"
                                                )
                                            
                                            with col3:
                                                if st.button("Update", key=f"btn_{attempt['attempt_id']}"):
                                                    if update_exam_attempt_and_result(attempt['attempt_id'], new_score, exam['total_marks']):
                                                        st.success("Score & Result updated!")
                                                        st.rerun()
                                        
                                        st.caption("✨ Results automatically saved to EXAM_RESULT table")
                                    else:
                                        st.info("No attempts recorded yet.")
                        else:
                            st.info("No exams created for this course yet.")
                    
                    with tab2:
                        st.subheader("Create New Exam")
                        exam_title = st.text_input("Exam Title")
                        total_marks = st.number_input("Total Marks", min_value=1, max_value=200, value=100)
                        
                        if st.button("Create Exam"):
                            if exam_title:
                                if create_exam(course_id, exam_title, total_marks):
                                    st.success("Exam created successfully!")
                                    st.rerun()
                            else:
                                st.warning("Please enter exam title")
                    
                    with tab3:
                        st.subheader("Add Exam Attempt for Student")
                        
                        # Get course exams
                        exams = get_course_exams(course_id)
                        
                        # Get enrolled students
                        conn = get_db_connection()
                        if conn:
                            cursor = conn.cursor(dictionary=True)
                            cursor.execute("""
                                SELECT s.roll_number, s.name
                                FROM ENROLLMENT e
                                JOIN STUDENT s ON e.student_id = s.roll_number
                                WHERE e.course_id = %s
                                ORDER BY s.roll_number
                            """, (course_id,))
                            enrolled_students = cursor.fetchall()
                            cursor.close()
                            conn.close()
                        else:
                            enrolled_students = []
                        
                        if exams and enrolled_students:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                exam_options = {f"{e['exam_title']}": e['exam_id'] for e in exams}
                                selected_exam = st.selectbox("Select Exam", list(exam_options.keys()))
                                selected_exam_id = exam_options[selected_exam]
                            
                            with col2:
                                student_options = {f"{s['roll_number']} - {s['name']}": s['roll_number'] for s in enrolled_students}
                                selected_student = st.selectbox("Select Student", list(student_options.keys()))
                                selected_roll_number = student_options[selected_student]
                            
                            if st.button("Add Exam Attempt"):
                                if create_exam_attempt(selected_exam_id, selected_roll_number):
                                    st.success("Exam attempt added successfully!")
                                    st.rerun()
                                else:
                                    st.error("Failed to add exam attempt (may already exist)")
                        else:
                            if not exams:
                                st.warning("No exams available. Please create an exam first.")
                            if not enrolled_students:
                                st.warning("No students enrolled in this course.")
            else:
                st.info("You are not assigned to any courses yet.")
    
    # Admin Dashboard
    elif st.session_state.role == "admin":
        st.title("⚙️ Admin Dashboard")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"Welcome, {st.session_state.user['full_name']}")
        with col2:
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.session_state.role = None
                st.rerun()
        
        st.markdown("---")
        
        tabs = st.tabs(["➕ Add Data", "👥 View Students", "👨‍🏫 View Teachers", "📚 View Courses", "📊 View Results"])
        
        # Add Data Tab
        with tabs[0]:
            add_tab = st.tabs(["Add Student", "Add Teacher", "Add Course", "Enroll Student"])
            
            with add_tab[0]:
                st.subheader("Add New Student")
                col1, col2 = st.columns(2)
                with col1:
                    username = st.text_input("Username")
                    full_name = st.text_input("Full Name")
                    phone = st.text_input("Phone")
                    roll_number = st.text_input("Roll Number")
                with col2:
                    password = st.text_input("Password", type="password", key="student_pass")
                    name = st.text_input("Student Name")
                    date_of_birth = st.date_input("Date of Birth")
                
                if st.button("Add Student"):
                    if all([username, password, full_name, roll_number, name]):
                        if add_student(username, password, full_name, phone, roll_number, name, date_of_birth):
                            st.success(f"Student {name} added successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to add student")
                    else:
                        st.warning("Please fill all required fields")
            
            with add_tab[1]:
                st.subheader("Add New Teacher")
                col1, col2 = st.columns(2)
                with col1:
                    teacher_username = st.text_input("Username", key="teacher_username")
                    teacher_name = st.text_input("Full Name", key="teacher_name")
                    teacher_phone = st.text_input("Phone", key="teacher_phone")
                with col2:
                    teacher_password = st.text_input("Password", type="password", key="teacher_pass")
                    specialization = st.text_input("Specialization")
                
                if st.button("Add Teacher"):
                    if all([teacher_username, teacher_password, teacher_name]):
                        if add_teacher(teacher_username, teacher_password, teacher_name, teacher_phone, specialization):
                            st.success(f"Teacher {teacher_name} added successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to add teacher")
                    else:
                        st.warning("Please fill all required fields")
            
            with add_tab[2]:
                st.subheader("Add New Course")
                col1, col2 = st.columns(2)
                with col1:
                    course_code = st.text_input("Course Code")
                    course_name = st.text_input("Course Name")
                with col2:
                    teachers = get_all_teachers()
                    if teachers:
                        teacher_options = {f"{t['full_name']}": t['teacher_id'] for t in teachers}
                        selected_teacher = st.selectbox("Assign Teacher", list(teacher_options.keys()))
                        teacher_id = teacher_options[selected_teacher]
                    else:
                        st.warning("No teachers available. Please add teachers first.")
                        teacher_id = None
                
                if st.button("Add Course"):
                    if course_code and course_name and teacher_id:
                        if add_course(course_code, course_name, teacher_id):
                            st.success(f"Course {course_name} added successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to add course")
                    else:
                        st.warning("Please fill all fields")
            
            with add_tab[3]:
                st.subheader("Enroll Student in Course")
                students = get_all_students()
                courses = get_all_courses()
                
                if students and courses:
                    col1, col2 = st.columns(2)
                    with col1:
                        student_options = {f"{s['roll_number']} - {s['name']}": s['roll_number'] for s in students}
                        selected_student = st.selectbox("Select Student", list(student_options.keys()))
                        enroll_roll_number = student_options[selected_student]
                    
                    with col2:
                        course_options = {f"{c['course_code']} - {c['course_name']}": c['course_id'] for c in courses}
                        selected_course = st.selectbox("Select Course", list(course_options.keys()))
                        enroll_course_id = course_options[selected_course]
                    
                    if st.button("Enroll Student"):
                        if enroll_student(enroll_roll_number, enroll_course_id):
                            st.success("Student enrolled successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to enroll student")
                else:
                    st.warning("Please add students and courses first.")
        
        # View Students Tab
        with tabs[1]:
            st.subheader("All Students")
            students = get_all_students()
            if students:
                df = pd.DataFrame(students)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No students found.")
        
        # View Teachers Tab
        with tabs[2]:
            st.subheader("All Teachers")
            teachers = get_all_teachers()
            if teachers:
                df = pd.DataFrame(teachers)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No teachers found.")
        
        # View Courses Tab
        with tabs[3]:
            st.subheader("All Courses")
            courses = get_all_courses()
            if courses:
                df = pd.DataFrame(courses)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No courses found.")
        
        # View Results Tab
        with tabs[4]:
            st.subheader("All Exam Results")
            st.info("✨ Results from EXAM_RESULT table (1:1 with EXAM_ATTEMPT)")
            
            results = get_all_results()
            
            if results:
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption("✨ Letter Grade and Status stored in EXAM_RESULT table")
            else:
                st.info("No exam results available yet.")

if __name__ == "__main__":
    main()
