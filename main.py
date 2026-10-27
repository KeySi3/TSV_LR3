from fastapi import FastAPI, HTTPException, status
import os
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

# Определение путей к директориям и локальному файлу базы данных
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = f"sqlite:///{os.path.join(BASE_DIR, 'tasks.db')}"

engine = create_engine(DATABASE)


class Base(DeclarativeBase):
    pass


class TaskDB(Base):
    __tablename__ = "tasks"

    task_id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(Integer, nullable=False)
    task_name = Column(String(120), nullable=False)


Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autoflush=False, bind=engine)
db = SessionLocal()


class TaskCreate(BaseModel):
    """
    Pydantic-модель для валидации данных при создании новой задачи.

    :param owner_id: Идентификатор владельца задачи
    :param task_name: Наименование задачи
    """
    model_config = ConfigDict(extra="forbid")
    owner_id: int = Field(gt=0)
    task_name: str = Field(min_length=1, max_length=120)


class TaskRead(BaseModel):
    """
    Pydantic-модель для валидации возвращаемых данных о задаче.

    :param task_id: Уникальный идентификатор задачи
    :param owner_id: Идентификатор владельца задачи
    :param task_name: Наименование задачи
    """
    model_config = ConfigDict(from_attributes=True)
    task_id: int = Field(gt=0)
    owner_id: int = Field(gt=0)
    task_name: str = Field(min_length=1, max_length=120)


class TaskUpdate(BaseModel):
    """
    Pydantic-модель для валидации возвращаемых данных о задаче.

    :param owner_id: Идентификатор владельца задачи
    :param task_name: Наименование задачи
    """
    model_config = ConfigDict(extra="forbid")
    owner_id: int = Field(gt=0)
    task_name: str = Field(min_length=1, max_length=120)


# Инициализация экземпляра приложения FastAPI
app = FastAPI(
    title="Task management"
)


@app.get("/tasks", response_model=List[TaskRead])
def get_all_tasks(owner_id: Optional[int] = None):
    """
    Возвращает список всех сохранённых задач с возможностью фильтрации по владельцу.

    :param owner_id: Необязательный идентификатор владельца для фильтрации
    :return: Список объектов задач TaskRead
    """
    query = db.query(TaskDB)
    if owner_id is not None:
        if owner_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Некорректные данные: ID задачи должен быть положительным числом"
            )
        query.filter(TaskDB.owner_id == owner_id)
    return query.all()


@app.get("/tasks/{task_id}", response_model=TaskRead)
def get_task_by_id(task_id: int):
    """
    Осуществляет поиск и возврат конкретной задачи по её идентификатору.

    :param task_id: Идентификатор искомой задачи
    :return: Объект найденной задачи TaskRead
    """
    task = db.query(TaskDB).filter(TaskDB.task_id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Задача с ID {task_id} не найдена"
        )
    return task


@app.post("/tasks", response_model=TaskRead)
def post_task(data: TaskCreate):
    """
    Создаёт новую задачу, присваивает уникальный идентификатор и сохраняет её в файл.

    :param data: Входные валидированные данные задачи (TaskCreate)
    :return: Созданная задача с назначенным task_id
    """
    new_task = TaskDB(**data.model_dump())
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@app.patch("/tasks/{task_id}", response_model=TaskRead)
def update_task(task_id: int, data: TaskUpdate):
    task = db.query(TaskDB).filter(TaskDB.task_id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Задача с ID {task_id} не найдена"
        )
    update_data = data.model_dump()
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не переданы данные для обновления"
        )
    for field, value in update_data.items():
        task.field = value
    db.commit()
    db.refresh()
    return task



@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    """
    Удаляет задачу из локального хранилища по её идентификатору.

    :param task_id: Идентификатор задачи, которую требуется удалить
    :return: None при успешном удалении
    """
    task = db.query(TaskDB).filter(TaskDB.task_id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Задача с ID {task_id} не найдена"
        )
    db.delete(task)
    db.commit()
    return None
