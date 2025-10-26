from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import uuid
from datetime import datetime, timedelta
import sys
import json
import traceback

# Add the ml directory to the path to import our models
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ml'))

# Import models (keep same names as in your project)
from disease_prediction_integration import DiseasePredictionIntegration
from mental_health_integration import MentalHealthIntegration
from fitness_integration import FitnessIntegration

app = Flask(__name__)
app.secret_key = 'health_platform_secret_key_2024'

app.config.update(
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False,
)

# Allow both localhost forms; adjust as needed for your frontend host/port
CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": ["http://127.0.0.1:5500"]}})

# initialize ML integration objects
disease_predictor = DiseasePredictionIntegration()
mental_health_assessor = MentalHealthIntegration()
fitness_recommender = FitnessIntegration()

# Database path (project root / health.db)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'health.db')
DB_PATH = os.path.abspath(DB_PATH)

# Helper: get a connection with sensible defaults to avoid "database is locked"
def get_db_connection():
    """
    Returns a sqlite3 connection with:
      - row factory as sqlite3.Row
      - check_same_thread=False so different Flask threads can use connections safely
      - a generous timeout so SQLite waits instead of immediately throwing locked errors
    IMPORTANT: Always close the connection (use with-statement or call conn.close()).
    """
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'schema.sql')
        if not os.path.exists(schema_path):
            raise FileNotFoundError(f"Schema file not found at: {schema_path}")
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = f.read()
        # ensure idempotent CREATE TABLE statements
        schema = schema.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ")
        conn = get_db_connection()
        try:
            conn.executescript(schema)
            conn.commit()
            print(f"✅ Database initialized successfully at {DB_PATH}")
        finally:
            conn.close()
    except Exception as e:
        print("❌ Error initializing database:", e)
        traceback.print_exc()

# Utility to execute queries safely
def execute_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        if commit:
            conn.commit()
        if fetchone:
            return cur.fetchone()
        if fetchall:
            return cur.fetchall()
        # return cursor if caller needs lastrowid
        return cur
    finally:
        conn.close()

# ------------------- User Authentication ------------------- #

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json(force=True)
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        existing_user = execute_query(
            'SELECT id FROM users WHERE username = ? OR email = ?',
            (username, email),
            fetchone=True
        )
        if existing_user:
            return jsonify({'error': 'User already exists'}), 400

        password_hash = generate_password_hash(password)
        execute_query(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (username, email, password_hash),
            commit=True
        )
        return jsonify({'message': 'User created successfully'}), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(force=True)
    username = data.get('username')
    password = data.get('password')

    try:
        user = execute_query('SELECT * FROM users WHERE username = ?', (username,), fetchone=True)
        if user and check_password_hash(user['password_hash'], password):
            # create session
            session_token = str(uuid.uuid4())
            session['user_id'] = user['id']
            session['session_token'] = session_token
            session.permanent = True

            expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()

            # persist session (store expires_at as ISO string)
            execute_query(
                'INSERT INTO user_sessions (user_id, session_token, expires_at) VALUES (?, ?, ?)',
                (user['id'], session_token, expires_at),
                commit=True
            )
            # Return session token; client should send cookies too for session
            return jsonify({'message': 'Login successful', 'session_token': session_token})
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    user_id = session.get('user_id')
    session_token = session.get('session_token')

    try:
        if user_id and session_token:
            execute_query(
                'DELETE FROM user_sessions WHERE user_id = ? AND session_token = ?',
                (user_id, session_token),
                commit=True
            )
    except Exception as e:
        traceback.print_exc()
        # continue to clear session anyway
    session.clear()
    return jsonify({'message': 'Logged out successfully'})

def check_auth():
    """
    Validates session by checking that session has a user_id and session_token
    and that it exists in the user_sessions table and is not expired.
    """
    user_id = session.get('user_id')
    session_token = session.get('session_token')
    if not user_id or not session_token:
        return False
    try:
        row = execute_query(
            'SELECT * FROM user_sessions WHERE user_id = ? AND session_token = ?',
            (user_id, session_token),
            fetchone=True
        )
        if not row:
            return False
        # Optionally check expiration
        expires_at = row['expires_at']
        if expires_at:
            try:
                exp = datetime.fromisoformat(expires_at)
                if datetime.utcnow() > exp:
                    # expired
                    # remove expired session
                    execute_query(
                        'DELETE FROM user_sessions WHERE user_id = ? AND session_token = ?',
                        (user_id, session_token),
                        commit=True
                    )
                    return False
            except Exception:
                # if parsing fails, still accept for compatibility; but consider fixing stored format
                pass
        return True
    except Exception as e:
        traceback.print_exc()
        return False

