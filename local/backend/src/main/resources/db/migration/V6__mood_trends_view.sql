CREATE VIEW mood_checkin_daily_trends AS
SELECT
  owner_user_id AS user_id,
  occurred_at::date AS checkin_date,
  ROUND(AVG(mood), 1) AS avg_mood,
  ROUND(AVG(stress), 1) AS avg_stress,
  ROUND(AVG(sleep_hours), 1) AS avg_sleep_hours,
  COUNT(*) AS checkin_count
FROM mood_checkin
GROUP BY owner_user_id, occurred_at::date
ORDER BY owner_user_id, checkin_date DESC;
