from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timezone
from threading import Lock

from request.controlador_db import insert_time_log_record, select_time_logs, updateColumn

time_log_bp = Blueprint("time_logs", __name__, url_prefix="/time-logs")


def genTimestamp():
    created_at = datetime.now(timezone.utc)
    return created_at.isoformat()


@time_log_bp.route("/", methods=["POST"])
def create_time_log():
    user_id = request.args.get("user_id")

    results = select_time_logs(user_id)

    if (len(results) > 0):
        return jsonify({"id": results[0]})

    id_log = insert_time_log_record(user_id)

    return jsonify({"id": id_log}), 201


@time_log_bp.route("/update", methods=["POST"])
def add_time_log():

    id = request.args.get("id")
    column = request.args.get("column")
    action = request.args.get("action")

    column_name = f"{action}_{column}"

    b = updateColumn(column_name, id)

    return jsonify({"result": b}), 201
