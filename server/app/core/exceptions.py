"""Исключения предметной области, в HTTP-ответы их переводит main.py."""


class TargetNotFoundError(Exception):
    """Сервис с таким id не найден."""


class DuplicateTargetError(Exception):
    """Сервис с таким именем уже есть."""
