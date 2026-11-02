-- Run in MySQL Workbench as an account allowed to create databases/users.
-- Replace the example password before running. Keep it identical to DATABASE_URL in .env.
CREATE DATABASE IF NOT EXISTS placement_system
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'placement_user'@'localhost' IDENTIFIED BY 'Replace-With-Your-Strong-DB-Password-2026!';
GRANT ALL PRIVILEGES ON placement_system.* TO 'placement_user'@'localhost';
FLUSH PRIVILEGES;
-- Table creation is managed by the Flask SQLAlchemy models:
-- .venv\Scripts\python.exe -m flask --app run.py init-db
