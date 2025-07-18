#!/usr/bin/env python3
"""
Script pentru curățenia automată a paste-urilor expirate
Poate fi rulat ca cron job pentru curățenie periodică
"""

import sqlite3
from datetime import datetime
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def cleanup_expired_pastes():
    """Șterge paste-urile expirate din baza de date"""
    try:
        conn = sqlite3.connect('infopaste.db', check_same_thread=False)
        c = conn.cursor()
        
        # Șterge paste-urile expirate
        c.execute('''
            DELETE FROM code_pastes 
            WHERE expires_at IS NOT NULL 
            AND expires_at < ?
        ''', (datetime.now().isoformat(),))
        
        deleted_count = c.rowcount
        
        # Șterge și înregistrările de vizualizări pentru paste-urile șterse
        c.execute('''
            DELETE FROM paste_views 
            WHERE paste_id NOT IN (SELECT id FROM code_pastes)
        ''')
        
        # Șterge comentariile pentru paste-urile șterse
        c.execute('''
            DELETE FROM paste_comments 
            WHERE paste_id NOT IN (SELECT id FROM code_pastes)
        ''')
        
        # Șterge explicațiile pentru paste-urile șterse
        c.execute('''
            DELETE FROM paste_explanations 
            WHERE paste_id NOT IN (SELECT id FROM code_pastes)
        ''')
        
        # Șterge aprecierile pentru paste-urile șterse
        c.execute('''
            DELETE FROM paste_likes 
            WHERE paste_id NOT IN (SELECT id FROM code_pastes)
        ''')
        
        conn.commit()
        conn.close()
        
        print(f"[{datetime.now()}] Cleanup completed: {deleted_count} expired pastes removed")
        return deleted_count
        
    except Exception as e:
        print(f"[{datetime.now()}] Error during cleanup: {e}")
        return 0

if __name__ == "__main__":
    print(f"[{datetime.now()}] Starting paste cleanup...")
    deleted_count = cleanup_expired_pastes()
    print(f"[{datetime.now()}] Cleanup finished. {deleted_count} pastes removed.")
    
    # Exit with appropriate code
    sys.exit(0 if deleted_count >= 0 else 1) 