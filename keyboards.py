from maxapi.types import CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder


def get_main_menu():
    """Главное меню с кнопками."""
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="➕ Добавить задачу", payload="add_task"))
    builder.row(CallbackButton(text="📋 Список задач", payload="list_tasks"))
    return builder.as_markup()


def get_tasks_keyboard(tasks):
    """
    Создаёт inline-клавиатуру со списком задач.
    Каждая кнопка содержит текст задачи и payload вида "done_<id>".
    """
    builder = InlineKeyboardBuilder()
    for task in tasks:
        builder.row(CallbackButton(
            text=f"{task['task_text']} [❌]",
            payload=f"done_{task['id']}"
        ))
    return builder.as_markup()
