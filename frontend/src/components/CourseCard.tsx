import type { Course } from "../types";
import "./CourseCard.css";

const CATEGORY_COLORS: Record<string, string> = {
  Core: "#00356b",
  Finance: "#286dc0",
  "Artificial Intelligence": "#7b5ea7",
  "Technology Management": "#5e8a6e",
  Marketing: "#c47c2e",
  Strategy: "#c0392b",
  Accounting: "#2c7a6b",
  Economics: "#1a6690",
  Operations: "#5c6e2b",
  "Organizational Behavior": "#7d4e8c",
  Entrepreneurship: "#b55a1e",
  "Entrepreneurship & Private Equity": "#b55a1e",
  "Asset Management": "#1e6b5e",
  Healthcare: "#2e7d6e",
  "Healthcare Management": "#2e7d6e",
  "Business & the Environment": "#3a7a3a",
  "Business & the Law": "#6b3a2e",
  "Business and the Law": "#6b3a2e",
  PhD: "#555",
  EMBA: "#3a5a8c",
  Nonprofit: "#5a6e2e",
  International: "#2e4a8c",
  "Real Estate": "#7a4a1e",
  "Political Science": "#4a2e6e",
};

const SESSION_LABEL: Record<string, string> = {
  fall: "Full Fall",
  "fall-1": "Fall 1",
  "fall-2": "Fall 2",
};

interface Props {
  course: Course;
  onClick: () => void;
}

export default function CourseCard({ course, onClick }: Props) {
  const category = course.course_category;
  const accentColor = CATEGORY_COLORS[category] ?? "#888";
  const session = SESSION_LABEL[course.course_session] ?? course.course_session;
  const syllabus = course.syllabus || course.old_syllabus;

  return (
    <article
      className="course-card"
      style={{ "--accent": accentColor } as React.CSSProperties}
      onClick={onClick}
    >
      <div className="card-accent-bar" />
      <div className="card-body">
        <div className="card-top">
          <span className="course-number">{course.course_number}</span>
          {session && <span className="session-badge">{session}</span>}
        </div>

        <h3 className="course-title">{course.course_title}</h3>

        <p className="faculty-name">
          <span className="icon">👤</span>
          {course.faculty_1 || "Staff"}
        </p>

        {course.daytimes && (
          <p className="daytimes">
            <span className="icon">🕐</span>
            {course.daytimes}
          </p>
        )}

        {course.room && (
          <p className="room">
            <span className="icon">📍</span>
            {course.room}
          </p>
        )}

        <div className="card-footer">
          <span
            className="category-badge"
            style={{ background: accentColor }}
          >
            {category || "Other"}
          </span>
          {course.units && (
            <span className="units-badge">{course.units} cr</span>
          )}
          {syllabus && (
            <a
              href={syllabus}
              target="_blank"
              rel="noreferrer"
              className="syllabus-link"
              onClick={(e) => e.stopPropagation()}
            >
              Syllabus ↗
            </a>
          )}
        </div>
      </div>
    </article>
  );
}
