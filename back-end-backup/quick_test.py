import requests

response = requests.get("http://localhost:8000/security/hash-chain/stats")
print("Status:", response.status_code)
print("Response:", response.json())
