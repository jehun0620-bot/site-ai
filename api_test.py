import requests

url = "https://jsonplaceholder.typicode.com/todos/1"

response = requests.get(url)

print("상태 코드:", response.status_code)

data = response.json()

print("제목:", data["title"])
