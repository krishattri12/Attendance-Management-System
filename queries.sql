-- Useful SQL queries to show in your viva / report

-- 1. Attendance percentage of every student in every course
SELECT * FROM v_attendance_summary;

-- 2. Defaulters (below 75%)
SELECT roll_no, student_name, course_name, percentage
FROM v_attendance_summary
WHERE percentage < 75
ORDER BY percentage;

-- 3. Students enrolled in a course (JOIN)
SELECT s.roll_no, s.name
FROM student s JOIN enrollment e ON s.student_id = e.student_id
WHERE e.course_id = 1;

-- 4. Number of students per department (GROUP BY)
SELECT d.dept_name, COUNT(s.student_id) AS total_students
FROM department d LEFT JOIN student s ON s.dept_id = d.dept_id
GROUP BY d.dept_id;

-- 5. Day-wise absentees for a course
SELECT a.att_date, s.name
FROM attendance a JOIN student s ON s.student_id = a.student_id
WHERE a.course_id = 1 AND a.status = 'A'
ORDER BY a.att_date;

-- 6. Students with the best attendance (subquery)
SELECT name FROM student WHERE student_id IN (
  SELECT student_id FROM v_attendance_summary
  GROUP BY student_id HAVING AVG(percentage) > 90);

-- 7. Courses taught by each teacher
SELECT t.name AS teacher, GROUP_CONCAT(c.course_name, ', ') AS courses
FROM teacher t LEFT JOIN course c ON c.teacher_id = t.teacher_id
GROUP BY t.teacher_id;
