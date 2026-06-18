from flask import Flask, jsonify, request, g
from flask_cors import CORS
from sqlalchemy import desc
from datetime import datetime, timedelta
import random
from database import SessionLocal, engine, Base
from models import Cage, SensorData, Alert

Base.metadata.create_all(bind=engine)

app = Flask(__name__)
CORS(app)

THRESHOLDS = {
    "temperature": {"min": 12.0, "max": 22.0},
    "salinity": {"min": 28.0, "max": 35.0}
}

ALERT_COOLDOWN_MINUTES = 30


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


def check_threshold(cage_id, cage_name, temperature, salinity):
    db = get_db()
    alerts = []
    now = datetime.utcnow()
    cooldown_time = now - timedelta(minutes=ALERT_COOLDOWN_MINUTES)

    temp_ok = THRESHOLDS["temperature"]["min"] <= temperature <= THRESHOLDS["temperature"]["max"]
    if not temp_ok:
        recent = db.query(Alert).filter(
            Alert.cage_id == cage_id,
            Alert.alert_type == "temperature",
            Alert.timestamp >= cooldown_time
        ).first()

        if not recent:
            level = "error" if temperature > THRESHOLDS["temperature"]["max"] else "warning"
            direction = "过高" if temperature > THRESHOLDS["temperature"]["max"] else "过低"
            alert = Alert(
                cage_id=cage_id,
                alert_type="temperature",
                message=f"{cage_name} 温度{direction}",
                value=temperature,
                threshold_min=THRESHOLDS["temperature"]["min"],
                threshold_max=THRESHOLDS["temperature"]["max"],
                level=level,
                resolved=False,
                timestamp=now
            )
            db.add(alert)
            alerts.append(alert)

    sal_ok = THRESHOLDS["salinity"]["min"] <= salinity <= THRESHOLDS["salinity"]["max"]
    if not sal_ok:
        recent = db.query(Alert).filter(
            Alert.cage_id == cage_id,
            Alert.alert_type == "salinity",
            Alert.timestamp >= cooldown_time
        ).first()

        if not recent:
            level = "error" if salinity > THRESHOLDS["salinity"]["max"] else "warning"
            direction = "过高" if salinity > THRESHOLDS["salinity"]["max"] else "过低"
            alert = Alert(
                cage_id=cage_id,
                alert_type="salinity",
                message=f"{cage_name} 盐度{direction}",
                value=salinity,
                threshold_min=THRESHOLDS["salinity"]["min"],
                threshold_max=THRESHOLDS["salinity"]["max"],
                level=level,
                resolved=False,
                timestamp=now
            )
            db.add(alert)
            alerts.append(alert)

    if alerts:
        db.commit()

    return alerts


def get_cage_alert_status(db, cage_id):
    latest_temp_alert = db.query(Alert).filter(
        Alert.cage_id == cage_id,
        Alert.alert_type == "temperature",
        Alert.resolved == False
    ).order_by(desc(Alert.timestamp)).first()

    latest_sal_alert = db.query(Alert).filter(
        Alert.cage_id == cage_id,
        Alert.alert_type == "salinity",
        Alert.resolved == False
    ).order_by(desc(Alert.timestamp)).first()

    has_alert = False
    alert_level = "normal"

    for alert in [latest_temp_alert, latest_sal_alert]:
        if alert:
            time_diff = (datetime.utcnow() - alert.timestamp).total_seconds()
            if time_diff < ALERT_COOLDOWN_MINUTES * 60:
                has_alert = True
                if alert.level == "error":
                    alert_level = "error"
                elif alert_level != "error":
                    alert_level = "warning"

    return {
        "hasAlert": has_alert,
        "level": alert_level,
        "temperatureAlert": latest_temp_alert is not None and (datetime.utcnow() - latest_temp_alert.timestamp).total_seconds() < ALERT_COOLDOWN_MINUTES * 60,
        "salinityAlert": latest_sal_alert is not None and (datetime.utcnow() - latest_sal_alert.timestamp).total_seconds() < ALERT_COOLDOWN_MINUTES * 60
    }


@app.route("/api/cages", methods=["GET"])
def get_cages():
    db = get_db()
    cages = db.query(Cage).all()
    result = []
    for cage in cages:
        latest_data = db.query(SensorData).filter(
            SensorData.cage_id == cage.id
        ).order_by(desc(SensorData.timestamp)).first()

        alert_status = get_cage_alert_status(db, cage.id)

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
            "alert": alert_status
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

    alert_status = get_cage_alert_status(db, cage_id)

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
        "alert": alert_status
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


