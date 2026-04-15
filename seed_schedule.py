from app import create_app, db
from app.models import User, ScheduleSlot
from datetime import datetime, timedelta

app = create_app()

with app.app_context():
    # Найдем первого врача
    doctor = User.query.filter_by(role='doctor').first()
    if not doctor:
        print("Нет врачей в базе. Создайте врача через регистрацию и смену роли в БД.")
    else:
        print(f"Генерация расписания для врача: {doctor.username}")
        
        # Очистим старое расписание этого врача
        ScheduleSlot.query.filter_by(doctor_id=doctor.id).delete()
        
        # Создадим слоты на сегодня и завтра каждые 30 минут с 9:00 до 18:00
        start_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        
        for day_offset in range(3): # На 3 дня вперед
            current_day = start_date + timedelta(days=day_offset)
            for hour in range(9, 18):
                for minute in [0, 30]:
                    slot_start = current_day.replace(hour=hour, minute=minute)
                    slot_end = slot_start + timedelta(minutes=30)
                    
                    slot = ScheduleSlot(
                        doctor_id=doctor.id,
                        start_time=slot_start,
                        end_time=slot_end,
                        is_available=True
                    )
                    db.session.add(slot)
        
        db.session.commit()
        print("Расписание успешно создано!")