# ------------------- Disease Prediction ------------------- #
@app.route('/api/health/predict-disease', methods=['POST'])
def predict_disease():
    if not check_auth():
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json(force=True)
    user_id = session.get('user_id')

    # Ensure symptoms stored as JSON string (safe for complex lists)
    symptoms_input = data.get('symptoms', []) or []
    # normalize to list of strings
    if not isinstance(symptoms_input, list):
        # if user passed a comma-separated string, split it
        if isinstance(symptoms_input, str):
            symptoms_list = [s.strip() for s in symptoms_input.split(',') if s.strip()]
        else:
            symptoms_list = []
    else:
        symptoms_list = [str(s) for s in symptoms_input]

    symptoms_json = json.dumps(symptoms_list, ensure_ascii=False)

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            '''INSERT INTO physical_health_inputs
               (user_id, age, gender, height, weight, blood_pressure_systolic,
                blood_pressure_diastolic, cholesterol_level, blood_sugar_level,
                symptoms, family_history, lifestyle_factors)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                user_id,
                data.get('age'),
                data.get('gender'),
                data.get('height'),
                data.get('weight'),
                data.get('bp_systolic'),
                data.get('bp_diastolic'),
                data.get('cholesterol'),
                data.get('blood_sugar'),
                symptoms_json,
                data.get('family_history'),
                json.dumps(data.get('lifestyle_factors')) if data.get('lifestyle_factors') is not None else None
            )
        )
        conn.commit()
        health_input_id = cur.lastrowid
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'DB error while saving health input: ' + str(e)}), 500
    finally:
        conn.close()

    try:
        prediction_result = disease_predictor.predict_disease_with_recommendations(symptoms_list)

        if 'error' in prediction_result:
            return jsonify({'error': prediction_result['error']}), 400

        # store full prediction_result as JSON string
        try:
            conn2 = get_db_connection()
            cur2 = conn2.cursor()
            cur2.execute(
                '''INSERT INTO disease_predictions
                   (user_id, health_input_id, predicted_diseases, risk_level,
                    confidence_score, recommendations)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (
                    user_id,
                    health_input_id,
                    json.dumps(prediction_result.get('predicted_disease')),  # could be list or str
                    prediction_result.get('risk_level', 'medium'),
                    float(prediction_result.get('confidence_score', 0.0)),
                    json.dumps(prediction_result)
                )
            )
            conn2.commit()
        finally:
            conn2.close()

        return jsonify(prediction_result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ------------------- Mental Health ------------------- #
@app.route('/api/mental-health/questions', methods=['GET'])
def get_mental_health_questions():
    if not check_auth():
        return jsonify({'error': 'Not authenticated'}), 401
    questions = mental_health_assessor.get_assessment_questions()
    return jsonify(questions)

@app.route('/api/mental-health/submit-quiz', methods=['POST'])
def submit_mental_health_quiz():
    if not check_auth():
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json(force=True)
    user_id = session.get('user_id')
    responses = data.get('responses', []) or []

    total_score, category_scores = mental_health_assessor.calculate_mental_health_score(responses)
    assessment_result = mental_health_assessor.get_mental_health_recommendations(total_score, category_scores)

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        for response in responses:
            question_id = response.get('question_id')
            answer = response.get('answer')
            answer_index = response.get('answer_index', 0)
            score = response.get('score', 0)
            cur.execute(
                '''INSERT INTO mental_health_responses
                   (user_id, question_id, answer, score)
                   VALUES (?, ?, ?, ?)''',
                (user_id, question_id, answer, score)
            )

        cur.execute(
            '''INSERT INTO mental_health_assessments
               (user_id, total_score, assessment_type, risk_level, recommendations)
               VALUES (?, ?, ?, ?, ?)''',
            (user_id, total_score, 'general', assessment_result.get('risk_level'),
             json.dumps(assessment_result.get('recommendations')))
        )
        conn.commit()
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'DB error while saving mental health results: ' + str(e)}), 500
    finally:
        conn.close()

    return jsonify(assessment_result)

