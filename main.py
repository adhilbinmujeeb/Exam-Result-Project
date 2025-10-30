import streamlit as st
import mysql.connector
from mysql.connector import Error
import pandas as pd
import hashlib
from datetime import datetime

# Database Configuration
import os

# Try to get from Streamlit secrets first, then environment variables, then defaults
try:
    DB_CONFIG = {
        'host': st.secrets.get('DB_HOST', os.getenv('MYSQLHOST')),
        'user': st.secrets.get('DB_USER', os.getenv('MYSQLUSER')),
        'password': st.secrets.get('DB_PASSWORD', os.getenv('MYSQLPASSWORD')),
        'database': st.secrets.get('DB_NAME', os.getenv('MYSQLDATABASE')),
        'port': int(st.secrets.get('DB_PORT', os.getenv('MYSQLPORT', 3306)))
    }
except:
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', 'root'),
        'database': os.getenv('DB_NAME', 'exam_management'),
        'port': int(os.getenv('DB_PORT', 3306))
    }

# Grading System based on the provided document
def calculate_grade(marks):
    """Calculate grade based on marks according to the grading system"""
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

# Initialize Database
def init_database():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role ENUM('student', 'teacher', 'admin') NOT NULL,
                name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                roll_no VARCHAR(20) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                semester INT NOT NULL,
                department VARCHAR(50) NOT NULL,
                user_id INT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                course_id VARCHAR(20) PRIMARY KEY,
                course_name VARCHAR(100) NOT NULL,
                credits INT NOT NULL,
                semester INT NOT NULL,
                teacher_id INT,
                FOREIGN KEY (teacher_id) REFERENCES users(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enrollments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                roll_no VARCHAR(20),
                course_id VARCHAR(20),
                FOREIGN KEY (roll_no) REFERENCES students(roll_no),
                FOREIGN KEY (course_id) REFERENCES courses(course_id),
                UNIQUE KEY unique_enrollment (roll_no, course_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                roll_no VARCHAR(20),
                course_id VARCHAR(20),
                marks DECIMAL(5,2),
                grade VARCHAR(2),
                grade_point INT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (roll_no) REFERENCES students(roll_no),
                FOREIGN KEY (course_id) REFERENCES courses(course_id),
                UNIQUE KEY unique_mark (roll_no, course_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semester_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                roll_no VARCHAR(20),
                semester INT,
                sgpa DECIMAL(4,2),
                cgpa DECIMAL(4,2),
                result_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (roll_no) REFERENCES students(roll_no),
                UNIQUE KEY unique_semester_result (roll_no, semester)
            )
        """)
        
        # Insert default admin if not exists
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            admin_pass = hash_password('admin123')
            cursor.execute("""
                INSERT INTO users (username, password, role, name) 
                VALUES ('admin', %s, 'admin', 'System Admin')
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
            SELECT * FROM users WHERE username = %s AND password = %s AND role = %s
        """, (username, hashed_pass, role))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    return None

# Student Functions
def get_student_details(roll_no):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE roll_no = %s", (roll_no,))
        student = cursor.fetchone()
        cursor.close()
        conn.close()
        return student
    return None

def get_student_marks(roll_no):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.course_id, c.course_name, c.credits, m.marks, m.grade, m.grade_point
            FROM marks m
            JOIN courses c ON m.course_id = c.course_id
            WHERE m.roll_no = %s
            ORDER BY c.semester, c.course_id
        """, (roll_no,))
        marks = cursor.fetchall()
        cursor.close()
        conn.close()
        return marks
    return []

def get_semester_result(roll_no, semester):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.course_id, c.course_name, c.credits, m.marks, m.grade, m.grade_point
            FROM marks m
            JOIN courses c ON m.course_id = c.course_id
            WHERE m.roll_no = %s AND c.semester = %s
        """, (roll_no, semester))
        marks = cursor.fetchall()
        cursor.close()
        conn.close()
        return marks
    return []

# Teacher Functions
def get_teacher_courses(teacher_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM courses WHERE teacher_id = %s
        """, (teacher_id,))
        courses = cursor.fetchall()
        cursor.close()
        conn.close()
        return courses
    return []

