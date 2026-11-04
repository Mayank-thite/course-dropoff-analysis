-- Run after loading. Speeds up the per-student joins.
CREATE INDEX idx_student_vle_student ON student_vle (code_module, code_presentation, id_student, date);
CREATE INDEX idx_student_assessment_student ON student_assessment (id_student, id_assessment);
