## ADDED Requirements

### Requirement: Feed post deletion requires class management permission

The system SHALL verify that a teacher attempting to delete a feed post can manage the class the post belongs to. When a non-owner user calls `DELETE /posts/{post_id}`, the system SHALL load the post, retrieve its `class_id`, and call `can_manage_class(user, cls)`. If the user cannot manage the class AND is not the post owner, the system SHALL return HTTP 403. Post owners SHALL always be able to delete their own posts regardless of class management permissions.

#### Scenario: Teacher deletes post in own class

- **WHEN** a teacher who manages class C calls `DELETE /posts/{post_id}` for a post in class C
- **THEN** the system SHALL delete the post and return HTTP 204

#### Scenario: Teacher deletes post in another class

- **WHEN** a teacher who does NOT manage class C calls `DELETE /posts/{post_id}` for a post in class C
- **THEN** the system SHALL return HTTP 403

#### Scenario: Post owner deletes own post

- **WHEN** a student who owns a post calls `DELETE /posts/{post_id}`
- **THEN** the system SHALL delete the post regardless of class management permissions

#### Scenario: Class manager deletes any post

- **WHEN** a user with `MANAGE_ALL_CLASSES` calls `DELETE /posts/{post_id}` for a post in any class
- **THEN** the system SHALL delete the post and return HTTP 204
