from fastapi.testclient import TestClient

from app import UserCreate, app


client = TestClient(app)


def test_user_creation():
    user = UserCreate(email='test@example.com', password='strongpassword')
    assert user.email == 'test@example.com'

def test_users_endpoint():
    response = client.get('/users')
    assert response.status_code == 200