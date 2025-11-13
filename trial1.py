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
        'host': st.secrets.get('DB_HOST', os.getenv('DB_HOST', 'trolley.proxy.rlwy.net')),
        'user': st.secrets.get('DB_USER', os.getenv('DB_USER', 'root')),
        'password': st.secrets.get('DB_PASSWORD', os.getenv('DB_PASSWORD', 'BDuUCrTHxJTWMmeDVdDpRSYCAnvKSulX')),
        'database': st.secrets.get('DB_NAME', os.getenv('DB_NAME', 'railway')),
        'port': int(st.secrets.get('DB_PORT', os.getenv('DB_PORT', 46682)))
    }
except:
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', 'root'),
        'database': os.getenv('DB_NAME', 'exam_management'),
        'port': int(os.getenv('DB_PORT', 3306))
    }

# Grading System - Pure Functions (No Database Dependencies)
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

def calculate_attempt_status(score_obtained):
    """Calculate attempt status based on score"""
    return 'completed' if score_obtained is not None else 'pending'

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
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role ENUM('admin', 'teacher', 'student') NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                phone VARCHAR(20)
            )
        """)
        
        # Create STUDENT table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS STUDENT (
                student_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT UNIQUE NOT NULL,
                roll_number VARCHAR(20) UNIQUE NOT NULL,
                date_of_birth DATE,
                FOREIGN KEY (user_id) REFERENCES USERS(user_id) ON DELETE CASCADE
            )
        """)
        
        # Create TEACHER table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS TEACHER (
                teacher_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT UNIQUE NOT NULL,
                employee_id VARCHAR(20) UNIQUE NOT NULL,
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
                exam_type VARCHAR(50),
                total_marks INT NOT NULL,
                FOREIGN KEY (course_id) REFERENCES COURSE(course_id) ON DELETE CASCADE
            )
        """)
        
        # Create ENROLLMENT table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ENROLLMENT (
                enrollment_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                course_id INT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES STUDENT(student_id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES COURSE(course_id) ON DELETE CASCADE,
                UNIQUE KEY unique_enrollment (student_id, course_id)
            )
        """)
        
        # Create EXAM_ATTEMPT table (REMOVED status column - 3NF compliant)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS EXAM_ATTEMPT (
                attempt_id INT AUTO_INCREMENT PRIMARY KEY,
                exam_id INT NOT NULL,
                student_id INT NOT NULL,
                score_obtained FLOAT,
                FOREIGN KEY (exam_id) REFERENCES EXAM(exam_id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES STUDENT(student_id) ON DELETE CASCADE
            )
        """)
        
        # Create GRADE table (REMOVED letter_grade and status columns - 3NF compliant)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS GRADE (
                grade_id INT AUTO_INCREMENT PRIMARY KEY,
                enrollment_id INT NOT NULL,
                total_score FLOAT,
                FOREIGN KEY (enrollment_id) REFERENCES ENROLLMENT(enrollment_id) ON DELETE CASCADE
            )
        """)
        
        # Insert default admin if not exists
        cursor.execute("SELECT * FROM USERS WHERE username = 'admin'")
        if not cursor.fetchone():
            admin_pass = hash_password('admin123')
            cursor.execute("""
                INSERT INTO USERS (username, email, password_hash, role, full_name) 
                VALUES ('admin', 'admin@system.com', %s, 'admin', 'System Administrator')
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
            SELECT s.*, u.full_name, u.email, u.phone 
            FROM STUDENT s
            JOIN USERS u ON s.user_id = u.user_id
            WHERE s.user_id = %s
        """, (user_id,))
        student = cursor.fetchone()
        cursor.close()
        conn.close()
        return student
    return None

def get_student_enrollments(student_id):
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
        """, (student_id,))
        enrollments = cursor.fetchall()
        cursor.close()
        conn.close()
        return enrollments
    return []

def get_student_exam_attempts(student_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ea.*, e.exam_title, e.exam_type, e.total_marks, 
                   c.course_code, c.course_name
            FROM EXAM_ATTEMPT ea
            JOIN EXAM e ON ea.exam_id = e.exam_id
            JOIN COURSE c ON e.course_id = c.course_id
            WHERE ea.student_id = %s
            ORDER BY ea.attempt_id DESC
        """, (student_id,))
        attempts = cursor.fetchall()
        
        # Calculate status on-the-fly (3NF compliant)
        for attempt in attempts:
            attempt['status'] = calculate_attempt_status(attempt['score_obtained'])
            if attempt['score_obtained'] is not None:
                attempt['grade'] = calculate_grade(attempt['score_obtained'], attempt['total_marks'])
        
        cursor.close()
        conn.close()
        return attempts
    return []

