import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_token(username: str, password: str):
    response = client.post("/login", data={"username": username, "password": password})
    return response.json()["access_token"]


def get_admin_token():
    return get_token("admin", "admin123")


def ensure_client_unblocked():
    admin_token = get_admin_token()
    client.put("/api/users/3/unblock", headers={"Authorization": f"Bearer {admin_token}"})



def test_login_success():
    """Успешный вход"""
    response = client.post("/login", data={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_fail():
    """Неверный пароль"""
    response = client.post("/login", data={"username": "admin", "password": "wrongpassword"})
    assert response.status_code == 400


def test_register_client_success():
    """Клиент может зарегистрироваться сам"""
    # Генерируем уникальный логин, чтобы тест был идемпотентным
    import time
    unique_username = f"newclient_{int(time.time())}"

    response = client.post("/register", json={
        "username": unique_username,
        "password": "newpass123",
        "password_confirm": "newpass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "client"
    assert data["username"] == unique_username
    assert "access_token" in data


def test_register_duplicate_username():
    """Нельзя зарегистрировать существующий логин"""
    response = client.post("/register", json={
        "username": "admin",
        "password": "any123",
        "password_confirm": "any123"
    })
    assert response.status_code == 400
    assert "уже существует" in response.json()["detail"]


def test_register_password_mismatch():
    """Пароли должны совпадать"""
    response = client.post("/register", json={
        "username": "testuser",
        "password": "pass123",
        "password_confirm": "different"
    })
    assert response.status_code == 400
    assert "не совпадают" in response.json()["detail"]


def test_register_short_password():
    """Пароль должен быть не короче 6 символов"""
    response = client.post("/register", json={
        "username": "testuser",
        "password": "123",
        "password_confirm": "123"
    })
    assert response.status_code == 400


def test_register_short_username():
    """Логин должен быть не короче 3 символов"""
    response = client.post("/register", json={
        "username": "ab",
        "password": "pass123",
        "password_confirm": "pass123"
    })
    assert response.status_code == 400



def test_create_request_as_client():
    """Клиент может создать заявку"""
    ensure_client_unblocked()
    token = get_token("client", "client123")
    response = client.post("/api/requests", json={
        "title": "Тест", "description": "Тест", "comments_enabled": True
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_update_request_as_client_forbidden():
    """Клиент НЕ МОЖЕТ изменить заявку после назначения диспетчера (RBAC)"""
    ensure_client_unblocked()
    token_client = get_token("client", "client123")
    token_disp = get_token("disp", "disp123")

    create_resp = client.post("/api/requests", json={
        "title": "Тест RBAC", "description": "Проверка", "comments_enabled": True
    }, headers={"Authorization": f"Bearer {token_client}"})
    assert create_resp.status_code == 200
    req_id = create_resp.json()["id"]

    client.put(f"/api/requests/{req_id}", json={
        "status": "В работе", "dispatcher": "disp"
    }, headers={"Authorization": f"Bearer {token_disp}"})

    update_resp = client.put(f"/api/requests/{req_id}", json={
        "title": "Попытка взлома"
    }, headers={"Authorization": f"Bearer {token_client}"})
    assert update_resp.status_code == 403


def test_update_request_as_dispatcher_allowed():
    """Диспетчер МОЖЕТ изменить статус заявки"""
    ensure_client_unblocked()
    token = get_token("disp", "disp123")

    create_resp = client.post("/api/requests", json={
        "title": "Тест диспетчера", "description": "...", "comments_enabled": True
    }, headers={"Authorization": f"Bearer {token}"})
    req_id = create_resp.json()["id"]

    response = client.put(f"/api/requests/{req_id}", json={
        "status": "В работе", "dispatcher": "disp"
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_delete_request_as_admin():
    """Администратор может удалить заявку"""
    token = get_admin_token()
    create_resp = client.post("/api/requests", json={
        "title": "На удаление", "description": "Тест", "comments_enabled": True
    }, headers={"Authorization": f"Bearer {token}"})
    req_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/api/requests/{req_id}", headers={"Authorization": f"Bearer {token}"})
    assert delete_resp.status_code == 200
    assert delete_resp.json()["message"] == "Заявка удалена"


def test_delete_request_as_client_forbidden():
    """Клиент НЕ может удалить заявку (Проверка RBAC)"""
    ensure_client_unblocked()
    token = get_token("client", "client123")
    response = client.delete("/api/requests/1", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403



def test_blocked_user_can_login_but_cannot_act():
    """Заблокированный пользователь может войти, но не может создавать заявки"""
    admin_token = get_admin_token()

    client.put("/api/users/3/block", json={"days": 10}, headers={"Authorization": f"Bearer {admin_token}"})

    client_token = get_token("client", "client123")
    assert client_token is not None

    get_resp = client.get("/api/requests", headers={"Authorization": f"Bearer {client_token}"})
    assert get_resp.status_code == 200

    post_resp = client.post("/api/requests", json={
        "title": "Попытка", "description": "...", "comments_enabled": True
    }, headers={"Authorization": f"Bearer {client_token}"})
    assert post_resp.status_code == 403
    assert "заблокирован" in post_resp.json()["detail"]

    client.put("/api/users/3/unblock", headers={"Authorization": f"Bearer {admin_token}"})

    post_resp_after = client.post("/api/requests", json={
        "title": "Успех", "description": "...", "comments_enabled": True
    }, headers={"Authorization": f"Bearer {client_token}"})
    assert post_resp_after.status_code == 200



def test_cannot_assign_completed_request():
    """Нельзя изменить заявителя/исполнителя выполненной заявки"""
    token_disp = get_token("disp", "disp123")

    create_resp = client.post("/api/requests", json={
        "title": "Тест блокировки", "description": "...", "comments_enabled": True
    }, headers={"Authorization": f"Bearer {token_disp}"})
    req_id = create_resp.json()["id"]

    client.put(f"/api/requests/{req_id}", json={
        "status": "Выполнена", "dispatcher": "disp"
    }, headers={"Authorization": f"Bearer {token_disp}"})

    assign_resp = client.put(f"/api/requests/{req_id}/assign", json={
        "created_by": "client"
    }, headers={"Authorization": f"Bearer {token_disp}"})

    assert assign_resp.status_code == 403
    assert "Нельзя изменить" in assign_resp.json()["detail"]


def test_chat_message_creation():
    """Отправка сообщения в чат поддержки по заявке"""
    ensure_client_unblocked()
    token = get_token("client", "client123")

    create_resp = client.post("/api/requests", json={
        "title": "Чат тест", "description": "...", "comments_enabled": True
    }, headers={"Authorization": f"Bearer {token}"})
    assert create_resp.status_code == 200, f"Создание заявки не удалось: {create_resp.json()}"
    req_id = create_resp.json()["id"]

    chat_resp = client.post(f"/api/chat/{req_id}", json={
        "text": "Здравствуйте, есть вопрос по заявке"
    }, headers={"Authorization": f"Bearer {token}"})
    assert chat_resp.status_code == 200

    get_chat_resp = client.get(f"/api/chat/{req_id}", headers={"Authorization": f"Bearer {token}"})
    assert get_chat_resp.status_code == 200
    messages = get_chat_resp.json()
    assert len(messages) == 1
    assert messages[0]["text"] == "Здравствуйте, есть вопрос по заявке"


def test_chat_integration():
    """Интеграция чата с заявкой и пользователями"""
    token = get_token("client", "client123")

    create_resp = client.post("/api/requests", json={
        "title": "Чат тест", "description": "...", "comments_enabled": True
    }, headers={"Authorization": f"Bearer {token}"})
    req_id = create_resp.json()["id"]

    client.post(f"/api/chat/{req_id}", json={"text": "Привет"},
                headers={"Authorization": f"Bearer {token}"})

    chat_resp = client.get(f"/api/chat/{req_id}",
                           headers={"Authorization": f"Bearer {token}"})
    assert len(chat_resp.json()) == 1
    assert chat_resp.json()[0]["text"] == "Привет"