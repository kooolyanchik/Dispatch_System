from app.database import engine, Base, SessionLocal
from app import models
from app.auth import get_password_hash

print("Сброс базы данных...")

Base.metadata.drop_all(bind=engine)

Base.metadata.create_all(bind=engine)

db = SessionLocal()
users = [
    models.User(username="admin", hashed_password=get_password_hash("admin123"), role="admin", is_blocked=False, block_until=None),
    models.User(username="disp", hashed_password=get_password_hash("disp123"), role="dispatcher", is_blocked=False, block_until=None),
    models.User(username="client", hashed_password=get_password_hash("client123"), role="client", is_blocked=False, block_until=None)
]
db.add_all(users)
db.commit()
db.close()

print("База данных успешно пересоздана!")
print("Админ: admin / admin123")
print("Диспетчер: disp / disp123")
print("Клиент: client / client123")