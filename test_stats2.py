import urllib.request
import urllib.parse
import json

def test():
    req1 = urllib.request.Request("http://127.0.0.1:5000/login")
    req1.add_header('Content-Type', 'application/json')
    data = json.dumps({'email': 'admin345@gmail.com', 'password': 'adminpassword'}).encode('utf-8')
    try:
        resp1 = urllib.request.urlopen(req1, data=data)
        cookie = resp1.headers.get('Set-Cookie')
        session_cookie = [c for c in cookie.split(',') if 'session=' in c][0].split(';')[0]
        
        req2 = urllib.request.Request("http://127.0.0.1:5000/admin/stats")
        req2.add_header('Cookie', session_cookie)
        resp2 = urllib.request.urlopen(req2)
        print("SUCCESS:", resp2.read().decode())
    except urllib.error.HTTPError as e:
        print("HTTP ERROR:", e.code)
        print(e.read().decode())
    except Exception as e:
        print("ERROR:", e)

test()
