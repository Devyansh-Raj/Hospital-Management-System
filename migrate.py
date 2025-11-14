"""
Migration script to add phone column to User table if it doesn't exist
Run this after updating models.py
"""
from flask import Flask
from application.database import db
from application.models import User
from sqlalchemy import inspect

def migrate_add_phone():
    """Add phone column to User table if it doesn't exist."""
    inspector = inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('user')]
    
    if 'phone' not in columns:
        print("Adding 'phone' column to User table...")
        with db.engine.connect() as conn:
            conn.execute("ALTER TABLE user ADD COLUMN phone VARCHAR(15)")
            conn.commit()
        print("✓ Phone column added successfully!")
    else:
        print("✓ Phone column already exists")

if __name__ == '__main__':
    from app import app
    with app.app_context():
        migrate_add_phone()
