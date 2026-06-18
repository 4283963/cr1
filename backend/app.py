from flask import Flask, jsonify, request, g
from flask_cors import CORS
from sqlalchemy import desc
from datetime import datetime, timedelta
import random
from database import SessionLocal, engine, Base
from models import Cage, SensorData

Base.metadata.create_all(bind=engine)

app = Flask(__name__)
CORS(app)


@app.before_request
def before_request():
    g.db = SessionLocal()


@app.teardown_request
def teardown_request(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def get_db():
    return g.db


@app.route("/api/cages", methods=["GET"])
def get_cages():
    db = get_db()
    cages = db.query(Cage).all()
    result = []
    for cage in cages:
        latest_data = db.query(SensorData).filter(
            SensorData.cage_id == cage.id
        ).order_by(desc(SensorData.timestamp)).first()

        result.append({
            "id": cage.id,
            "name": cage.name,
            "x": cage.x,
            "y": cage.y,
            "z": cage.z,
            "depth": cage.depth,
            "status": cage.status,
            "temperature": latest_data.temperature if latest_data else None,
            "salinity": latest_data.salinity if latest_data else None,
            "lastUpdate": latest_data.timestamp.isoformat() if latest_data else None,
        })
    return jsonify(result)


@app.route("/api/cages/<int:cage_id>", methods=["GET"])
def get_cage_detail(cage_id):
    db = get_db()
    cage = db.query(Cage).filter(Cage.id == cage_id).first()
    if not cage:
        return jsonify({"error": "网箱不存在"}), 404

    latest_data = db.query(SensorData).filter(
        SensorData.cage_id == cage.id
    ).order_by(desc(SensorData.timestamp)).first()

    return jsonify({
        "id": cage.id,
        "name": cage.name,
        "x": cage.x,
        "y": cage.y,
        "z": cage.z,
        "depth": cage.depth,
        "status": cage.status,
        "temperature": latest_data.temperature if latest_data else None,
        "salinity": latest_data.salinity if latest_data else None,
        "lastUpdate": latest_data.timestamp.isoformat() if latest_data else None,
    })


@app.route("/api/cages/<int:cage_id>/history", methods=["GET"])
def get_cage_history(cage_id):
    db = get_db()
    hours = request.args.get("hours", default=24, type=int)

    cage = db.query(Cage).filter(Cage.id == cage_id).first()
    if not cage:
        return jsonify({"error": "网箱不存在"}), 404

    time_threshold = datetime.utcnow() - timedelta(hours=hours)
    history_data = db.query(SensorData).filter(
        SensorData.cage_id == cage_id,
        SensorData.timestamp >= time_threshold
    ).order_by(SensorData.timestamp).all()

    result = []
    for data in history_data:
        result.append({
            "timestamp": data.timestamp.isoformat(),
            "temperature": data.temperature,
            "salinity": data.salinity,
        })

    return jsonify({
        "cageId": cage_id,
        "cageName": cage.name,
        "data": result,
    })


@app.route("/api/sensor/update", methods=["POST"])
def update_sensor_data():
    db = get_db()
    data = request.json
    cage_id = data.get("cage_id")
    temperature = data.get("temperature")
    salinity = data.get("salinity")

    cage = db.query(Cage).filter(Cage.id == cage_id).first()
    if not cage:
        return jsonify({"error": "网箱不存在"}), 404

    sensor_data = SensorData(
        cage_id=cage_id,
        temperature=temperature,
        salinity=salinity,
        timestamp=datetime.utcnow()
    )
    db.add(sensor_data)
    db.commit()

    return jsonify({"message": "数据更新成功", "id": sensor_data.id})


@app.route("/api/sensor/random-update", methods=["POST"])
def random_update():
    db = get_db()
    cages = db.query(Cage).all()

    for cage in cages:
        latest_data = db.query(SensorData).filter(
            SensorData.cage_id == cage.id
        ).order_by(desc(SensorData.timestamp)).first()

        base_temp = latest_data.temperature if latest_data else 18.0
        base_sal = latest_data.salinity if latest_data else 32.0

        new_temp = round(base_temp + random.uniform(-0.3, 0.3), 2)
        new_sal = round(base_sal + random.uniform(-0.2, 0.2), 2)

        sensor_data = SensorData(
            cage_id=cage.id,
            temperature=new_temp,
            salinity=new_sal,
            timestamp=datetime.utcnow()
        )
        db.add(sensor_data)

    db.commit()
    return jsonify({"message": "所有网箱数据已更新", "count": len(cages)})


if __name__ == "__main__":
    app.run(debug=False, port=5000)
