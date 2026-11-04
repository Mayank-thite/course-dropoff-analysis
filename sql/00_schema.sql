-- Schema for the Open University Learning Analytics Dataset (OULAD).
-- Plain SQL that runs on PostgreSQL and DuckDB.
-- All "date" columns are days relative to the module presentation start (day 0).

DROP TABLE IF EXISTS student_vle;
DROP TABLE IF EXISTS student_assessment;
DROP TABLE IF EXISTS student_registration;
DROP TABLE IF EXISTS student_info;
DROP TABLE IF EXISTS vle;
DROP TABLE IF EXISTS assessments;
DROP TABLE IF EXISTS courses;

CREATE TABLE courses (
    code_module                TEXT NOT NULL,
    code_presentation          TEXT NOT NULL,
    module_presentation_length INTEGER,
    PRIMARY KEY (code_module, code_presentation)
);

CREATE TABLE assessments (
    code_module       TEXT NOT NULL,
    code_presentation TEXT NOT NULL,
    id_assessment     INTEGER PRIMARY KEY,
    assessment_type   TEXT,               -- TMA (tutor marked), CMA (computer marked), Exam
    date              INTEGER,            -- due day; NULL for some exams
    weight            DOUBLE PRECISION
);

CREATE TABLE vle (
    id_site           INTEGER PRIMARY KEY,
    code_module       TEXT NOT NULL,
    code_presentation TEXT NOT NULL,
    activity_type     TEXT,
    week_from         INTEGER,
    week_to           INTEGER
);

CREATE TABLE student_info (
    code_module          TEXT NOT NULL,
    code_presentation    TEXT NOT NULL,
    id_student           INTEGER NOT NULL,
    gender               TEXT,
    region               TEXT,
    highest_education    TEXT,
    imd_band             TEXT,
    age_band             TEXT,
    num_of_prev_attempts INTEGER,
    studied_credits      INTEGER,
    disability           TEXT,
    final_result         TEXT,           -- Pass, Distinction, Fail, Withdrawn
    PRIMARY KEY (code_module, code_presentation, id_student)
);

CREATE TABLE student_registration (
    code_module         TEXT NOT NULL,
    code_presentation   TEXT NOT NULL,
    id_student          INTEGER NOT NULL,
    date_registration   INTEGER,         -- usually negative (registered before start)
    date_unregistration INTEGER,         -- NULL if the student never unregistered
    PRIMARY KEY (code_module, code_presentation, id_student)
);

CREATE TABLE student_assessment (
    id_assessment  INTEGER NOT NULL,
    id_student     INTEGER NOT NULL,
    date_submitted INTEGER,
    is_banked      INTEGER,
    score          DOUBLE PRECISION
);

CREATE TABLE student_vle (
    code_module       TEXT NOT NULL,
    code_presentation TEXT NOT NULL,
    id_student        INTEGER NOT NULL,
    id_site           INTEGER NOT NULL,
    date              INTEGER NOT NULL,
    sum_click         INTEGER NOT NULL
);
