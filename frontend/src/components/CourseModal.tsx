import type { Course } from "../types";
import "./CourseModal.css";

interface Props {
  course: Course;
  onClose: () => void;
}

export default function CourseModal({ course, onClose }: Props) {
  const syllabus = course.syllabus || course.old_syllabus;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>✕</button>

        <div className="modal-header">
          <span className="modal-number">{course.course_number}</span>
          <h2 className="modal-title">{course.course_title}</h2>
        </div>

        <div className="modal-meta">
          {course.faculty_1 && (
            <div className="meta-row">
              <span className="meta-label">Faculty</span>
              <span>{course.faculty_1}</span>
            </div>
          )}
          {course.daytimes && (
            <div className="meta-row">
              <span className="meta-label">Schedule</span>
              <span>{course.daytimes}</span>
            </div>
          )}
          {course.room && (
            <div className="meta-row">
              <span className="meta-label">Room</span>
              <span>{course.room}</span>
            </div>
          )}
          {course.course_session && (
            <div className="meta-row">
              <span className="meta-label">Session</span>
              <span style={{ textTransform: "capitalize" }}>{course.course_session.replace("-", " ")}</span>
            </div>
          )}
          {course.units && (
            <div className="meta-row">
              <span className="meta-label">Credits</span>
              <span>{course.units}</span>
            </div>
          )}
          {course.course_category && (
            <div className="meta-row">
              <span className="meta-label">Category</span>
              <span>{course.course_category}</span>
            </div>
          )}
        </div>

        {course.course_description && (
          <div className="modal-section">
            <h4>About This Course</h4>
            <p className="modal-description">{course.course_description}</p>
          </div>
        )}

        {course.faculty_bio && (
          <div className="modal-section">
            <h4>About the Faculty</h4>
            <p className="modal-bio">{course.faculty_bio}</p>
          </div>
        )}

        {syllabus && (
          <a href={syllabus} target="_blank" rel="noreferrer" className="modal-syllabus-btn">
            View Syllabus ↗
          </a>
        )}
      </div>
    </div>
  );
}