@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    db = get_db()
    hours = request.args.get("hours", default=24, type=int)
    only_unresolved = request.args.get("unresolved", default="false") == "true"

    time_threshold = datetime.utcnow() - timedelta(hours=hours)
    query = db.query(Alert).filter(Alert.timestamp >= time_threshold)

    if only_unresolved:
        query = query.filter(Alert.resolved == False)

    alerts = query.order_by(desc(Alert.timestamp)).all()

    result = []
    for alert in alerts:
        cage = db.query(Cage).filter(Cage.id == alert.cage_id).first()
        result.append({
            "id": alert.id,
            "cageId": alert.cage_id,
            "cageName": cage.name if cage else "未知",
            "alertType": alert.alert_type,
            "message": alert.message,
            "value": alert.value,
            "thresholdMin": alert.threshold_min,
            "thresholdMax": alert.threshold_max,
            "level": alert.level,
            "resolved": alert.resolved,
            "timestamp": alert.timestamp.isoformat()
        })

    return jsonify(result)


@app.route("/api/alerts/latest", methods=["GET"])
def get_latest_alerts():
    db = get_db()
    limit = request.args.get("limit", default=20, type=int)

    alerts = db.query(Alert).order_by(desc(Alert.timestamp)).limit(limit).all()

    result = []
    for alert in alerts:
        cage = db.query(Cage).filter(Cage.id == alert.cage_id).first()
        result.append({
            "id": alert.id,
            "cageId": alert.cage_id,
            "cageName": cage.name if cage else "未知",
            "alertType": alert.alert_type,
            "message": alert.message,
            "value": alert.value,
            "thresholdMin": alert.threshold_min,
            "thresholdMax": alert.threshold_max,
            "level": alert.level,
            "resolved": alert.resolved,
            "timestamp": alert.timestamp.isoformat()
        })

    return jsonify(result)


@app.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
def resolve_alert(alert_id):
    db = get_db()
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        return jsonify({"error": "报警不存在"}), 404

    alert.resolved = True
    db.commit()

    return jsonify({"message": "报警已确认处理", "id": alert.id})


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

    alerts = check_threshold(cage_id, cage.name, temperature, salinity)

    return jsonify({
        "message": "数据更新成功",
        "id": sensor_data.id,
        "alerts": [{"type": a.alert_type, "level": a.level, "message": a.message} for a in alerts]
    })


@app.route("/api/sensor/random-update", methods=["POST"])
def random_update():
    db = get_db()
    cages = db.query(Cage).all()
    all_alerts = []

    for idx, cage in enumerate(cages):
        latest_data = db.query(SensorData).filter(
            SensorData.cage_id == cage.id
        ).order_by(desc(SensorData.timestamp)).first()

        base_temp = latest_data.temperature if latest_data else 18.0
        base_sal = latest_data.salinity if latest_data else 32.0

        if idx == 1 and random.random() < 0.4:
            new_temp = round(23.0 + random.uniform(0, 2), 2)
        elif idx == 8 and random.random() < 0.4:
            new_sal = round(36.0 + random.uniform(0, 2), 2)
            new_temp = round(base_temp + random.uniform(-0.3, 0.3), 2)
        else:
            new_temp = round(base_temp + random.uniform(-0.3, 0.3), 2)
            new_sal = round(base_sal + random.uniform(-0.2, 0.2), 2)

        new_temp = round(base_temp + random.uniform(-0.5, 0.5), 2) if idx != 1 else round(23.5 + random.uniform(0, 1.5), 2)
        new_sal = round(base_sal + random.uniform(-0.3, 0.3), 2) if idx != 8 else round(35.5 + random.uniform(0, 1.5), 2)

        sensor_data = SensorData(
            cage_id=cage.id,
            temperature=new_temp,
            salinity=new_sal,
            timestamp=datetime.utcnow()
        )
        db.add(sensor_data)

        alerts = check_threshold(cage.id, cage.name, new_temp, new_sal)
        all_alerts.extend(alerts)

    db.commit()
    return jsonify({
        "message": "所有网箱数据已更新",
        "count": len(cages),
        "newAlerts": len(all_alerts)
    })


if __name__ == "__main__":
    app.run(debug=False, port=5000)
