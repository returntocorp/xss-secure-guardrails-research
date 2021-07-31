from flask_sqlalchemy import SQLAlchemy
from database import db
import enum

class TriageStatus(enum.Enum):
    unreviewed = 0
    true_positive = "👍"
    false_positive = "👎"
    unknown = "🤷"

class Taxonomy(enum.Enum):
    A = "👍 Detected XSS, and the fix addressed the finding"
    B = "👍 Detected XSS, but the fix was not the fix recommended by the policy (e.g., detected unsafe template, but fix was in server code)"
    C = "😐 Framework not covered"
    D = "😐 Language not covered"
    E = "👎 XSS not detected"

class Finding(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    repo_url = db.Column(db.String(1024))
    repo_message = db.Column(db.Text())
    fix_commit = db.Column(db.String(512))
    previous_commit = db.Column(db.String(512))
    diff_text = db.Column(db.Text())
    semgrep_results_on_diff = db.Column(db.Text())
    triage_status = db.Column(db.Enum(TriageStatus))
    taxonomy = db.Column(db.Enum(Taxonomy))
    reviewer_notes = db.Column(db.Text())