def get_course_students(course_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.roll_no, s.name, s.semester, s.department, 
                   COALESCE(m.marks, 0) as marks, m.grade, m.grade_point
            FROM enrollments e
            JOIN students s ON e.roll_no = s.roll_no
            LEFT JOIN marks m ON e.roll_no = m.roll_no AND e.course_id = m.course_id
            WHERE e.course_id = %s
            ORDER BY s.roll_no
        """, (course_id,))
        students = cursor.fetchall()
        cursor.close()
        conn.close()
        return students
    return []

def update_student_marks(roll_no, course_id, marks):
    grade, grade_point = calculate_grade(marks)
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO marks (roll_no, course_id, marks, grade, grade_point)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE marks = %s, grade = %s, grade_point = %s
        """, (roll_no, course_id, marks, grade, grade_point, marks, grade, grade_point))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    return False

# Admin Functions
def add_student(roll_no, name, semester, department, password):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Create user account
            hashed_pass = hash_password(password)
            cursor.execute("""
                INSERT INTO users (username, password, role, name)
                VALUES (%s, %s, 'student', %s)
            """, (roll_no, hashed_pass, name))
            user_id = cursor.lastrowid
            
            # Create student record
            cursor.execute("""
                INSERT INTO students (roll_no, name, semester, department, user_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (roll_no, name, semester, department, user_id))
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

def add_teacher(username, name, password):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            hashed_pass = hash_password(password)
            cursor.execute("""
                INSERT INTO users (username, password, role, name)
                VALUES (%s, %s, 'teacher', %s)
            """, (username, hashed_pass, name))
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

def add_course(course_id, course_name, credits, semester, teacher_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO courses (course_id, course_name, credits, semester, teacher_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (course_id, course_name, credits, semester, teacher_id))
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

def enroll_student(roll_no, course_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO enrollments (roll_no, course_id)
                VALUES (%s, %s)
            """, (roll_no, course_id))
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
        cursor.execute("SELECT id, name, username FROM users WHERE role = 'teacher'")
        teachers = cursor.fetchall()
        cursor.close()
        conn.close()
        return teachers
    return []

