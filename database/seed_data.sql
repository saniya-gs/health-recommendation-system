-- Seed data for Health Platform
INSERT INTO mental_health_questions (question_text, category, options) VALUES
('How often do you feel anxious or worried?', 'anxiety', '["Never", "Rarely", "Sometimes", "Often", "Always"]'),
('How would you rate your overall mood today?', 'mood', '["Very poor", "Poor", "Fair", "Good", "Excellent"]'),
('How well do you sleep at night?', 'sleep', '["Very poorly", "Poorly", "Fairly well", "Well", "Very well"]'),
('How often do you feel overwhelmed by daily tasks?', 'stress', '["Never", "Rarely", "Sometimes", "Often", "Always"]'),
('How connected do you feel to others?', 'social', '["Not at all", "Slightly", "Moderately", "Quite a bit", "Extremely"]'),
('How confident do you feel about your future?', 'confidence', '["Not at all", "Slightly", "Moderately", "Quite a bit", "Extremely"]'),
('How often do you engage in activities you enjoy?', 'enjoyment', '["Never", "Rarely", "Sometimes", "Often", "Always"]'),
('How would you rate your energy levels?', 'energy', '["Very low", "Low", "Moderate", "High", "Very high"]'),
('How often do you feel sad or down?', 'depression', '["Never", "Rarely", "Sometimes", "Often", "Always"]'),
('How well do you cope with stress?', 'coping', '["Very poorly", "Poorly", "Fairly well", "Well", "Very well"]');