from app import create_app, db
from app.models import User 

app = create_app()

@app.shell_context_processor
def make_shell_context():
    """Добавляет объекты в контекст Flask Shell для удобной отладки"""
    return {'db': db, 'User': User}

if __name__ == '__main__':
    # Создаем все таблицы, если их еще нет
    with app.app_context():
        db.create_all()
        print("Таблицы базы данных проверены/созданы.")
    
    app.run(debug=True)