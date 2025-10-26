-- Health Platform Database Schema (SQLite version)

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    date_of_birth DATE,
    gender TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE physical_health_inputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    age INTEGER,
    gender TEXT,
    height REAL,
    weight REAL,
    blood_pressure_systolic INTEGER,
    blood_pressure_diastolic INTEGER,
    cholesterol_level REAL,
    blood_sugar_level REAL,
    symptoms TEXT,
    family_history TEXT,
    lifestyle_factors TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE disease_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    health_input_id INTEGER NOT NULL,
    predicted_diseases TEXT,
    risk_level TEXT,
    confidence_score REAL,
    recommendations TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (health_input_id) REFERENCES physical_health_inputs(id) ON DELETE CASCADE
);

CREATE TABLE mental_health_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_text TEXT NOT NULL,
    category TEXT,
    options TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE mental_health_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    answer TEXT,
    score INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES mental_health_questions(id) ON DELETE CASCADE
);

CREATE TABLE mental_health_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    total_score INTEGER,
    assessment_type TEXT,
    risk_level TEXT,
    recommendations TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE fitness_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    age INTEGER,
    gender TEXT,
    height REAL,
    weight REAL,
    activity_level TEXT,
    fitness_goals TEXT,
    medical_conditions TEXT,
    dietary_restrictions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE diet_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    fitness_profile_id INTEGER NOT NULL,
    plan_name TEXT,
    plan_type TEXT,
    daily_calories INTEGER,
    macronutrients TEXT,
    meal_plan TEXT,
    duration_weeks INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (fitness_profile_id) REFERENCES fitness_profiles(id) ON DELETE CASCADE
);

CREATE TABLE exercise_routines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    fitness_profile_id INTEGER NOT NULL,
    routine_name TEXT,
    routine_type TEXT,
    exercises TEXT,
    duration_minutes INTEGER,
    difficulty_level TEXT,
    frequency_per_week INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (fitness_profile_id) REFERENCES fitness_profiles(id) ON DELETE CASCADE
);

CREATE TABLE mental_wellness_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    assessment_id INTEGER NOT NULL,
    recommendation_type TEXT,
    title TEXT,
    description TEXT,
    resources TEXT,
    priority TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (assessment_id) REFERENCES mental_health_assessments(id) ON DELETE CASCADE
);

CREATE TABLE combined_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    physical_health_score REAL,
    mental_health_score REAL,
    overall_health_score REAL,
    priority_recommendations TEXT,
    lifestyle_suggestions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
