"""
database.py - SQLite database setup and management for ratings
"""

import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ratings.db')


def get_db_connection():
    """Get a database connection with row factory for dict-like access"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database schema"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create ratings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            hall_name TEXT NOT NULL,
            university TEXT NOT NULL,
            meal_period TEXT NOT NULL,
            rating REAL NOT NULL CHECK(rating >= 0 AND rating <= 10),
            date TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(device_id, hall_name, university, meal_period, date)
        )
    ''')

    # Create index for efficient querying of averages
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_ratings_lookup
        ON ratings(hall_name, university, meal_period, date)
    ''')

    # Create index for user lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_ratings_user
        ON ratings(device_id, hall_name, university, meal_period, date)
    ''')

    conn.commit()
    conn.close()
    print("Database initialized successfully")


def get_rating_averages(university=None, meal_period=None, date=None):
    """
    Get average ratings for all halls in the current meal period

    Args:
        university: Filter by university (optional)
        meal_period: The meal period to query
        date: The date to query (YYYY-MM-DD format)

    Returns:
        Dict mapping hall names to {average, count}
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if university:
        cursor.execute('''
            SELECT hall_name, AVG(rating) as average, COUNT(*) as count
            FROM ratings
            WHERE university = ? AND meal_period = ? AND date = ?
            GROUP BY hall_name
        ''', (university, meal_period, date))
    else:
        cursor.execute('''
            SELECT hall_name, university, AVG(rating) as average, COUNT(*) as count
            FROM ratings
            WHERE meal_period = ? AND date = ?
            GROUP BY hall_name, university
        ''', (meal_period, date))

    rows = cursor.fetchall()
    conn.close()

    ratings = {}
    for row in rows:
        if university:
            key = row['hall_name']
        else:
            key = f"{row['university']}:{row['hall_name']}"
        ratings[key] = {
            "average": round(row['average'], 1),
            "count": row['count']
        }

    return ratings


def submit_rating(device_id, hall_name, university, meal_period, rating, date):
    """
    Submit or update a rating

    Uses UPSERT to update existing rating or insert new one
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO ratings (device_id, hall_name, university, meal_period, rating, date)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(device_id, hall_name, university, meal_period, date)
        DO UPDATE SET rating = ?, timestamp = CURRENT_TIMESTAMP
    ''', (device_id, hall_name, university, meal_period, rating, date, rating))

    conn.commit()
    conn.close()


def get_user_rating(device_id, hall_name, university, meal_period, date):
    """
    Get a user's existing rating for a hall in the current meal period

    Returns:
        Rating value if exists, None otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT rating FROM ratings
        WHERE device_id = ? AND hall_name = ? AND university = ?
        AND meal_period = ? AND date = ?
    ''', (device_id, hall_name, university, meal_period, date))

    row = cursor.fetchone()
    conn.close()

    return row['rating'] if row else None


def get_leaderboard(limit=50, meal_period=None, date=None):
    """
    Get top users by total number of ratings submitted for a meal period/date
    
    Args:
        limit: Maximum number of users to return
        meal_period: The meal period to query
        date: The date to query (YYYY-MM-DD format)
        
    Returns:
        List of dicts with rank, anonymized name, and total_ratings
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if meal_period and date:
        cursor.execute('''
            SELECT device_id, COUNT(*) as total_ratings
            FROM ratings
            WHERE meal_period = ? AND date = ?
            GROUP BY device_id
            ORDER BY total_ratings DESC
            LIMIT ?
        ''', (meal_period, date, limit))
    else:
        cursor.execute('''
            SELECT device_id, COUNT(*) as total_ratings
            FROM ratings
            GROUP BY device_id
            ORDER BY total_ratings DESC
            LIMIT ?
        ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Anonymize device IDs as "User #1", "User #2", etc.
    leaderboard = []
    for idx, row in enumerate(rows):
        leaderboard.append({
            "rank": idx + 1,
            "user_id": row['device_id'],
            "display_name": f"User #{idx + 1}",
            "total_ratings": row['total_ratings']
        })
    
    return leaderboard


def get_user_stats(device_id, meal_period=None, date=None):
    """
    Get user's rank and total ratings for a meal period/date
    
    Args:
        device_id: User's device UUID
        meal_period: The meal period to query
        date: The date to query (YYYY-MM-DD format)
        
    Returns:
        Dict with rank and total_ratings
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if meal_period and date:
        cursor.execute('''
            SELECT COUNT(*) as total
            FROM ratings
            WHERE device_id = ? AND meal_period = ? AND date = ?
        ''', (device_id, meal_period, date))
        result = cursor.fetchone()
        total_ratings = result['total'] if result else 0
        
        cursor.execute('''
            SELECT COUNT(*) + 1 as rank
            FROM (
                SELECT device_id, COUNT(*) as cnt
                FROM ratings
                WHERE meal_period = ? AND date = ?
                GROUP BY device_id
            ) AS user_counts
            WHERE cnt > (
                SELECT COUNT(*)
                FROM ratings
                WHERE device_id = ? AND meal_period = ? AND date = ?
            )
        ''', (meal_period, date, device_id, meal_period, date))
    else:
        # All-time fallback
        cursor.execute('SELECT COUNT(*) as total FROM ratings WHERE device_id = ?', (device_id,))
        result = cursor.fetchone()
        total_ratings = result['total'] if result else 0
        
        cursor.execute('''
            SELECT COUNT(*) + 1 as rank
            FROM (
                SELECT device_id, COUNT(*) as cnt
                FROM ratings
                GROUP BY device_id
            ) AS user_counts
            WHERE cnt > (SELECT COUNT(*) FROM ratings WHERE device_id = ?)
        ''', (device_id,))
    
    result = cursor.fetchone()
    rank = result['rank'] if result else 1
    conn.close()
    
    return {
        "rank": rank,
        "total_ratings": total_ratings
    }


# Initialize database when module is imported
if __name__ == "__main__":
    init_db()
    print(f"Database created at: {DATABASE_PATH}")
