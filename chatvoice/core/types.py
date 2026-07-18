from enum import Enum


class UserRole(str, Enum):
    user = "user"
    editor = "editor"
    admin = "admin"
