from flask import render_template, request, jsonify

import api
import samples


def admin_main():
    return render_template("admin/admin_home.html")


def admin_samples():
    if request.method == "POST":
        action = request.form.get("action")
        sample_id = request.form.get("sample_id", type=int)

        if action == "approve":
            sample = api.get_sample_info(sample_id)
            if sample:
                sample.is_public = True
                api.db.session.commit()
            return jsonify({"success": True})
        elif action == "delete":
            return samples.delete_sample(sample_id)

    samples_list = api.samples_private()

    return render_template(
        "admin/admin_samples.html",
        samples=samples_list)
