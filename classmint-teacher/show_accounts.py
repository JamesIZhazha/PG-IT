#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClassMint Default Account Viewer
View default account information automatically created by the system
"""

import sqlite3
import sys
import os

def get_default_accounts():
    """Get default account information"""
    db_path = "classmint.db"
    
    if not os.path.exists(db_path):
        print("Database file does not exist. Please run the Flask application first to initialize the database.")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("ClassMint Default Account Information")
        print("=" * 50)
        
        # Get teacher account
        teacher = cursor.execute("SELECT username FROM users WHERE username = 'admin'").fetchone()
        if teacher:
            print("Teacher Account:")
            print("   Username: admin")
            print("   Password: admin123")
            print("   Note: Automatically created on first system run")
            print()
        
        # Get student accounts
        students = cursor.execute("SELECT username FROM users WHERE username LIKE 'student%' ORDER BY username").fetchall()
        if students:
            print("Student Accounts:")
            for student in students:
                print(f"   Username: {student['username']}")
                print("   Password: student123")
            print("   Note: Automatically created on first system run")
            print()
        
        # Get shop items information
        items = cursor.execute("SELECT COUNT(*) as count FROM shop_items WHERE status = 'ACTIVE'").fetchone()
        if items and items['count'] > 0:
            print("Shop Items:")
            print(f"   Created {items['count']} default items")
            print("   Including: Apple, Book, Gift Card, Coffee, Game Time, Trophy")
            print()
        
        print("Security Tips:")
        print("   1. It is recommended to change passwords immediately after first login")
        print("   2. These default accounts should be deleted in production environment")
        print("   3. Use strong passwords and change them regularly")
        
    except Exception as e:
        print(f"Error reading database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    get_default_accounts()
