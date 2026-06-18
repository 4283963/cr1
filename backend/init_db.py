import random
from datetime import datetime, timedelta
from database import engine, SessionLocal, Base
from models import Cage, SensorData

Base.metadata.create_all(bind=engine)

db = SessionLocal()

cage_configs = [
    {"name": "A1号网箱", "x": -40, "y": 0, "z": -30, "depth": 8, "status": "normal"},
    {"name": "A2号网箱", "x": -10, "y": 0, "z": -30, "depth": 10, "status": "normal"},
    {"name": "A3号网箱", "x": 20, "y": 0, "z": -30, "depth": 12, "status": "normal"},
    {"name": "B1号网箱", "x": -40, "y": 0, "z": 0, "depth": 6, "status": "normal"},
    {"name": "B2号网箱", "x": -10, "y": 0, "z": 0, "depth": 9, "status": "warning"},
    {"name": "B3号网箱", "x": 20, "y": 0, "z": 0, "depth": 11, "status": "normal"},
    {"name": "C1号网箱", "x": -40, "y": 0, "z": 30, "depth": 7, "status": "normal"},
    {"name": "C2号网箱", "x": -10, "y": 0, "z": 30, "depth": 10, "status": "normal"},
    {"name": "C3号网箱", "x": 20, "y": 0, "z": 30, "depth": 13, "status": "error"},
]

cages = []
for cfg in cage_configs:
    cage = Cage(**cfg)
    db.add(cage)
    cages.append(cage)

db.commit()

now = datetime.utcnow()
for cage in cages:
    base_temp = 18.0 + random.uniform(-2, 2)
    base_salinity = 32.0 + random.uniform(-1, 1)
    for i in range(72):
        timestamp = now - timedelta(hours=i)
        temp = base_temp + random.uniform(-1.5, 1.5)
        sal = base_salinity + random.uniform(-0.8, 0.8)
        sensor_data = SensorData(
            cage_id=cage.id,
            temperature=round(temp, 2),
            salinity=round(sal, 2),
            timestamp=timestamp
        )
        db.add(sensor_data)

db.commit()
db.close()

print("数据库初始化完成！创建了", len(cages), "个网箱")
