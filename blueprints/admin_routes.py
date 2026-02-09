from flask import Blueprint, jsonify
from flask_login import login_required, current_user

import admin

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
@login_required
def admin_required():
    if not current_user.is_admin:
        return jsonify({"message": "Access denied"}), 403


@admin_bp.route("/")
def admin_main():
    return admin.admin_main()
