import shelve

SESSION_DB = "session/session_db"

def save_session(nickname):
    """Сохраняет текущую сессию в базу shelve."""
    with shelve.open(SESSION_DB) as db:
        db["nickname"] = nickname

def load_session():
    """Загружает сессию из базы shelve."""
    with shelve.open(SESSION_DB) as db:
        return db.get("nickname", None)

def clear_session():
    """Удаляет данные сессии из базы shelve."""
    with shelve.open(SESSION_DB) as db:
        if "nickname" in db:
            del db["nickname"]
