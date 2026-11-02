# Database setup quick reference

1. Run `sql/01_create_database.sql` in MySQL Workbench.
2. Set `DATABASE_URL` in `.env` to `mysql+pymysql://placement_user:YOUR_URL_ENCODED_PASSWORD@localhost:3306/placement_system?charset=utf8mb4`.
3. Create tables with `python -m flask --app run.py init-db`.
4. Seed fictional data with `python seed_demo.py`.
5. Verify using `sql/03_verify_demo_data.sql`.

The web app and seed script both load `.env` and read the same `DATABASE_URL`, so both connect to the same MySQL database. Passwords are hashed in `users.password_hash`; private CSVs contain temporary demo passwords solely so testers can log in. Keep them private and change passwords after first login. Student usernames are roll numbers 100–129. Demo college-admin usernames are `admin_demo01`, `admin_demo02`, and `admin_demo03`.
