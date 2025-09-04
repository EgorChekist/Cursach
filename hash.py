# Функция для хэширования пароля
import hashlib


def hash_password(password):
    hash_obj = hashlib.sha384(bytes(password, 'utf-8'))
    return hash_obj.hexdigest()
