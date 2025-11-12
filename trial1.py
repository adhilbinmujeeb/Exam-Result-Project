import streamlit as st
import mysql.connector
from mysql.connector import Error
import pandas as pd
import hashlib
from datetime import datetime
import os

# Database Configuration
try:
    DB_CONFIG = {
        'host': st.secrets.get('DB_HOST', os.getenv('DB_HOST', 'interchange.proxy.rlwy.net')),
        'user': st.secrets.get('DB_USER', os.getenv('DB_USER', 'root')),
        'password': st.secrets.get('DB_PASSWORD', os.getenv('DB_PASSWORD', 'IvFcKTyXyPvwjFTXPyEasdaHdDvhKoaM')),
        'database': st.secrets.get('DB_NAME', os.getenv('DB_NAME', 'railway')),
        'port': int(st.secrets.get('DB_PORT', os.getenv('DB_PORT', 49523)))
    }
except:
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', 'root'),
        'database': os.getenv('DB_NAME', 'exam_management'),
        'port': int(os.getenv('DB_PORT', 3306))
    }

# Grading System
def calculate_grade(marks):
    """Calculate grade based on marks"""
    if marks >= 90:
        return 'O', 10
    elif marks >= 80:
        return 'A+', 9
    elif marks >= 70:
        return 'A', 8
    elif marks >= 60:
        return 'B+', 7
    elif marks >= 50:
        return 'B', 6
    elif marks >= 40:
        return 'C', 5
    else:
        return 'F', 0

def calculate_sgpa(grades_credits):
    """Calculate SGPA from grades and credits"""
    total_credits = sum(credit for _, credit in grades_credits)
    if total_credits == 0:
        return 0
    weighted_sum = sum(grade_point * credit for grade_point, credit in grades_credits)
    return round(weighted_sum / total_credits, 2)

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

# Initialize Database based on normalized ER diagram
def init_database():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        
        # ADMINISTRATOR table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ADMINISTRATOR (
                admin_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(100),
                full_name VARCHAR(100) NOT NULL
            )
        """)
        
        # DEPARTMENT table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS DEPARTMENT (
                department_id INT AUTO_INCREMENT PRIMARY KEY,
                department_name VARCHAR(100) NOT NULL,
                department_code VARCHAR(20) UNIQUE NOT NULL,
                description TEXT
            )
        """)
        
        # TEACHER table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS TEACHER (
                teacher_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100),
                password VARCHAR(255) NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                phone VARCHAR(20),
                department_id INT,
                FOREIGN KEY (department_id) REFERENCES DEPARTMENT(department_id)
            )
        """)
        
        # STUDENT table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS STUDENT (
                student_id INT AUTO_INCREMENT PRIMARY KEY,
                student_number VARCHAR(50) UNIQUE NOT NULL,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100),
                password VARCHAR(255) NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                phone VARCHAR(20),
                department_id INT,
                FOREIGN KEY (department_id) REFERENCES DEPARTMENT(department_id)
            )
        """)
        
        # COURSE table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS COURSE (
                course_id INT AUTO_INCREMENT PRIMARY KEY,
                course_code VARCHAR(20) UNIQUE NOT NULL,
                course_name VARCHAR(100) NOT NULL,
                credit_hours INT NOT NULL,
                semester VARCHAR(20),
                department_id INT,
                teacher_id INT,
                FOREIGN KEY (department_id) REFERENCES DEPARTMENT(department_id),
                FOREIGN KEY (teacher_id) REFERENCES TEACHER(teacher_id)
            )
        """)
        
        # ENROLLMENT_REQUEST table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ENROLLMENT_REQUEST (
                request_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT,
                course_id INT,
                status ENUM('pending', 'accepted', 'rejected') DEFAULT 'pending',
                FOREIGN KEY (student_id) REFERENCES STUDENT(student_id),
                FOREIGN KEY (course_id) REFERENCES COURSE(course_id)
            )
        """)
        
        # COURSE_ENROLLMENT table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS COURSE_ENROLLMENT (
                enrollment_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT,
                course_id INT,
                request_id INT,
                academic_year VARCHAR(20),
                semester VARCHAR(20),
                status ENUM('active', 'completed', 'dropped') DEFAULT 'active',
                FOREIGN KEY (student_id) REFERENCES STUDENT(student_id),
                FOREIGN KEY (course_id) REFERENCES COURSE(course_id),
                FOREIGN KEY (request_id) REFERENCES ENROLLMENT_REQUEST(request_id),
                UNIQUE KEY unique_enrollment (student_id, course_id, academic_year, semester)
            )
        """)
        
        # EXAM table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS EXAM (
                exam_id INT AUTO_INCREMENT PRIMARY KEY,
                course_id INT,
                teacher_id INT,
                exam_title VARCHAR(100) NOT NULL,
                exam_type VARCHAR(50),
                total_marks INT,
                duration_minutes INT,
                status ENUM('draft', 'open', 'closed') DEFAULT 'draft',
                is_supplementary BOOLEAN DEFAULT FALSE,
                parent_exam_id INT,
                FOREIGN KEY (course_id) REFERENCES COURSE(course_id),
                FOREIGN KEY (teacher_id) REFERENCES TEACHER(teacher_id),
                FOREIGN KEY (parent_exam_id) REFERENCES EXAM(exam_id)
            )
        """)
        
        # EXAM_ATTEMPT table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS EXAM_ATTEMPT (
                attempt_id INT AUTO_INCREMENT PRIMARY KEY,
                exam_id INT,
                student_id INT,
                attempt_number INT DEFAULT 1,
                status ENUM('in_progress', 'submitted', 'graded') DEFAULT 'in_progress',
                FOREIGN KEY (exam_id) REFERENCES EXAM(exam_id),
                FOREIGN KEY (student_id) REFERENCES STUDENT(student_id)
            )
        """)
        
        # EXAM_SCORE table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS EXAM_SCORE (
                score_id INT AUTO_INCREMENT PRIMARY KEY,
                attempt_id INT,
                score_obtained DECIMAL(5,2),
                max_score DECIMAL(5,2),
                score_type VARCHAR(50),
                status ENUM('pending', 'validated') DEFAULT 'pending',
                FOREIGN KEY (attempt_id) REFERENCES EXAM_ATTEMPT(attempt_id)
            )
        """)
        
        # COURSE_GRADE table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS COURSE_GRADE (
                grade_id INT AUTO_INCREMENT PRIMARY KEY,
                enrollment_id INT,
                total_score DECIMAL(5,2),
                letter_grade VARCHAR(5),
                grade_point DECIMAL(3,2),
                status ENUM('provisional', 'final', 'superseded') DEFAULT 'provisional',
                grade_version INT DEFAULT 1,
                is_final BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (enrollment_id) REFERENCES COURSE_ENROLLMENT(enrollment_id)
            )
        """)
        
        # Insert default admin if not exists
        cursor.execute("SELECT * FROM ADMINISTRATOR WHERE username = 'admin'")
        if not cursor.fetchone():
            admin_pass = hash_password('admin123')
            cursor.execute("""
                INSERT INTO ADMINISTRATOR (username, password, email, full_name) 
                VALUES ('admin', %s, 'admin@system.com', 'System Administrator')
            """, (admin_pass,))
        
        # Insert default department if not exists
        cursor.execute("SELECT * FROM DEPARTMENT WHERE department_code = 'GEN'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO DEPARTMENT (department_name, department_code, description)
                VALUES ('General Studies', 'GEN', 'General department for all students')
            """)
        
        conn.commit()
        cursor.close()
        conn.close()