def get_student_grades(student_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT g.*, c.course_code, c.course_name, e.course_id
            FROM GRADE g
            JOIN ENROLLMENT e ON g.enrollment_id = e.enrollment_id
            JOIN COURSE c ON e.course_id = c.course_id
            WHERE e.student_id = %s
        """, (student_id,))
        grades = cursor.fetchall()
        
        # Calculate letter_grade and status on-the-fly (3NF compliant)
        for grade in grades:
            # Get average total marks for the course
            cursor.execute("""
                SELECT AVG(ex.total_marks) as avg_marks
                FROM EXAM ex
                WHERE ex.course_id = %s
            """, (grade['course_id'],))
            result = cursor.fetchone()
            avg_marks = result['avg_marks'] if result and result['avg_marks'] else 100
            
            # Calculate derived fields
            grade['letter_grade'] = calculate_grade(grade['total_score'], avg_marks)
            grade['status'] = determine_pass_fail(grade['letter_grade'])
        
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
            SELECT t.*, u.full_name, u.email, u.phone 
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
            SELECT ea.*, s.roll_number, u.full_name, e.total_marks
            FROM EXAM_ATTEMPT ea
            JOIN STUDENT s ON ea.student_id = s.student_id
            JOIN USERS u ON s.user_id = u.user_id
            JOIN EXAM e ON ea.exam_id = e.exam_id
            WHERE ea.exam_id = %s
            ORDER BY u.full_name
        """, (exam_id,))
        attempts = cursor.fetchall()
        
        # Calculate status and grade on-the-fly (3NF compliant)
        for attempt in attempts:
            attempt['status'] = calculate_attempt_status(attempt['score_obtained'])
            if attempt['score_obtained'] is not None:
                attempt['grade'] = calculate_grade(attempt['score_obtained'], attempt['total_marks'])
        
        cursor.close()
        conn.close()
        return attempts
    return []

def update_exam_attempt(attempt_id, score):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        # Only store score_obtained, status is calculated on-the-fly
        cursor.execute("""
            UPDATE EXAM_ATTEMPT 
            SET score_obtained = %s
            WHERE attempt_id = %s
        """, (score, attempt_id))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    return False

def create_exam(course_id, exam_title, exam_type, total_marks):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO EXAM (course_id, exam_title, exam_type, total_marks)
                VALUES (%s, %s, %s, %s)
            """, (course_id, exam_title, exam_type, total_marks))
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

def create_exam_attempt(exam_id, student_id):
    """Create a new exam attempt for a student"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO EXAM_ATTEMPT (exam_id, student_id, score_obtained)
                VALUES (%s, %s, NULL)
            """, (exam_id, student_id))
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
def add_student(username, email, password, full_name, phone, roll_number, date_of_birth):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            hashed_pass = hash_password(password)
            cursor.execute("""
                INSERT INTO USERS (username, email, password_hash, role, full_name, phone)
                VALUES (%s, %s, %s, 'student', %s, %s)
            """, (username, email, hashed_pass, full_name, phone))
            user_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO STUDENT (user_id, roll_number, date_of_birth)
                VALUES (%s, %s, %s)
            """, (user_id, roll_number, date_of_birth))
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

def add_teacher(username, email, password, full_name, phone, employee_id, specialization):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            hashed_pass = hash_password(password)
            cursor.execute("""
                INSERT INTO USERS (username, email, password_hash, role, full_name, phone)
                VALUES (%s, %s, %s, 'teacher', %s, %s)
            """, (username, email, hashed_pass, full_name, phone))
            user_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO TEACHER (user_id, employee_id, specialization)
                VALUES (%s, %s, %s)
            """, (user_id, employee_id, specialization))
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

def enroll_student(student_id, course_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO ENROLLMENT (student_id, course_id)
                VALUES (%s, %s)
            """, (student_id, course_id))
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
            SELECT t.teacher_id, t.employee_id, t.specialization, 
                   u.full_name, u.email, u.username
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
            SELECT s.student_id, s.roll_number, s.date_of_birth,
                   u.full_name, u.email, u.phone, u.username
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