@app.route('/api/mental-health/analyze-text', methods=['POST'])
def analyze_text_sentiment():
    if not check_auth():
        return jsonify({'error': 'Not authenticated'}), 401
    data = request.get_json(force=True)
    text = data.get('text', '')
    sentiment_result = mental_health_assessor.analyze_text_sentiment(text)
    return jsonify(sentiment_result)
@app.route('/api/health/last-prediction', methods=['GET'])
def get_last_prediction():
  if not check_auth():
    return jsonify({'error': 'Not authenticated'}), 401
  user_id = session.get('user_id')
  row = execute_query(
    'SELECT recommendations FROM disease_predictions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1',
    (user_id,),
    fetchone=True
  )
  if row:
    return jsonify(json.loads(row['recommendations']))
  return jsonify({'error': 'No previous predictions'}), 404


# ------------------- Fitness ------------------- #
@app.route('/api/fitness/profile', methods=['POST'])
def create_fitness_profile():
    if not check_auth():
        return jsonify({'error': 'Not authenticated'}), 401
    data = request.get_json(force=True)
    user_id = session.get('user_id')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            '''INSERT INTO fitness_profiles
               (user_id, age, gender, height, weight, activity_level,
                fitness_goals, medical_conditions, dietary_restrictions)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                user_id,
                data.get('age'),
                data.get('gender'),
                data.get('height'),
                data.get('weight'),
                data.get('activity_level'),
                data.get('fitness_goals'),
                json.dumps(data.get('medical_conditions')) if data.get('medical_conditions') is not None else None,
                json.dumps(data.get('dietary_restrictions')) if data.get('dietary_restrictions') is not None else None
            )
        )
        conn.commit()
        profile_id = cur.lastrowid
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'DB error while creating fitness profile: ' + str(e)}), 500
    finally:
        conn.close()

    return jsonify({'profile_id': profile_id, 'message': 'Fitness profile created'})

@app.route('/api/fitness/recommendations', methods=['POST'])
def get_fitness_recommendations():
    if not check_auth():
        return jsonify({'error': 'Not authenticated'}), 401
    data = request.get_json(force=True)
    user_id = session.get('user_id')

    try:
        fitness_recommendations = fitness_recommender.get_fitness_recommendations(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'Error generating recommendations: ' + str(e)}), 500

    # Persist diet plan and exercise routine as JSON strings for list/dict fields
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        diet_plan = fitness_recommendations.get('diet_plan', {})
        exercise_plan = fitness_recommendations.get('exercise_plan', {})

        cur.execute(
            '''INSERT INTO diet_plans
               (user_id, fitness_profile_id, plan_name, plan_type,
                daily_calories, macronutrients, meal_plan, duration_weeks)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                user_id,
                data.get('profile_id'),
                'Personalized Diet Plan',
                'Balanced',
                diet_plan.get('daily_calories'),
                json.dumps(diet_plan.get('macronutrients')) if diet_plan.get('macronutrients') is not None else None,
                json.dumps(diet_plan.get('meal_plan')) if diet_plan.get('meal_plan') is not None else None,
                diet_plan.get('duration_weeks', 4)
            )
        )

        cur.execute(
            '''INSERT INTO exercise_routines
               (user_id, fitness_profile_id, routine_name, routine_type,
                exercises, duration_minutes, difficulty_level, frequency_per_week)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                user_id,
                data.get('profile_id'),
                'Personalized Exercise Routine',
                'Mixed',
                json.dumps(exercise_plan.get('exercises')) if exercise_plan.get('exercises') is not None else None,
                exercise_plan.get('duration_minutes'),
                exercise_plan.get('intensity'),
                exercise_plan.get('frequency_per_week')
            )
        )

        conn.commit()
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'DB error while saving fitness recommendations: ' + str(e)}), 500
    finally:
        conn.close()

    return jsonify(fitness_recommendations)

# ------------------- Run App ------------------- #
if __name__ == '__main__':
    init_db()
    # Note: use_reloader=False prevents Flask from launching the app twice in debug mode,
    # which can cause SQLite locking issues when using a file DB.
    app.run(debug=True, port=5000, use_reloader=False)