def get_all_students():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students ORDER BY roll_no")
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
            SELECT c.*, u.name as teacher_name 
            FROM courses c
            LEFT JOIN users u ON c.teacher_id = u.id
            ORDER BY c.semester, c.course_id
        """)
        courses = cursor.fetchall()
        cursor.close()
        conn.close()
        return courses
    return []

def generate_semester_results(semester):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        # Get all students in this semester
        cursor.execute("""
            SELECT DISTINCT s.roll_no, s.name
            FROM students s
            WHERE s.semester = %s
        """, (semester,))
        students = cursor.fetchall()
        
        for student in students:
            roll_no = student['roll_no']
            # Get all marks for this student in this semester
            cursor.execute("""
                SELECT m.grade_point, c.credits
                FROM marks m
                JOIN courses c ON m.course_id = c.course_id
                WHERE m.roll_no = %s AND c.semester = %s
            """, (roll_no, semester))
            results = cursor.fetchall()
            
            if results:
                grades_credits = [(r['grade_point'], r['credits']) for r in results]
                sgpa = calculate_sgpa(grades_credits)
                
                # Calculate CGPA (average of all semester SGPAs up to current semester)
                cursor.execute("""
                    SELECT AVG(sgpa) as cgpa FROM semester_results 
                    WHERE roll_no = %s AND semester <= %s
                """, (roll_no, semester))
                cgpa_result = cursor.fetchone()
                cgpa = cgpa_result['cgpa'] if cgpa_result['cgpa'] else sgpa
                
                # Insert or update semester result
                cursor.execute("""
                    INSERT INTO semester_results (roll_no, semester, sgpa, cgpa)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE sgpa = %s, cgpa = %s
                """, (roll_no, semester, sgpa, cgpa, sgpa, cgpa))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    return False

# Streamlit UI
def main():
    st.set_page_config(page_title="Exam Result Management System", layout="wide")
    
    # Initialize database
    init_database()
    
    # Session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.role = None
    
    # Login Page
    if not st.session_state.logged_in:
        st.title("🎓 Exam Result Management System")
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.subheader("Login")
            role = st.selectbox("Select Role", ["student", "teacher", "admin"])
            
            if role == "student":
                username = st.text_input("Roll Number")
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
                    st.error("Invalid credentials!")
    
    # Student Dashboard
    elif st.session_state.role == "student":
        st.title("📚 Student Dashboard")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"Welcome, {st.session_state.user['name']}")
        with col2:
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.session_state.role = None
                st.rerun()
        
        st.markdown("---")
        
        roll_no = st.session_state.user['username']
        student = get_student_details(roll_no)
        
        if student:
            # Student Details
            st.subheader("📋 Student Details")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Roll Number", student['roll_no'])
            col2.metric("Name", student['name'])
            col3.metric("Semester", student['semester'])
            col4.metric("Department", student['department'])
            
            st.markdown("---")
            
            # Tabs for different views
            tab1, tab2 = st.tabs(["📊 All Marks", "📈 Semester Results"])
            
            with tab1:
                st.subheader("Your Marks")
                marks = get_student_marks(roll_no)
                if marks:
                    df = pd.DataFrame(marks)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No marks available yet.")
            
            with tab2:
                st.subheader("Semester-wise Results")
                semester = st.selectbox("Select Semester", range(1, 9))
                
                if st.button("View Result"):
                    semester_marks = get_semester_result(roll_no, semester)
                    if semester_marks:
                        df = pd.DataFrame(semester_marks)
                        st.dataframe(df, use_container_width=True)
                        
                        # Calculate SGPA
                        grades_credits = [(m['grade_point'], m['credits']) for m in semester_marks]
                        sgpa = calculate_sgpa(grades_credits)
                        
                        st.success(f"**SGPA for Semester {semester}: {sgpa}**")
                    else:
                        st.warning(f"No results available for Semester {semester}")
    
    # Teacher Dashboard
    elif st.session_state.role == "teacher":
        st.title("👨‍🏫 Teacher Dashboard")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"Welcome, {st.session_state.user['name']}")
        with col2:
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.session_state.role = None
                st.rerun()
        
        st.markdown("---")
        
        teacher_id = st.session_state.user['id']
        courses = get_teacher_courses(teacher_id)
        
        if courses:
            st.subheader("📚 Your Courses")
            course_names = [f"{c['course_id']} - {c['course_name']}" for c in courses]
            selected_course = st.selectbox("Select Course", course_names)
            
            if selected_course:
                course_id = selected_course.split(" - ")[0]
                
                st.markdown("---")
                st.subheader("👥 Students Enrolled")
                
                students = get_course_students(course_id)
                if students:
                    st.write(f"Total Students: {len(students)}")
                    
                    # Display and update marks
                    for student in students:
                        with st.expander(f"{student['roll_no']} - {student['name']}"):
                            col1, col2, col3 = st.columns([2, 2, 1])
                            
                            with col1:
                                st.write(f"**Department:** {student['department']}")
                                st.write(f"**Semester:** {student['semester']}")
                            
                            with col2:
                                current_marks = student['marks'] if student['marks'] else 0
                                st.write(f"**Current Marks:** {current_marks}")
                                if student['grade']:
                                    st.write(f"**Grade:** {student['grade']} (GP: {student['grade_point']})")
                            
                            with col3:
                                new_marks = st.number_input(
                                    "Update Marks",
                                    min_value=0.0,
                                    max_value=100.0,
                                    value=float(current_marks),
                                    key=f"marks_{student['roll_no']}"
                                )
                                
                                if st.button("Update", key=f"btn_{student['roll_no']}"):
                                    if update_student_marks(student['roll_no'], course_id, new_marks):
                                        st.success("Marks updated successfully!")
                                        st.rerun()
                                    else:
                                        st.error("Failed to update marks")
                else:
                    st.info("No students enrolled in this course.")
        else:
            st.info("You are not assigned to any courses yet.")
    
    # Admin Dashboard
    elif st.session_state.role == "admin":
        st.title("⚙️ Admin Dashboard")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"Welcome, {st.session_state.user['name']}")
        with col2:
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.session_state.role = None
                st.rerun()
        
        st.markdown("---")
        
        tabs = st.tabs(["➕ Add Data", "👥 View Students", "📚 View Courses", "📊 Generate Results"])
        
        # Add Data Tab
        with tabs[0]:
            add_tab = st.tabs(["Add Student", "Add Teacher", "Add Course", "Enroll Student"])
            
            with add_tab[0]:
                st.subheader("Add New Student")
                col1, col2 = st.columns(2)
                with col1:
                    roll_no = st.text_input("Roll Number")
                    name = st.text_input("Student Name")
                with col2:
                    semester = st.number_input("Semester", min_value=1, max_value=8, value=1)
                    department = st.text_input("Department")
                password = st.text_input("Password", type="password", key="student_pass")
                
                if st.button("Add Student"):
                    if roll_no and name and department and password:
                        if add_student(roll_no, name, semester, department, password):
                            st.success(f"Student {name} added successfully!")
                        else:
                            st.error("Failed to add student")
                    else:
                        st.warning("Please fill all fields")
            
            with add_tab[1]:
                st.subheader("Add New Teacher")
                col1, col2 = st.columns(2)
                with col1:
                    teacher_username = st.text_input("Username")
                with col2:
                    teacher_name = st.text_input("Teacher Name")
                teacher_password = st.text_input("Password", type="password", key="teacher_pass")
                
                if st.button("Add Teacher"):
                    if teacher_username and teacher_name and teacher_password:
                        if add_teacher(teacher_username, teacher_name, teacher_password):
                            st.success(f"Teacher {teacher_name} added successfully!")
                        else:
                            st.error("Failed to add teacher")
                    else:
                        st.warning("Please fill all fields")
            
            with add_tab[2]:
                st.subheader("Add New Course")
                col1, col2 = st.columns(2)
                with col1:
                    course_id = st.text_input("Course ID")
                    course_name = st.text_input("Course Name")
                    credits = st.number_input("Credits", min_value=1, max_value=6, value=3)
                with col2:
                    course_semester = st.number_input("Semester", min_value=1, max_value=8, value=1, key="course_sem")
                    teachers = get_all_teachers()
                    if teachers:
                        teacher_options = {f"{t['name']} ({t['username']})": t['id'] for t in teachers}
                        selected_teacher = st.selectbox("Assign Teacher", list(teacher_options.keys()))
                        teacher_id = teacher_options[selected_teacher]
                    else:
                        st.warning("No teachers available. Please add teachers first.")
                        teacher_id = None
                
                if st.button("Add Course"):
                    if course_id and course_name and teacher_id:
                        if add_course(course_id, course_name, credits, course_semester, teacher_id):
                            st.success(f"Course {course_name} added successfully!")
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
                        student_options = {f"{s['roll_no']} - {s['name']}": s['roll_no'] for s in students}
                        selected_student = st.selectbox("Select Student", list(student_options.keys()))
                        enroll_roll_no = student_options[selected_student]
                    
                    with col2:
                        course_options = {f"{c['course_id']} - {c['course_name']}": c['course_id'] for c in courses}
                        selected_course = st.selectbox("Select Course", list(course_options.keys()))
                        enroll_course_id = course_options[selected_course]
                    
                    if st.button("Enroll Student"):
                        if enroll_student(enroll_roll_no, enroll_course_id):
                            st.success("Student enrolled successfully!")
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
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No students found.")
        
        # View Courses Tab
        with tabs[2]:
            st.subheader("All Courses")
            courses = get_all_courses()
            if courses:
                df = pd.DataFrame(courses)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No courses found.")
        
        # Generate Results Tab
        with tabs[3]:
            st.subheader("Generate Semester Results")
            result_semester = st.number_input("Select Semester", min_value=1, max_value=8, value=1, key="result_sem")
            
            if st.button("Generate Results"):
                if generate_semester_results(result_semester):
                    st.success(f"Results generated successfully for Semester {result_semester}!")
                else:
                    st.error("Failed to generate results")
            
            st.markdown("---")
            st.subheader("View Semester Results")
            view_semester = st.number_input("Select Semester", min_value=1, max_value=8, value=1, key="view_sem")
            
            if st.button("View Results"):
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("""
                        SELECT s.roll_no, s.name, s.department, sr.sgpa, sr.cgpa, sr.result_date
                        FROM semester_results sr
                        JOIN students s ON sr.roll_no = s.roll_no
                        WHERE sr.semester = %s
                        ORDER BY sr.sgpa DESC
                    """, (view_semester,))
                    results = cursor.fetchall()
                    cursor.close()
                    conn.close()
                    
                    if results:
                        df = pd.DataFrame(results)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info(f"No results available for Semester {view_semester}")

if __name__ == "__main__":
    main()
