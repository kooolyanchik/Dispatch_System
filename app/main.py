from fastapi import FastAPI, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, ConfigDict
from datetime import datetime, timedelta
from fastapi.responses import Response
from .database import engine, get_db, Base
from . import models
from .auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, require_role, require_active_user
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Dispatch System Pro")
templates = Jinja2Templates(directory="app/templates")


# --- Pydantic Схемы ---
class RequestCreate(BaseModel):
    title: str
    description: str
    comments_enabled: bool = True


class RequestUpdate(BaseModel):
    status: str | None = None
    dispatcher: str | None = None
    title: str | None = None
    description: str | None = None


class RequestAssign(BaseModel):
    created_by: str | None = None
    dispatcher: str | None = None


class CommentCreate(BaseModel):
    text: str


class ChatMessageCreate(BaseModel):
    text: str


class UserBlock(BaseModel):
    days: int


class UserCreate(BaseModel):
    username: str
    password: str
    role: str  # 'client', 'dispatcher', 'admin'


class RegisterUser(BaseModel):
    username: str
    password: str
    password_confirm: str


# --- Инициализация тестовых пользователей ---
@app.on_event("startup")
def startup_event():
    db = next(get_db())
    if not db.query(models.User).filter(models.User.username == "admin").first():
        db.add_all([
            models.User(username="admin", hashed_password=get_password_hash("admin123"), role="admin", is_blocked=False,
                        block_until=None),
            models.User(username="disp", hashed_password=get_password_hash("disp123"), role="dispatcher",
                        is_blocked=False, block_until=None),
            models.User(username="client", hashed_password=get_password_hash("client123"), role="client",
                        is_blocked=False, block_until=None)
        ])
        db.commit()


# --- Веб-интерфейс ---
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    requests = db.query(models.Request).all()
    return templates.TemplateResponse("dashboard.html", {"request": request, "requests": requests})


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})


# --- Аутентификация ---
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверное имя пользователя или пароль")
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}


