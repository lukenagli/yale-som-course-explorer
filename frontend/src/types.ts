// One row of the `courses` table (column names match the database).
export interface Course {
  id: number;
  course_id: string;
  course_number: string;
  course_title: string;
  course_category: string;
  course_type: string;
  course_session: string;
  course_description: string;
  faculty_1: string;
  faculty_1_email: string;
  faculty_bio: string;
  daytimes: string;
  timings_day: string;
  timings_start: string;
  timings_end: string;
  room: string;
  section: string;
  units: string;
  term_code: string;
  syllabus: string;
  old_syllabus: string;
}

export interface User {
  id: number;
  email: string;
  name: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  tools_used?: string[];
  loading?: boolean;
}
