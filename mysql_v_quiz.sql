--------------------------------------------------
-- Department Table
--------------------------------------------------
CREATE TABLE department (
    dept_id INT PRIMARY KEY AUTO_INCREMENT,
    dept_name VARCHAR(100) UNIQUE NOT NULL
);

--------------------------------------------------
-- Class Table
--------------------------------------------------
CREATE TABLE class (
    class_id INT PRIMARY KEY AUTO_INCREMENT,
    class_name VARCHAR(100) NOT NULL,
    dept_id INT NOT NULL,
    CONSTRAINT fk_class_dept FOREIGN KEY (dept_id) REFERENCES department(dept_id)
);

--------------------------------------------------
-- User Table (common for all logins)
--------------------------------------------------
CREATE TABLE app_user (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student','teacher','admin') NOT NULL
);

--------------------------------------------------
-- Teacher Table (extra teacher info)
--------------------------------------------------
CREATE TABLE teacher (
    teacher_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    CONSTRAINT fk_teacher_user FOREIGN KEY (user_id) REFERENCES app_user(user_id)
);

--------------------------------------------------
-- Student Table (extra student info)
--------------------------------------------------
CREATE TABLE student (
    student_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    class_id INT NOT NULL,
    dept_id INT NOT NULL,
    CONSTRAINT fk_student_user FOREIGN KEY (user_id) REFERENCES app_user(user_id),
    CONSTRAINT fk_student_class FOREIGN KEY (class_id) REFERENCES class(class_id),
    CONSTRAINT fk_student_dept FOREIGN KEY (dept_id) REFERENCES department(dept_id)
);

--------------------------------------------------
-- Quiz Table
--------------------------------------------------
CREATE TABLE quiz (
    quiz_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    subject VARCHAR(100) NOT NULL,
    class_id INT NOT NULL,
    dept_id INT NOT NULL,
    no_of_question INT DEFAULT 10 NOT NULL,
    mark_per_question INT DEFAULT 1 NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    duration_minutes INT NOT NULL,
    created_by INT NOT NULL,
    starttime VARCHAR(10),
    endtime VARCHAR(10),
    status VARCHAR(20) DEFAULT 'active',
    total_marks INT GENERATED ALWAYS AS (no_of_question * mark_per_question) STORED,
    CONSTRAINT fk_quiz_class FOREIGN KEY (class_id) REFERENCES class(class_id),
    CONSTRAINT fk_quiz_dept FOREIGN KEY (dept_id) REFERENCES department(dept_id),
    CONSTRAINT fk_quiz_teacher FOREIGN KEY (created_by) REFERENCES teacher(teacher_id)
);

--------------------------------------------------
-- Quiz Questions Table
--------------------------------------------------
CREATE TABLE quiz_question (
    question_id INT PRIMARY KEY AUTO_INCREMENT,
    quiz_id INT NOT NULL,
    question TEXT NOT NULL,
    op1 VARCHAR(255) NOT NULL,
    op2 VARCHAR(255) NOT NULL,
    op3 VARCHAR(255) NOT NULL,
    op4 VARCHAR(255) NOT NULL,
    correct_answer ENUM('op1','op2','op3','op4') NOT NULL,
    mark INT DEFAULT 1 NOT NULL,
    CONSTRAINT fk_question_quiz FOREIGN KEY (quiz_id) REFERENCES quiz(quiz_id)
);

--------------------------------------------------
-- Result for Each Question Table
--------------------------------------------------
CREATE TABLE result_for_each_question (
    result_for_each_question_id INT PRIMARY KEY AUTO_INCREMENT,
    quiz_id INT NOT NULL,
    question_id INT NOT NULL,
    student_id INT NOT NULL,
    question VARCHAR(500) NOT NULL,
    op1 VARCHAR(100) NOT NULL,
    op2 VARCHAR(100) NOT NULL,
    op3 VARCHAR(100) NOT NULL,
    op4 VARCHAR(100) NOT NULL,
    crt_ans ENUM('op1','op2','op3','op4') NOT NULL,
    student_ans ENUM('op1','op2','op3','op4') DEFAULT NULL,
    CONSTRAINT fk_rfeq_quiz FOREIGN KEY (quiz_id) REFERENCES quiz(quiz_id),
    CONSTRAINT fk_rfeq_question FOREIGN KEY (question_id) REFERENCES quiz_question(question_id),
    CONSTRAINT fk_rfeq_student FOREIGN KEY (student_id) REFERENCES student(student_id)
);

--------------------------------------------------
-- Result for Quiz Table
--------------------------------------------------
CREATE TABLE result_for_quiz (
    result_id INT PRIMARY KEY AUTO_INCREMENT,
    quiz_id INT NOT NULL,
    student_id INT NOT NULL,
    total_mark INT DEFAULT 0,
    CONSTRAINT fk_rfq_quiz FOREIGN KEY (quiz_id) REFERENCES quiz(quiz_id),
    CONSTRAINT fk_rfq_student FOREIGN KEY (student_id) REFERENCES student(student_id)
);
