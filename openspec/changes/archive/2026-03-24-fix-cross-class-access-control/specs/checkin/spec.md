## MODIFIED Requirements

### Requirement: Teacher corrects attendance

Teachers SHALL be able to correct attendance records for students in classes they manage. The `POST /api/classes/{class_id}/attendance/correct` endpoint SHALL call `can_manage_class(user, cls)` to verify the teacher has authority over the specified class. If the teacher cannot manage the class, the system SHALL return HTTP 403. Teachers with `MANAGE_ALL_CLASSES` SHALL be able to correct attendance in any class.

#### Scenario: Teacher corrects attendance in own class

- **WHEN** a teacher who manages class C calls `POST /api/classes/{class_id}/attendance/correct` for class C
- **THEN** the system SHALL proceed with the correction normally

#### Scenario: Teacher corrects attendance in another class

- **WHEN** a teacher who does NOT manage class C calls `POST /api/classes/{class_id}/attendance/correct` for class C
- **THEN** the system SHALL return HTTP 403
