import requests
import json
from requests.auth import HTTPDigestAuth  # ✅ This is httpAuth

def modify_user_status(base_url, username, password, employee_no,  begin_time=None, employee_name=None):
    url = f"{base_url}/ISAPI/AccessControl/UserInfo/Modify?format=json"




    payload = {
        "UserInfo": {
            "employeeNo": employee_no,
            "name": employee_name if employee_name else employee_no,  # Use the provided name or employee number
            "Valid": {
                "enable": True,
                "beginTime": begin_time,
                "timeType": "local"
            },
            "addUser": True,
            "checkUser": False
        }
    }

    headers = {'Content-Type': 'application/json'}

    # ✅ Use HTTPBasicAuth instead of passing tuple
    auth = HTTPDigestAuth(username, password)

    response = requests.put(
        url,
        auth=auth,
        headers=headers,
        data=json.dumps(payload)
    )

    try:
        return response.json()
    except ValueError:
        return {
            "error": "Invalid JSON response",
            "status_code": response.status_code,
            "text": response.text
        }



result = modify_user_status("http://192.168.0.82:80", "admin", "a1234@4321", "0022", "2021-05-22T00:00:00")
print(result)