@app.post("/register")
def register_user(data: RegisterUser, db: Session = Depends(get_db)):
    """Регистрация нового клиента. Диспетчеры и админы создаются только администратором."""
    # Валидация
    if data.password != data.password_confirm:
        raise HTTPException(status_code=400, detail="Пароли не совпадают")
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Пароль должен содержать минимум 6 символов")
    if len(data.username) < 3:
        raise HTTPException(status_code=400, detail="Логин должен содержать минимум 3 символа")

    # Проверка уникальности
    existing = db.query(models.User).filter(models.User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")

    # Создаём пользователя с ролью client
    new_user = models.User(
        username=data.username,
        hashed_password=get_password_hash(data.password),
        role="client",
        is_blocked=False,
        block_until=None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Автоматически авторизуем после регистрации
    access_token = create_access_token(data={"sub": new_user.username, "role": new_user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": new_user.role,
        "username": new_user.username,
        "message": "Регистрация успешна"
    }


@app.get("/api/me")
def get_me(current_user: models.User = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "role": current_user.role,
        "is_blocked": current_user.is_blocked,
        "block_until": current_user.block_until.strftime('%d.%m.%Y %H:%M') if current_user.block_until else None
    }


# --- API Пользователей ---
@app.get("/api/users", response_model=List[dict])
def get_users(db: Session = Depends(get_db), current_user: models.User = Depends(require_role(["admin"]))):
    return [{
        "id": u.id, "username": u.username, "role": u.role,
        "is_blocked": u.is_blocked, "block_until": str(u.block_until) if u.block_until else None
    } for u in db.query(models.User).all()]


@app.get("/api/users/list")
def get_users_list(db: Session = Depends(get_db),
                   current_user: models.User = Depends(require_role(["admin", "dispatcher"]))):
    users = db.query(models.User).all()
    return [{"username": u.username, "role": u.role} for u in users]


@app.post("/api/users")
def create_user(user_data: UserCreate, db: Session = Depends(get_db),
                current_user: models.User = Depends(require_role(["admin"]))):
    existing_user = db.query(models.User).filter(models.User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")

    new_user = models.User(
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role,
        is_blocked=False,
        block_until=None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": f"Пользователь {user_data.username} создан", "username": new_user.username,
            "role": new_user.role}


@app.put("/api/users/{user_id}/block")
def block_user(user_id: int, block_data: UserBlock, db: Session = Depends(get_db),
               current_user: models.User = Depends(require_role(["admin"]))):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_blocked = True
    user.block_until = datetime.utcnow() + timedelta(days=block_data.days)
    db.commit()
    return {"message": f"Пользователь {user.username} заблокирован на {block_data.days} дней"}


@app.put("/api/users/{user_id}/unblock")
def unblock_user(user_id: int, db: Session = Depends(get_db),
                 current_user: models.User = Depends(require_role(["admin"]))):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_blocked = False
    user.block_until = None
    db.commit()
    return {"message": f"Блокировка пользователя {user.username} снята"}


@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db),
                current_user: models.User = Depends(require_role(["admin"]))):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    db.delete(user)
    db.commit()
    return {"message": "Пользователь удален"}


# --- API Заявок ---
@app.get("/api/requests")
def get_requests(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role == "client":
        return db.query(models.Request).filter(models.Request.created_by == current_user.username).all()
    return db.query(models.Request).all()


@app.post("/api/requests")
def create_request(req: RequestCreate, db: Session = Depends(get_db),
                   current_user: models.User = Depends(require_active_user)):
    db_req = models.Request(**req.model_dump(), created_by=current_user.username)
    db.add(db_req)
    db.commit()
    db.refresh(db_req)
    return {"message": "Заявка создана", "id": db_req.id}


@app.put("/api/requests/{request_id}")
def update_request(request_id: int, update: RequestUpdate, db: Session = Depends(get_db),
                   current_user: models.User = Depends(require_active_user)):
    db_req = db.query(models.Request).filter(models.Request.id == request_id).first()
    if not db_req:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if current_user.role == "client":
        if db_req.status != "Новая" or db_req.dispatcher is not None:
            raise HTTPException(status_code=403, detail="Нельзя изменить заявку после назначения исполнителя")
        db_req.title = update.title or db_req.title
        db_req.description = update.description or db_req.description
        if update.status == "Отменена":
            db_req.status = "Отменена"
    else:
        if update.status:
            db_req.status = update.status
        if update.dispatcher:
            db_req.dispatcher = update.dispatcher
        if update.title:
            db_req.title = update.title
        if update.description:
            db_req.description = update.description

    db.commit()
    return {"message": "Заявка обновлена"}


@app.put("/api/requests/{request_id}/assign")
def assign_request(request_id: int, assign_data: RequestAssign, db: Session = Depends(get_db),
                   current_user: models.User = Depends(require_role(["admin", "dispatcher"]))):
    db_req = db.query(models.Request).filter(models.Request.id == request_id).first()
    if not db_req:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if db_req.status in ["Выполнена", "Отменена"]:
        raise HTTPException(
            status_code=403,
            detail=f"Нельзя изменить заявителя или исполнителя заявки со статусом '{db_req.status}'"
        )

    if assign_data.created_by is not None:
        if assign_data.created_by == "":
            raise HTTPException(status_code=400, detail="Заявитель не может быть пустым")
        user = db.query(models.User).filter(models.User.username == assign_data.created_by).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"Пользователь {assign_data.created_by} не найден")
        db_req.created_by = assign_data.created_by

    if assign_data.dispatcher is not None:
        if assign_data.dispatcher == "":
            db_req.dispatcher = None
        else:
            user = db.query(models.User).filter(models.User.username == assign_data.dispatcher).first()
            if not user:
                raise HTTPException(status_code=404, detail=f"Пользователь {assign_data.dispatcher} не найден")
            db_req.dispatcher = assign_data.dispatcher

    db.commit()
    return {"message": "Заявитель и/или исполнитель обновлены"}


@app.delete("/api/requests/{request_id}")
def delete_request(request_id: int, db: Session = Depends(get_db),
                   current_user: models.User = Depends(require_role(["admin", "dispatcher"]))):
    db_req = db.query(models.Request).filter(models.Request.id == request_id).first()
    if not db_req:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    db.delete(db_req)
    db.commit()
    return {"message": "Заявка удалена"}


# --- API Комментариев ---
@app.get("/api/requests/{request_id}/comments")
def get_comments(request_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    req = db.query(models.Request).filter(models.Request.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return db.query(models.Comment).filter(models.Comment.request_id == request_id).all()


@app.post("/api/requests/{request_id}/comments")
def add_comment(request_id: int, comment: CommentCreate, db: Session = Depends(get_db),
                current_user: models.User = Depends(require_active_user)):
    req = db.query(models.Request).filter(models.Request.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    db_comment = models.Comment(request_id=request_id, author=current_user.username, text=comment.text)
    db.add(db_comment)
    db.commit()
    return {"message": "Комментарий добавлен"}


# --- API Чата поддержки ---
@app.get("/api/chat/{request_id}")
def get_chat(request_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    req = db.query(models.Request).filter(models.Request.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    if current_user.role == "client" and req.created_by != current_user.username:
        raise HTTPException(status_code=403, detail="Нет доступа к чату этой заявки")

    return db.query(models.ChatMessage).filter(models.ChatMessage.request_id == request_id).order_by(
        models.ChatMessage.created_at).all()


@app.post("/api/chat/{request_id}")
def send_chat_message(request_id: int, msg: ChatMessageCreate, db: Session = Depends(get_db),
                      current_user: models.User = Depends(require_active_user)):
    req = db.query(models.Request).filter(models.Request.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    if current_user.role == "client" and req.created_by != current_user.username:
        raise HTTPException(status_code=403, detail="Нет доступа")

    db_msg = models.ChatMessage(request_id=request_id, sender=current_user.role, text=msg.text)
    db.add(db_msg)
    db.commit()
    return {"message": "Сообщение отправлено"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)