import requests
import json
from bs4 import BeautifulSoup

def test_api():
    # Create session
    session = requests.Session()
    
    # First get the login page to get CSRF token
    login_page = session.get('http://localhost:5000/login')
    soup = BeautifulSoup(login_page.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'})['value']
    
    print(f"CSRF Token: {csrf_token}")
    
    # Login with CSRF token
    login_data = {
        'username': 'test',
        'password': 'test123',
        'csrf_token': csrf_token
    }
    
    login_response = session.post('http://localhost:5000/login', data=login_data)
    print(f"Login status: {login_response.status_code}")
    
    if login_response.status_code == 200:
        # Test chat API
        chat_data = {
            'user_input': 'explica algoritmul fill',
            'clasa': '10'
        }
        
        chat_response = session.post('http://localhost:5000/api/chat', data=chat_data)
        print(f"Chat API status: {chat_response.status_code}")
        
        if chat_response.status_code == 200:
            try:
                result = chat_response.json()
                print("Success!")
                print(f"Response: {result.get('response', 'No response')[:200]}...")
            except:
                print("Response is not JSON:")
                print(chat_response.text[:500])
        else:
            print("Chat API failed:")
            print(chat_response.text[:500])
    else:
        print("Login failed:")
        print(login_response.text[:500])

if __name__ == "__main__":
    test_api() 