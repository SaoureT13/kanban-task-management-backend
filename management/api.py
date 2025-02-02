import random
from django.shortcuts import get_object_or_404
from django.template.defaulttags import querystring

from ninja import NinjaAPI, Form
from typing import List
from .schema import *
from .forms import *
from .models import Board, BoardColumn, Task

api = NinjaAPI()


def generate_hex_color():
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    return f'#{r:02x}{g:02x}{b:02x}'


@api.get("/boards", response=List[BoardSchemaOut])
def get_boards(request):
    queryset = Board.objects.all().prefetch_related("columns")
    return list(queryset)


@api.get("/columns/{board_id}", response=List[ColumnSchemaOut])
def get_columns_by_board(request, board_id: int):
    queryset = BoardColumn.objects.filter(board_id=board_id)
    return list(queryset)


@api.get("/subtasks/{task_id}", response=List[TaskSchemaOut])
def get_subtasks_by_task(request, task_id: int):
    queryset = Task.objects.filter(task_parent=task_id)
    return list(queryset)


@api.post('/boards', response=BoardSchemaOut)
def create_board(request, payload: BoardSchemaIn):
    board = Board.objects.create(name=payload.name)
    for column in payload.columns:
        color = generate_hex_color()
        BoardColumn.objects.create(name=column.name, color=color, board=board)

    return board


# Update board name and board columns(name)
@api.put("/boards/{board_id}", response=BoardSchemaOut)
def update_board(request, board_id: int, payload: BoardUpdateSchema):
    board = get_object_or_404(Board, pk=payload.id)
    board.name = payload.name.capitalize()
    board.save()

    if payload.columns:
        column_id_list = [column.id for column in payload.columns if column.id and column.id is not None]

        board.columns.exclude(id__in=column_id_list).delete()

        for column_data in payload.columns:
            if column_data.id is not None:
                column = get_object_or_404(BoardColumn, pk=column_data.id)
                column.name = column_data.name.capitalize()
                column.save()
            else:
                BoardColumn.objects.create(name=column_data.name.capitalize(), board=board, color=generate_hex_color())
    else:
        board.columns.all().delete()

    return board


@api.delete("/boards/{board_id}")
def delete_board(request, board_id: int):
    board = get_object_or_404(Board, pk=board_id)
    board.delete()

    return {"success": True}


# Mark task as completed
@api.put("/subtasks/{task_id}")
def update_subtask(request, task_id: int):
    task = get_object_or_404(Task, pk=task_id)
    task.is_completed = not task.is_completed
    task.save()

    task = get_object_or_404(Task, pk=task.task_parent_id)
    if all(subtask.is_completed for subtask in task.subtasks.all()):
        task.is_completed = True
    else:
        task.is_completed = False
    task.save()

    return {"success": True, "description": "Task successfully updated",
            "task": {"is_completed": task.is_completed, "id": task.id}}


@api.post("/tasks", response=TaskSchemaOut)
def create_task(request, payload: TaskSchemaIn):
    column = get_object_or_404(BoardColumn, pk=payload.board_column)

    if column:
        new_task = Task.objects.create(title=payload.title, board_column=column)
        if payload.description and not payload.description.lower() == "string":
            new_task.description = payload.description

        if payload.task_parent_id and payload.task_parent_id is not None:
            new_task.task_parent_id = payload.task_parent_id
        new_task.save()

        return new_task

    return api.create_response(request, {"errors": "Status(column) not found"}, status=404)


# Change column of task
@api.put("/tasks/{task_id}/columns/{column_id}", response=TaskSchemaOut)
def update_task_column(request, task_id: int, column_id: int):
    task = get_object_or_404(Task, pk=task_id)
    board_column = get_object_or_404(BoardColumn, pk=column_id)
    task.board_column = board_column
    task.save()

    return task


@api.delete("/tasks/{task_id}")
def delete_task(request, task_id: int):
    task = get_object_or_404(Task, pk=task_id)
    task.delete()

    return {"success": True}


@api.put("/tasks/{task_id}", response=TaskSchemaOut)
def update_task(request, task_id: int, payload: TaskUpdateSchema):
    task = get_object_or_404(Task, pk=task_id)
    task.title = payload.title
    if payload.description and payload.description is not None:
        task.description = payload.description
    if payload.board_column:
        board_column = get_object_or_404(BoardColumn, pk=payload.board_column)
        task.board_column = board_column

    task.save()

    return task
