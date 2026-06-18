from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Cage(Base):
    __tablename__ = "cages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    x = Column(Float, default=0.0)
    y = Column(Float, default=0.0)
    z = Column(Float, default=0.0)
    depth = Column(Float, default=0.0)
    status = Column(String, default="normal")
    created_at = Column(DateTime, default=datetime.utcnow)

    sensor_data = relationship("SensorData", back_populates="cage")


class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    cage_id = Column(Integer, ForeignKey("cages.id"))
    temperature = Column(Float)
    salinity = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

    cage = relationship("Cage", back_populates="sensor_data")
