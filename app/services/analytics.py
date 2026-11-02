import io
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sqlalchemy import func
from ..extensions import db
from ..models import Student, PlacementOffer, Application, JobOpening, StudentSkill, Skill, Role


def college_placement_summary(college_id):
    """Unique-student placement rate; only active students in the selected graduating cohort."""
    eligible_query = Student.query.filter_by(college_id=college_id, status="active")
    eligible_count = eligible_query.count()
    placed_ids = db.session.query(PlacementOffer.student_id).filter(
        PlacementOffer.college_id == college_id,
        PlacementOffer.acceptance_status.in_(["accepted", "pending"]),
    ).distinct().all()
    placed_count = len(placed_ids)
    rate = (placed_count / eligible_count * 100) if eligible_count else 0.0

    packages = [float(x[0]) for x in db.session.query(PlacementOffer.annual_package_lpa).filter(
        PlacementOffer.college_id == college_id,
        PlacementOffer.acceptance_status.in_(["accepted", "pending"]),
    ).all() if x[0] is not None]
    return {
        "eligible_students": eligible_count,
        "unique_placed_students": placed_count,
        "placement_rate": round(rate, 2),
        "mean_package_lpa": round(float(np.mean(packages)), 2) if packages else None,
        "median_package_lpa": round(float(np.median(packages)), 2) if packages else None,
        "min_package_lpa": min(packages) if packages else None,
        "max_package_lpa": max(packages) if packages else None,
        "offer_count": len(packages),
    }


def department_placement_rows(college_id):
    """Section-level starter report using distinct student IDs to avoid duplicate-offer inflation."""
    students = Student.query.filter_by(college_id=college_id, status="active").all()
    placed_ids = {row[0] for row in db.session.query(PlacementOffer.student_id).filter(
        PlacementOffer.college_id == college_id,
        PlacementOffer.acceptance_status.in_(["accepted", "pending"]),
    ).distinct().all()}
    grouped = {}
    for student in students:
        key = student.section_id
        grouped.setdefault(key, {"section_id": key, "eligible": 0, "placed": 0})
        grouped[key]["eligible"] += 1
        if student.id in placed_ids:
            grouped[key]["placed"] += 1
    output = []
    for row in grouped.values():
        row["placement_rate"] = (row["placed"] / row["eligible"] * 100) if row["eligible"] else 0.0
        output.append(row)
    return output


def package_histogram_png(college_id):
    values = [float(x[0]) for x in db.session.query(PlacementOffer.annual_package_lpa).filter(
        PlacementOffer.college_id == college_id
    ).all() if x[0] is not None]
    fig, ax = plt.subplots(figsize=(7, 4))
    if values:
        ax.hist(values, bins=min(10, max(3, len(set(values)))), edgecolor="black")
        ax.set_xlabel("Annual package (LPA)")
        ax.set_ylabel("Number of offers")
        ax.set_title("Package distribution")
    else:
        ax.text(0.5, 0.5, "No package data available", ha="center", va="center")
        ax.set_axis_off()
    fig.tight_layout()
    output = io.BytesIO()
    fig.savefig(output, format="png", dpi=140)
    plt.close(fig)
    output.seek(0)
    return output


def skill_demand(college_id):
    rows = db.session.query(Skill.name, func.count(StudentSkill.student_id).label("student_count")).join(
        StudentSkill, StudentSkill.skill_id == Skill.id
    ).filter(StudentSkill.college_id == college_id).group_by(Skill.id, Skill.name).order_by(
        func.count(StudentSkill.student_id).desc()
    ).limit(20).all()
    return [{"skill": name, "students": count} for name, count in rows]


def application_status_summary(college_id):
    """Count applications by workflow status for one college only."""
    rows = db.session.query(Application.status, func.count(Application.id)).filter(
        Application.college_id == college_id
    ).group_by(Application.status).all()
    labels = ["applied", "shortlisted", "interview", "selected", "offer_accepted", "rejected", "withdrawn", "waitlisted"]
    counts = {status: count for status, count in rows}
    return [{"status": label.replace("_", " ").title(), "count": counts.get(label, 0)} for label in labels]


def application_status_chart_png(college_id):
    summary = application_status_summary(college_id)
    labels = [row["status"] for row in summary]
    values = [row["count"] for row in summary]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(labels, values, edgecolor="black")
    ax.set_title("Job application status overview")
    ax.set_ylabel("Number of applications")
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    output = io.BytesIO()
    fig.savefig(output, format="png", dpi=140)
    plt.close(fig)
    output.seek(0)
    return output


def academic_performance_chart_png(college_id):
    """Plot average recorded subject totals for the selected college."""
    from ..models import Mark, Subject
    rows = db.session.query(Subject.name, func.avg(Mark.total_marks)).join(
        Mark, Mark.subject_id == Subject.id
    ).filter(Mark.college_id == college_id, Subject.college_id == college_id).group_by(
        Subject.id, Subject.name
    ).order_by(Subject.name).limit(12).all()
    fig, ax = plt.subplots(figsize=(8, 4))
    if rows:
        labels = [name for name, _ in rows]
        values = [float(avg or 0) for _, avg in rows]
        ax.bar(labels, values, edgecolor="black")
        ax.set_ylabel("Average marks")
        ax.set_ylim(bottom=0)
        ax.tick_params(axis="x", rotation=30)
        ax.set_title("Average marks by subject")
    else:
        ax.text(0.5, 0.5, "No subject marks recorded yet", ha="center", va="center")
        ax.set_axis_off()
    fig.tight_layout()
    output = io.BytesIO()
    fig.savefig(output, format="png", dpi=140)
    plt.close(fig)
    output.seek(0)
    return output


def attendance_status_chart_png(college_id):
    """Plot present, absent and excused attendance record counts."""
    from ..models import AttendanceRecord
    rows = db.session.query(AttendanceRecord.status, func.count(AttendanceRecord.id)).filter(
        AttendanceRecord.college_id == college_id
    ).group_by(AttendanceRecord.status).all()
    labels = ["present", "absent", "excused"]
    counts = dict(rows)
    values = [counts.get(label, 0) for label in labels]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([label.title() for label in labels], values, edgecolor="black")
    ax.set_ylabel("Attendance records")
    ax.set_title("Attendance status overview")
    fig.tight_layout()
    output = io.BytesIO()
    fig.savefig(output, format="png", dpi=140)
    plt.close(fig)
    output.seek(0)
    return output
