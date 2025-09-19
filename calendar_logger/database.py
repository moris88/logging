import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_name="events.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()

    def create_table(self):
        """Creates the events table if it doesn't exist."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                is_logged INTEGER NOT NULL DEFAULT 0
            )
        """)
        self.conn.commit()

    def get_all_events(self):
        """Retrieves all events from the database as a list of dictionaries."""
        self.cursor.execute("SELECT * FROM events")
        columns = [description[0] for description in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]

    def add_event(self, name, description, start_time, end_time):
        """Adds a new event to the database."""
        self.cursor.execute("""
            INSERT INTO events (name, description, start_time, end_time)
            VALUES (?, ?, ?, ?)
        """, (name, description, start_time, end_time))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_event(self, event_id, name, description, start_time, end_time):
        """Updates an existing event."""
        self.cursor.execute("""
            UPDATE events
            SET name = ?, description = ?, start_time = ?, end_time = ?
            WHERE id = ?
        """, (name, description, start_time, end_time, event_id))
        self.conn.commit()

    def delete_event(self, event_id):
        """Deletes an event from the database."""
        self.cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
        self.conn.commit()

    def set_event_logged(self, event_id):
        """Marks an event as logged in the database."""
        self.cursor.execute("UPDATE events SET is_logged = 1 WHERE id = ?", (event_id,))
        self.conn.commit()

    def __del__(self):
        self.conn.close()