def calculate_and_update_grades():
    """Calculate grades for all enrollments based on exam attempts - 3NF compliant"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        # Get all enrollments
        cursor.execute("""
            SELECT e.enrollment_id, e.student_id, e.course_id
            FROM ENROLLMENT e
        """)
        enrollments = cursor.fetchall()
        
        for enrollment in enrollments:
            # Get all exam attempts for this student in this course
            cursor.execute("""
                SELECT ea.score_obtained, ex.total_marks
                FROM EXAM_ATTEMPT ea
                JOIN EXAM ex ON ea.exam_id = ex.exam_id
                WHERE ea.student_id = %s AND ex.course_id = %s 
                AND ea.score_obtained IS NOT NULL
            """, (enrollment['student_id'], enrollment['course_id']))
            attempts = cursor.fetchall()
            
            if attempts:
                # Calculate total score (sum of all exam scores)
                total_score = sum(a['score_obtained'] for a in attempts)
                
                # Insert or update grade (only store total_score, not derived fields)
                cursor.execute("""
                    INSERT INTO GRADE (enrollment_id, total_score)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE 
                        total_score = %s
                """, (enrollment['enrollment_id'], total_score, total_score))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    return False

def get_all_grades_with_calculations():
    """Get all grades with calculated letter_grade and status - 3NF compliant"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT g.grade_id, s.roll_number, u.full_name, c.course_code, c.course_name,
                   g.total_score, e.course_id
            FROM GRADE g
            JOIN ENROLLMENT e ON g.enrollment_id = e.enrollment_id
            JOIN STUDENT s ON e.student_id = s.student_id
            JOIN USERS u ON s.user_id = u.user_id
            JOIN COURSE c ON e.course_id = c.course_id
            ORDER BY s.roll_number, c.course_code
        """)
        grades = cursor.fetchall()
        
        # Calculate derived fields for each grade
        for grade in grades:
            # Get average total marks for the course
            cursor.execute("""
                SELECT AVG(ex.total_marks) as avg_marks
                FROM EXAM ex
                WHERE ex.course_id = %s
            """, (grade['course_id'],))
            result = cursor.fetchone()
            avg_marks = result['avg_marks'] if result and result['avg_marks'] else 100
            
            # Calculate derived fields
            grade['letter_grade'] = calculate_grade(grade['total_score'], avg_marks)
            grade['status'] = determine_pass_fail(grade['letter_grade'])
        
        cursor.close()
        conn.close()
        return grades
    return []

# Streamlit UI
def main():
    st.set_page_config(page_title="Exam Management System - 3NF Compliant", layout="wide")
    
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
        st.caption("3NF Compliant Database Design (No Timestamps)")
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
            col2.metric("Name", student['full_name'])
            col3.metric("Email", student['email'])
            col4.metric("Phone", student['phone'] or 'N/A')
            
            st.markdown("---")
            
            # Tabs for different views
            tab1, tab2, tab3 = st.tabs(["📚 My Courses", "📝 Exam Attempts", "🎯 Grades"])
            
            with tab1:
                st.subheader("Enrolled Courses")
                enrollments = get_student_enrollments(student['student_id'])
                if enrollments:
                    df = pd.DataFrame(enrollments)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("You are not enrolled in any courses yet.")
            
            with tab2:
                st.subheader("My Exam Attempts")
                attempts = get_student_exam_attempts(student['student_id'])
                if attempts:
                    df = pd.DataFrame(attempts)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.caption("✨ Status and Grade are calculated dynamically (3NF compliant)")
                else:
                    st.info("No exam attempts recorded yet.")
            
            with tab3:
                st.subheader("My Grades")
                grades = get_student_grades(student['student_id'])
                if grades:
                    # Remove course_id from display
                    display_grades = [{k: v for k, v in g.items() if k != 'course_id'} for g in grades]
                    df = pd.DataFrame(display_grades)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.caption("✨ Letter Grade and Status are calculated dynamically (3NF compliant)")
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
            st.info(f"Employee ID: {teacher['employee_id']} | Specialization: {teacher['specialization']}")
            
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
                                with st.expander(f"{exam['exam_title']} ({exam['exam_type']}) - {exam['total_marks']} marks"):
                                    
                                    st.markdown("#### Student Attempts")
                                    attempts = get_exam_attempts(exam['exam_id'])
                                    
                                    if attempts:
                                        for attempt in attempts:
                                            col1, col2, col3 = st.columns([2, 2, 1])
                                            
                                            with col1:
                                                st.write(f"**{attempt['full_name']}** ({attempt['roll_number']})")
                                                status_color = "🟢" if attempt['status'] == 'completed' else "🟡"
                                                st.caption(f"{status_color} Status: {attempt['status']}")
                                                if attempt.get('grade'):
                                                    st.caption(f"Grade: {attempt['grade']}")
                                            
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
                                                    if update_exam_attempt(attempt['attempt_id'], new_score):
                                                        st.success("Score updated!")
                                                        st.rerun()
                                        
                                        st.caption("✨ Status and Grade are calculated dynamically (3NF compliant)")
                                    else:
                                        st.info("No attempts recorded yet.")
                        else:
                            st.info("No exams created for this course yet.")
                    
                    with tab2:
                        st.subheader("Create New Exam")
                        exam_title = st.text_input("Exam Title")
                        exam_type = st.selectbox("Exam Type", ["Midterm", "Final", "Quiz", "Assignment"])
                        total_marks = st.number_input("Total Marks", min_value=1, max_value=200, value=100)
                        
                        if st.button("Create Exam"):
                            if exam_title:
                                if create_exam(course_id, exam_title, exam_type, total_marks):
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
                                SELECT s.student_id, s.roll_number, u.full_name
                                FROM ENROLLMENT e
                                JOIN STUDENT s ON e.student_id = s.student_id
                                JOIN USERS u ON s.user_id = u.user_id
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
                                exam_options = {f"{e['exam_title']} ({e['exam_type']})": e['exam_id'] for e in exams}
                                selected_exam = st.selectbox("Select Exam", list(exam_options.keys()))
                                selected_exam_id = exam_options[selected_exam]
                            
                            with col2:
                                student_options = {f"{s['roll_number']} - {s['full_name']}": s['student_id'] for s in enrolled_students}
                                selected_student = st.selectbox("Select Student", list(student_options.keys()))
                                selected_student_id = student_options[selected_student]
                            
                            if st.button("Add Exam Attempt"):
                                if create_exam_attempt(selected_exam_id, selected_student_id):
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
        
        tabs = st.tabs(["➕ Add Data", "👥 View Students", "👨‍🏫 View Teachers", "📚 View Courses", "📊 Calculate Grades"])
        
        # Add Data Tab
        with tabs[0]:
            add_tab = st.tabs(["Add Student", "Add Teacher", "Add Course", "Enroll Student"])
            
            with add_tab[0]:
                st.subheader("Add New Student")
                col1, col2 = st.columns(2)
                with col1:
                    username = st.text_input("Username")
                    email = st.text_input("Email")
                    full_name = st.text_input("Full Name")
                    phone = st.text_input("Phone")
                with col2:
                    roll_number = st.text_input("Roll Number")
                    date_of_birth = st.date_input("Date of Birth")
                    password = st.text_input("Password", type="password", key="student_pass")
                
                if st.button("Add Student"):
                    if all([username, email, full_name, roll_number, password]):
                        if add_student(username, email, password, full_name, phone, roll_number, date_of_birth):
                            st.success(f"Student {full_name} added successfully!")
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
                    teacher_email = st.text_input("Email", key="teacher_email")
                    teacher_name = st.text_input("Full Name", key="teacher_name")
                with col2:
                    teacher_phone = st.text_input("Phone", key="teacher_phone")
                    employee_id = st.text_input("Employee ID")
                    specialization = st.text_input("Specialization")
                teacher_password = st.text_input("Password", type="password", key="teacher_pass")
                
                if st.button("Add Teacher"):
                    if all([teacher_username, teacher_email, teacher_name, employee_id, teacher_password]):
                        if add_teacher(teacher_username, teacher_email, teacher_password, teacher_name, teacher_phone, employee_id, specialization):
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
                        teacher_options = {f"{t['full_name']} ({t['employee_id']})": t['teacher_id'] for t in teachers}
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
                        student_options = {f"{s['roll_number']} - {s['full_name']}": s['student_id'] for s in students}
                        selected_student = st.selectbox("Select Student", list(student_options.keys()))
                        enroll_student_id = student_options[selected_student]
                    
                    with col2:
                        course_options = {f"{c['course_code']} - {c['course_name']}": c['course_id'] for c in courses}
                        selected_course = st.selectbox("Select Course", list(course_options.keys()))
                        enroll_course_id = course_options[selected_course]
                    
                    if st.button("Enroll Student"):
                        if enroll_student(enroll_student_id, enroll_course_id):
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
        
        # Calculate Grades Tab
        with tabs[4]:
            st.subheader("Calculate and Update Grades")
            st.write("This will calculate grades for all students based on their exam attempts.")
            st.info("✨ 3NF Compliant: Only total_score is stored. Letter grades and pass/fail status are calculated dynamically.")
            
            if st.button("Calculate Grades", type="primary"):
                if calculate_and_update_grades():
                    st.success("Grades calculated and updated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to calculate grades")
            
            st.markdown("---")
            st.subheader("View All Grades")
            
            grades = get_all_grades_with_calculations()
            
            if grades:
                # Remove course_id from display
                display_grades = [{k: v for k, v in g.items() if k != 'course_id'} for g in grades]
                df = pd.DataFrame(display_grades)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption("✨ Letter Grade and Status are calculated dynamically from total_score (3NF compliant)")
            else:
                st.info("No grades calculated yet. Click 'Calculate Grades' button above.")

if __name__ == "__main__":
    main()