# Authentication
def authenticate(username, password, role):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        hashed_pass = hash_password(password)
        
        if role == 'admin':
            cursor.execute("""
                SELECT admin_id as id, username, full_name as name, 'admin' as role
                FROM ADMINISTRATOR WHERE username = %s AND password = %s
            """, (username, hashed_pass))
        elif role == 'teacher':
            cursor.execute("""
                SELECT teacher_id as id, username, full_name as name, 'teacher' as role
                FROM TEACHER WHERE username = %s AND password = %s
            """, (username, hashed_pass))
        elif role == 'student':
            cursor.execute("""
                SELECT student_id as id, student_number as username, full_name as name, 'student' as role
                FROM STUDENT WHERE student_number = %s AND password = %s
            """, (username, hashed_pass))
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    return None

# STUDENT FUNCTIONS
def get_student_details(student_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.*, d.department_name 
            FROM STUDENT s
            LEFT JOIN DEPARTMENT d ON s.department_id = d.department_id
            WHERE s.student_id = %s
        """, (student_id,))
        student = cursor.fetchone()
        cursor.close()
        conn.close()
        return student
    return None

def get_available_courses(student_id):
    """Get courses available for enrollment"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.*, t.full_name as teacher_name, d.department_name
            FROM COURSE c
            LEFT JOIN TEACHER t ON c.teacher_id = t.teacher_id
            LEFT JOIN DEPARTMENT d ON c.department_id = d.department_id
            WHERE c.course_id NOT IN (
                SELECT course_id FROM COURSE_ENROLLMENT 
                WHERE student_id = %s AND status = 'active'
            )
            AND c.course_id NOT IN (
                SELECT course_id FROM ENROLLMENT_REQUEST 
                WHERE student_id = %s AND status = 'pending'
            )
        """, (student_id, student_id))
        courses = cursor.fetchall()
        cursor.close()
        conn.close()
        return courses
    return []

def get_student_enrollments(student_id):
    """Get student's enrolled courses"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ce.*, c.course_code, c.course_name, c.credit_hours,
                   t.full_name as teacher_name
            FROM COURSE_ENROLLMENT ce
            JOIN COURSE c ON ce.course_id = c.course_id
            LEFT JOIN TEACHER t ON c.teacher_id = t.teacher_id
            WHERE ce.student_id = %s AND ce.status = 'active'
        """, (student_id,))
        enrollments = cursor.fetchall()
        cursor.close()
        conn.close()
        return enrollments
    return []

def send_enrollment_request(student_id, course_id):
    """Send enrollment request for a course"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO ENROLLMENT_REQUEST (student_id, course_id, status)
                VALUES (%s, %s, 'pending')
            """, (student_id, course_id))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            st.error(f"Error sending request: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
    return False

def get_student_pending_requests(student_id):
    """Get student's pending enrollment requests"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT er.*, c.course_code, c.course_name, t.full_name as teacher_name
            FROM ENROLLMENT_REQUEST er
            JOIN COURSE c ON er.course_id = c.course_id
            LEFT JOIN TEACHER t ON c.teacher_id = t.teacher_id
            WHERE er.student_id = %s AND er.status = 'pending'
        """, (student_id,))
        requests = cursor.fetchall()
        cursor.close()
        conn.close()
        return requests
    return []

def get_student_exams(student_id):
    """Get available exams for student's enrolled courses"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT e.*, c.course_name, c.course_code
            FROM EXAM e
            JOIN COURSE c ON e.course_id = c.course_id
            JOIN COURSE_ENROLLMENT ce ON c.course_id = ce.course_id
            WHERE ce.student_id = %s 
            AND ce.status = 'active'
            AND e.status = 'open'
        """, (student_id,))
        exams = cursor.fetchall()
        cursor.close()
        conn.close()
        return exams
    return []

def get_student_grades(student_id):
    """Get student's grades"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT cg.*, ce.academic_year, ce.semester,
                   c.course_code, c.course_name, c.credit_hours
            FROM COURSE_GRADE cg
            JOIN COURSE_ENROLLMENT ce ON cg.enrollment_id = ce.enrollment_id
            JOIN COURSE c ON ce.course_id = c.course_id
            WHERE ce.student_id = %s AND cg.is_final = TRUE
            ORDER BY ce.academic_year, ce.semester
        """, (student_id,))
        grades = cursor.fetchall()
        cursor.close()
        conn.close()
        return grades
    return []

# TEACHER FUNCTIONS
def get_teacher_courses(teacher_id):
    """Get courses assigned to teacher"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.*, d.department_name,
                   (SELECT COUNT(*) FROM COURSE_ENROLLMENT 
                    WHERE course_id = c.course_id AND status = 'active') as enrolled_count
            FROM COURSE c
            LEFT JOIN DEPARTMENT d ON c.department_id = d.department_id
            WHERE c.teacher_id = %s
        """, (teacher_id,))
        courses = cursor.fetchall()
        cursor.close()
        conn.close()
        return courses
    return []

def get_enrollment_requests(teacher_id):
    """Get enrollment requests for teacher's courses"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT er.*, s.student_number, s.full_name as student_name,
                   c.course_code, c.course_name
            FROM ENROLLMENT_REQUEST er
            JOIN STUDENT s ON er.student_id = s.student_id
            JOIN COURSE c ON er.course_id = c.course_id
            WHERE c.teacher_id = %s AND er.status = 'pending'
        """, (teacher_id,))
        requests = cursor.fetchall()
        cursor.close()
        conn.close()
        return requests
    return []

def process_enrollment_request(request_id, action, academic_year, semester):
    """Accept or reject enrollment request"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Get request details
            cursor.execute("""
                SELECT student_id, course_id FROM ENROLLMENT_REQUEST 
                WHERE request_id = %s
            """, (request_id,))
            request = cursor.fetchone()
            
            if action == 'accept':
                # Update request status
                cursor.execute("""
                    UPDATE ENROLLMENT_REQUEST 
                    SET status = 'accepted' 
                    WHERE request_id = %s
                """, (request_id,))
                
                # Create enrollment
                cursor.execute("""
                    INSERT INTO COURSE_ENROLLMENT 
                    (student_id, course_id, request_id, academic_year, semester, status)
                    VALUES (%s, %s, %s, %s, %s, 'active')
                """, (request['student_id'], request['course_id'], request_id, 
                      academic_year, semester))
            else:
                cursor.execute("""
                    UPDATE ENROLLMENT_REQUEST 
                    SET status = 'rejected' 
                    WHERE request_id = %s
                """, (request_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            st.error(f"Error processing request: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
    return False

def get_course_students(course_id):
    """Get students enrolled in a course"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ce.enrollment_id, s.student_id, s.student_number, 
                   s.full_name, ce.academic_year, ce.semester,
                   cg.total_score, cg.letter_grade, cg.grade_point
            FROM COURSE_ENROLLMENT ce
            JOIN STUDENT s ON ce.student_id = s.student_id
            LEFT JOIN COURSE_GRADE cg ON ce.enrollment_id = cg.enrollment_id 
                AND cg.is_final = TRUE
            WHERE ce.course_id = %s AND ce.status = 'active'
        """, (course_id,))
        students = cursor.fetchall()
        cursor.close()
        conn.close()
        return students
    return []

def get_teacher_exams(teacher_id):
    """Get exams created by teacher"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT e.*, c.course_code, c.course_name
            FROM EXAM e
            JOIN COURSE c ON e.course_id = c.course_id
            WHERE e.teacher_id = %s
            ORDER BY e.exam_id DESC
        """, (teacher_id,))
        exams = cursor.fetchall()
        cursor.close()
        conn.close()
        return exams
    return []

def create_exam(course_id, teacher_id, exam_title, exam_type, total_marks, duration_minutes, is_supplementary=False, parent_exam_id=None):
    """Create a new exam"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO EXAM (course_id, teacher_id, exam_title, exam_type, 
                                  total_marks, duration_minutes, status, is_supplementary, parent_exam_id)
                VALUES (%s, %s, %s, %s, %s, %s, 'draft', %s, %s)
            """, (course_id, teacher_id, exam_title, exam_type, total_marks, 
                  duration_minutes, is_supplementary, parent_exam_id))
            exam_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            return exam_id
        except Error as e:
            st.error(f"Error creating exam: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return None
    return None

def update_exam_status(exam_id, status):
    """Update exam status (draft/open/closed)"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE EXAM SET status = %s WHERE exam_id = %s
            """, (status, exam_id))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            st.error(f"Error updating exam: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
    return False

def update_course_grade(enrollment_id, total_score):
    """Update or create course grade"""
    letter_grade, grade_point = calculate_grade(total_score)
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Check if grade exists
            cursor.execute("""
                SELECT grade_id FROM COURSE_GRADE 
                WHERE enrollment_id = %s AND is_final = TRUE
            """, (enrollment_id,))
            existing_grade = cursor.fetchone()
            
            if existing_grade:
                # Update existing grade
                cursor.execute("""
                    UPDATE COURSE_GRADE 
                    SET total_score = %s, letter_grade = %s, grade_point = %s
                    WHERE grade_id = %s
                """, (total_score, letter_grade, grade_point, existing_grade[0]))
            else:
                # Create new grade
                cursor.execute("""
                    INSERT INTO COURSE_GRADE 
                    (enrollment_id, total_score, letter_grade, grade_point, status, is_final)
                    VALUES (%s, %s, %s, %s, 'final', TRUE)
                """, (enrollment_id, total_score, letter_grade, grade_point))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            st.error(f"Error updating grade: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
    return False

# ADMIN FUNCTIONS
def add_department(dept_name, dept_code, description):
    """Add new department"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO DEPARTMENT (department_name, department_code, description)
                VALUES (%s, %s, %s)
            """, (dept_name, dept_code, description))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            st.error(f"Error adding department: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False
    return False

def get_all_departments():
    """Get all departments"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM DEPARTMENT ORDER BY department_name")
        departments = cursor.fetchall()
        cursor.close()
        conn.close()
        return departments
    return []

def add_student(student_number, username, email, password, full_name, phone, department_id):
    """Add new student"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            hashed_pass = hash_password(password)
            cursor.execute("""
                INSERT INTO STUDENT (student_number, username, email, password, 
                                     full_name, phone, department_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (student_number, username, email, hashed_pass, full_name, phone, department_id))
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

def add_teacher(username, email, password, full_name, phone, department_id):
    """Add new teacher"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            hashed_pass = hash_password(password)
            cursor.execute("""
                INSERT INTO TEACHER (username, email, password, full_name, phone, department_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (username, email, hashed_pass, full_name, phone, department_id))
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

def add_course(course_code, course_name, credit_hours, semester, department_id, teacher_id):
    """Add new course"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO COURSE (course_code, course_name, credit_hours, 
                                    semester, department_id, teacher_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (course_code, course_name, credit_hours, semester, department_id, teacher_id))
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

def get_all_students():
    """Get all students"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.*, d.department_name 
            FROM STUDENT s
            LEFT JOIN DEPARTMENT d ON s.department_id = d.department_id
            ORDER BY s.student_number
        """)
        students = cursor.fetchall()
        cursor.close()
        conn.close()
        return students
    return []

def get_all_teachers():
    """Get all teachers"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT t.*, d.department_name 
            FROM TEACHER t
            LEFT JOIN DEPARTMENT d ON t.department_id = d.department_id
            ORDER BY t.full_name
        """)
        teachers = cursor.fetchall()
        cursor.close()
        conn.close()
        return teachers
    return []

def get_all_courses():
    """Get all courses"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.*, d.department_name, t.full_name as teacher_name
            FROM COURSE c
            LEFT JOIN DEPARTMENT d ON c.department_id = d.department_id
            LEFT JOIN TEACHER t ON c.teacher_id = t.teacher_id
            ORDER BY c.semester, c.course_code
        """)
        courses = cursor.fetchall()
        cursor.close()
        conn.close()
        return courses
    return []

def get_system_stats():
    """Get system statistics"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        stats = {}
        
        cursor.execute("SELECT COUNT(*) as count FROM STUDENT")
        stats['students'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM TEACHER")
        stats['teachers'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM COURSE")
        stats['courses'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM DEPARTMENT")
        stats['departments'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM EXAM")
        stats['exams'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM ENROLLMENT_REQUEST WHERE status = 'pending'")
        stats['pending_requests'] = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()
        return stats
    return {}

# STREAMLIT UI
def main():
    st.set_page_config(page_title="Exam Result Management System", layout="wide", initial_sidebar_state="expanded")
    
    # Initialize database
    init_database()
    
    # Session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.role = None
    
    # Login Page
    if not st.session_state.logged_in:
        st.title("🎓 Examination & Results Management System")
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.subheader("🔐 Login")
            role = st.selectbox("Select Role", ["student", "teacher", "admin"])
            
            if role == "student":
                username = st.text_input("Student Number")
            else:
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
                    st.error("❌ Invalid credentials!")
    
    # STUDENT DASHBOARD
    elif st.session_state.role == "student":
        st.title("📚 Student Dashboard")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"Welcome, {st.session_state.user['name']}")
        with col2:
            if st.button("🚪 Logout"):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.session_state.role = None
                st.rerun()
        
        st.markdown("---")
        
        student_id = st.session_state.user['id']
        student = get_student_details(student_id)
        
        if student:
            # Student Info Card
            with st.container():
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Student Number", student['student_number'])
                col2.metric("Name", student['full_name'])
                col3.metric("Email", student['email'] or 'N/A')
                col4.metric("Department", student['department_name'] or 'N/A')
            
            st.markdown("---")
            
            # Tabs
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📖 My Courses", 
                "➕ Enroll in Course", 
                "⏳ Pending Requests",
                "📝 Available Exams",
                "📊 My Grades"
            ])
            
            # Tab 1: My Courses
            with tab1:
                st.subheader("📖 My Enrolled Courses")
                enrollments = get_student_enrollments(student_id)
                
                if enrollments:
                    for enrollment in enrollments:
                        with st.expander(f"{enrollment['course_code']} - {enrollment['course_name']}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Teacher:** {enrollment['teacher_name']}")
                                st.write(f"**Credits:** {enrollment['credit_hours']}")
                            with col2:
                                st.write(f"**Academic Year:** {enrollment['academic_year']}")
                                st.write(f"**Semester:** {enrollment['semester']}")
                else:
                    st.info("You are not enrolled in any courses yet.")
            
            # Tab 2: Enroll in Course
            with tab2:
                st.subheader("➕ Available Courses for Enrollment")
                available_courses = get_available_courses(student_id)
                
                if available_courses:
                    for course in available_courses:
                        with st.expander(f"{course['course_code']} - {course['course_name']}"):
                            col1, col2, col3 = st.columns([2, 2, 1])
                            with col1:
                                st.write(f"**Teacher:** {course['teacher_name']}")
                                st.write(f"**Department:** {course['department_name']}")
                            with col2:
                                st.write(f"**Credits:** {course['credit_hours']}")
                                st.write(f"**Semester:** {course['semester']}")
                            with col3:
                                if st.button("Send Request", key=f"req_{course['course_id']}"):
                                    if send_enrollment_request(student_id, course['course_id']):
                                        st.success("✅ Request sent!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to send request")
                else:
                    st.info("No courses available for enrollment.")
            
            # Tab 3: Pending Requests
            with tab3:
                st.subheader("⏳ Your Pending Enrollment Requests")
                pending_requests = get_student_pending_requests(student_id)
                
                if pending_requests:
                    for req in pending_requests:
                        with st.container():
                            st.write(f"**{req['course_code']} - {req['course_name']}**")
                            st.write(f"Teacher: {req['teacher_name']}")
                            st.write(f"Status: 🟡 Pending")
                            st.markdown("---")
                else:
                    st.info("No pending requests.")
            
            # Tab 4: Available Exams
            with tab4:
                st.subheader("📝 Available Exams")
                exams = get_student_exams(student_id)
                
                if exams:
                    for exam in exams:
                        with st.expander(f"{exam['exam_title']} - {exam['course_name']}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Course:** {exam['course_code']}")
                                st.write(f"**Type:** {exam['exam_type']}")
                                st.write(f"**Total Marks:** {exam['total_marks']}")
                            with col2:
                                st.write(f"**Duration:** {exam['duration_minutes']} minutes")
                                st.write(f"**Status:** {'🔴 Supplementary' if exam['is_supplementary'] else '🟢 Regular'}")
                            
                            st.button("Take Exam", key=f"exam_{exam['exam_id']}")
                else:
                    st.info("No exams available at the moment.")
            
            # Tab 5: My Grades
            with tab5:
                st.subheader("📊 My Grades")
                grades = get_student_grades(student_id)
                
                if grades:
                    df = pd.DataFrame(grades)
                    df = df[['course_code', 'course_name', 'credit_hours', 'total_score', 
                            'letter_grade', 'grade_point', 'academic_year', 'semester']]
                    st.dataframe(df, use_container_width=True)
                    
                    # Calculate SGPA
                    if len(grades) > 0:
                        grades_credits = [(g['grade_point'], g['credit_hours']) for g in grades]
                        sgpa = calculate_sgpa(grades_credits)
                        st.success(f"**Overall SGPA: {sgpa}**")
                else:
                    st.info("No grades available yet.")
    
    # TEACHER DASHBOARD
    elif st.session_state.role == "teacher":
        st.title("👨‍🏫 Teacher Dashboard")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"Welcome, {st.session_state.user['name']}")
        with col2:
            if st.button("🚪 Logout"):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.session_state.role = None
                st.rerun()
        
        st.markdown("---")
        
        teacher_id = st.session_state.user['id']
        
        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📚 My Courses",
            "📩 Enrollment Requests",
            "📝 Manage Exams",
            "📊 Grade Students"
        ])
        
        # Tab 1: My Courses
        with tab1:
            st.subheader("📚 My Assigned Courses")
            courses = get_teacher_courses(teacher_id)
            
            if courses:
                for course in courses:
                    with st.expander(f"{course['course_code']} - {course['course_name']}"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**Credits:** {course['credit_hours']}")
                            st.write(f"**Semester:** {course['semester']}")
                        with col2:
                            st.write(f"**Department:** {course['department_name']}")
                            st.write(f"**Enrolled Students:** {course['enrolled_count']}")
                        with col3:
                            st.write(f"**Course ID:** {course['course_id']}")
            else:
                st.info("You have no assigned courses yet.")
        
        # Tab 2: Enrollment Requests
        with tab2:
            st.subheader("📩 Pending Enrollment Requests")
            requests = get_enrollment_requests(teacher_id)
            
            if requests:
                for req in requests:
                    with st.container():
                        st.write(f"**Student:** {req['student_name']} ({req['student_number']})")
                        st.write(f"**Course:** {req['course_code']} - {req['course_name']}")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            academic_year = st.text_input("Academic Year", "2024-2025", 
                                                         key=f"year_{req['request_id']}")
                        with col2:
                            semester = st.selectbox("Semester", ["Fall", "Spring", "Summer"], 
                                                   key=f"sem_{req['request_id']}")
                        with col3:
                            if st.button("✅ Accept", key=f"accept_{req['request_id']}"):
                                if process_enrollment_request(req['request_id'], 'accept', 
                                                             academic_year, semester):
                                    st.success("Request accepted!")
                                    st.rerun()
                        with col4:
                            if st.button("❌ Reject", key=f"reject_{req['request_id']}"):
                                if process_enrollment_request(req['request_id'], 'reject', 
                                                             academic_year, semester):
                                    st.success("Request rejected!")
                                    st.rerun()
                        
                        st.markdown("---")
            else:
                st.info("No pending enrollment requests.")
        
        # Tab 3: Manage Exams
        with tab3:
            st.subheader("📝 Manage Exams")
            
            # Create New Exam
            with st.expander("➕ Create New Exam"):
                courses = get_teacher_courses(teacher_id)
                if courses:
                    course_options = {f"{c['course_code']} - {c['course_name']}": c['course_id'] 
                                     for c in courses}
                    selected_course = st.selectbox("Select Course", list(course_options.keys()))
                    course_id = course_options[selected_course]
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        exam_title = st.text_input("Exam Title")
                        exam_type = st.selectbox("Exam Type", ["Midterm", "Final", "Quiz", "CA"])
                        total_marks = st.number_input("Total Marks", min_value=1, max_value=100, value=20)
                    with col2:
                        duration = st.number_input("Duration (minutes)", min_value=10, max_value=300, value=60)
                        is_supplementary = st.checkbox("Supplementary Exam")
                        parent_exam_id = None
                        if is_supplementary:
                            parent_exam_id = st.number_input("Parent Exam ID", min_value=1)
                    
                    if st.button("Create Exam"):
                        if exam_title:
                            exam_id = create_exam(course_id, teacher_id, exam_title, exam_type, 
                                                 total_marks, duration, is_supplementary, parent_exam_id)
                            if exam_id:
                                st.success(f"✅ Exam created successfully! Exam ID: {exam_id}")
                                st.rerun()
                        else:
                            st.warning("Please fill in all required fields.")
            
            # View Existing Exams
            st.markdown("### My Exams")
            exams = get_teacher_exams(teacher_id)
            
            if exams:
                for exam in exams:
                    with st.expander(f"{exam['exam_title']} - {exam['course_name']}"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**Type:** {exam['exam_type']}")
                            st.write(f"**Marks:** {exam['total_marks']}")
                        with col2:
                            st.write(f"**Duration:** {exam['duration_minutes']} min")
                            st.write(f"**Status:** {exam['status']}")
                        with col3:
                            if exam['status'] == 'draft':
                                if st.button("Open Exam", key=f"open_{exam['exam_id']}"):
                                    if update_exam_status(exam['exam_id'], 'open'):
                                        st.success("Exam opened!")
                                        st.rerun()
                            elif exam['status'] == 'open':
                                if st.button("Close Exam", key=f"close_{exam['exam_id']}"):
                                    if update_exam_status(exam['exam_id'], 'closed'):
                                        st.success("Exam closed!")
                                        st.rerun()
            else:
                st.info("No exams created yet.")
        
        # Tab 4: Grade Students
        with tab4:
            st.subheader("📊 Grade Students")
            courses = get_teacher_courses(teacher_id)
            
            if courses:
                course_options = {f"{c['course_code']} - {c['course_name']}": c['course_id'] 
                                 for c in courses}
                selected_course = st.selectbox("Select Course", list(course_options.keys()), 
                                              key="grade_course")
                course_id = course_options[selected_course]
                
                students = get_course_students(course_id)
                
                if students:
                    st.write(f"**Total Students:** {len(students)}")
                    
                    for student in students:
                        with st.expander(f"{student['student_number']} - {student['full_name']}"):
                            col1, col2, col3 = st.columns([2, 2, 1])
                            
                            with col1:
                                st.write(f"**Academic Year:** {student['academic_year']}")
                                st.write(f"**Semester:** {student['semester']}")
                            
                            with col2:
                                current_score = student['total_score'] if student['total_score'] else 0
                                st.write(f"**Current Score:** {current_score}")
                                if student['letter_grade']:
                                    st.write(f"**Grade:** {student['letter_grade']} (GP: {student['grade_point']})")
                            
                            with col3:
                                new_score = st.number_input("Update Score", min_value=0.0, 
                                                           max_value=20.0, value=float(current_score),
                                                           key=f"score_{student['enrollment_id']}")
                                
                                if st.button("Update", key=f"btn_{student['enrollment_id']}"):
                                    if update_course_grade(student['enrollment_id'], new_score):
                                        st.success("✅ Grade updated!")
                                        st.rerun()
                else:
                    st.info("No students enrolled in this course.")
            else:
                st.info("You have no assigned courses.")
    
    # ADMIN DASHBOARD
    elif st.session_state.role == "admin":
        st.title("⚙️ Administrator Dashboard")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"Welcome, {st.session_state.user['name']}")
        with col2:
            if st.button("🚪 Logout"):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.session_state.role = None
                st.rerun()
        
        st.markdown("---")
        
        # System Statistics
        stats = get_system_stats()
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("Students", stats.get('students', 0))
        col2.metric("Teachers", stats.get('teachers', 0))
        col3.metric("Courses", stats.get('courses', 0))
        col4.metric("Departments", stats.get('departments', 0))
        col5.metric("Exams", stats.get('exams', 0))
        col6.metric("Pending Requests", stats.get('pending_requests', 0))
        
        st.markdown("---")
        
        # Tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "➕ Add Data",
            "👥 View Students",
            "👨‍🏫 View Teachers",
            "📚 View Courses",
            "🏢 View Departments"
        ])
        
        # Tab 1: Add Data
        with tab1:
            add_tabs = st.tabs(["Add Department", "Add Student", "Add Teacher", "Add Course"])
            
            # Add Department
            with add_tabs[0]:
                st.subheader("➕ Add New Department")
                col1, col2 = st.columns(2)
                with col1:
                    dept_name = st.text_input("Department Name")
                    dept_code = st.text_input("Department Code")
                with col2:
                    dept_desc = st.text_area("Description")
                
                if st.button("Add Department"):
                    if dept_name and dept_code:
                        if add_department(dept_name, dept_code, dept_desc):
                            st.success("✅ Department added successfully!")
                        else:
                            st.error("❌ Failed to add department")
                    else:
                        st.warning("Please fill in all required fields.")
            
            # Add Student
            with add_tabs[1]:
                st.subheader("➕ Add New Student")
                departments = get_all_departments()
                
                if departments:
                    col1, col2 = st.columns(2)
                    with col1:
                        student_number = st.text_input("Student Number")
                        username = st.text_input("Username", key="student_username")
                        email = st.text_input("Email", key="student_email")
                        full_name = st.text_input("Full Name", key="student_name")
                    with col2:
                        phone = st.text_input("Phone", key="student_phone")
                        dept_options = {d['department_name']: d['department_id'] for d in departments}
                        selected_dept = st.selectbox("Department", list(dept_options.keys()), 
                                                    key="student_dept")
                        dept_id = dept_options[selected_dept]
                        password = st.text_input("Password", type="password", key="student_pass")
                    
                    if st.button("Add Student"):
                        if student_number and username and full_name and password:
                            if add_student(student_number, username, email, password, 
                                         full_name, phone, dept_id):
                                st.success("✅ Student added successfully!")
                            else:
                                st.error("❌ Failed to add student")
                        else:
                            st.warning("Please fill in all required fields.")
                else:
                    st.warning("Please add departments first.")
            
            # Add Teacher
            with add_tabs[2]:
                st.subheader("➕ Add New Teacher")
                departments = get_all_departments()
                
                if departments:
                    col1, col2 = st.columns(2)
                    with col1:
                        teacher_username = st.text_input("Username", key="teacher_username")
                        teacher_email = st.text_input("Email", key="teacher_email")
                        teacher_name = st.text_input("Full Name", key="teacher_name")
                    with col2:
                        teacher_phone = st.text_input("Phone", key="teacher_phone")
                        dept_options = {d['department_name']: d['department_id'] for d in departments}
                        selected_dept = st.selectbox("Department", list(dept_options.keys()), 
                                                    key="teacher_dept")
                        dept_id = dept_options[selected_dept]
                        teacher_password = st.text_input("Password", type="password", key="teacher_pass")
                    
                    if st.button("Add Teacher"):
                        if teacher_username and teacher_name and teacher_password:
                            if add_teacher(teacher_username, teacher_email, teacher_password,
                                         teacher_name, teacher_phone, dept_id):
                                st.success("✅ Teacher added successfully!")
                            else:
                                st.error("❌ Failed to add teacher")
                        else:
                            st.warning("Please fill in all required fields.")
                else:
                    st.warning("Please add departments first.")
            
            # Add Course
            with add_tabs[3]:
                st.subheader("➕ Add New Course")
                departments = get_all_departments()
                teachers = get_all_teachers()
                
                if departments and teachers:
                    col1, col2 = st.columns(2)
                    with col1:
                        course_code = st.text_input("Course Code")
                        course_name = st.text_input("Course Name")
                        credit_hours = st.number_input("Credit Hours", min_value=1, max_value=6, value=3)
                    with col2:
                        semester = st.selectbox("Semester", ["Fall", "Spring", "Summer"])
                        dept_options = {d['department_name']: d['department_id'] for d in departments}
                        selected_dept = st.selectbox("Department", list(dept_options.keys()), 
                                                    key="course_dept")
                        dept_id = dept_options[selected_dept]
                        
                        teacher_options = {f"{t['full_name']} ({t['username']})": t['teacher_id'] 
                                         for t in teachers}
                        selected_teacher = st.selectbox("Assign Teacher", list(teacher_options.keys()))
                        teacher_id = teacher_options[selected_teacher]
                    
                    if st.button("Add Course"):
                        if course_code and course_name:
                            if add_course(course_code, course_name, credit_hours, semester, 
                                        dept_id, teacher_id):
                                st.success("✅ Course added successfully!")
                            else:
                                st.error("❌ Failed to add course")
                        else:
                            st.warning("Please fill in all required fields.")
                else:
                    st.warning("Please add departments and teachers first.")
        
        # Tab 2: View Students
        with tab2:
            st.subheader("👥 All Students")
            students = get_all_students()
            if students:
                df = pd.DataFrame(students)
                df = df[['student_number', 'full_name', 'email', 'phone', 'department_name']]
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No students found.")
        
        # Tab 3: View Teachers
        with tab3:
            st.subheader("👨‍🏫 All Teachers")
            teachers = get_all_teachers()
            if teachers:
                df = pd.DataFrame(teachers)
                df = df[['username', 'full_name', 'email', 'phone', 'department_name']]
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No teachers found.")
        
        # Tab 4: View Courses
        with tab4:
            st.subheader("📚 All Courses")
            courses = get_all_courses()
            if courses:
                df = pd.DataFrame(courses)
                df = df[['course_code', 'course_name', 'credit_hours', 'semester', 
                        'department_name', 'teacher_name']]
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No courses found.")
        
        # Tab 5: View Departments
        with tab5:
            st.subheader("🏢 All Departments")
            departments = get_all_departments()
            if departments:
                df = pd.DataFrame(departments)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No departments found.")

if __name__ == "__main__":
    main()
