from flask import render_template, request, jsonify, url_for

import api
import samples
from notifications import notify_user


def admin_main():
    return render_template("admin/admin_home.html")


def admin_samples():
    if request.method == "POST":
        action = request.form.get("action")
        sample_id = request.form.get("sample_id", type=int)
        sample = api.get_sample_info(sample_id)
        uploader = api.get_user_info(sample.uploader)

        if action == "approve":
            sample.is_public = True
            api.db.session.commit()

            sample_url = url_for("main.sample_page", sample_id=sample.id)
            message = render_template(
                "notifications/approval.html",
                username=uploader.username,
                filename=sample.filename,
                sample_url=sample_url
            )
            notify_user(uploader.id, f"Sample approved: {sample.filename}", message)

            return jsonify({"success": True})
        elif action == "delete":
            message = render_template(
                "notifications/denial.html",
                username=uploader.username,
                filename=sample.filename
            )
            notify_user(uploader.id, f"Sample denied: {sample.filename}", message)

            return samples.delete_sample(sample_id)

    samples_list = api.samples_private()

    return render_template(
        "admin/admin_samples.html",
        samples=samples_list)
