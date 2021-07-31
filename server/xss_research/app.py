import flask
import logging
import os
import sys
from urllib.parse import urlparse 
from database import db
from models import Finding, TriageStatus
from typing import Any

from flask_migrate import Migrate

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

def create_app() -> flask.Flask:
    app = flask.Flask(__name__)
    db_path = os.path.abspath(os.environ.get("RULE_STATS_DB", "../data/xss_research_v2.db"))
    sql_url = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_DATABASE_URI"] = sql_url
    db.init_app(app)
    return app

app = create_app()
with app.app_context():
    db.create_all()
migrate = Migrate(app, db)

@app.errorhandler(404)
def handler_not_found(exc: Any) -> Any:
    return exc

@app.route('/', methods=["GET"])
def index() -> flask.Response():
    findings: List[Finding] = Finding.query.order_by(Finding.triage_status.desc()).all()
    return flask.render_template("index.html", findings=findings)

@app.route('/login')
def login() -> flask.Response():
    pass

@app.route('/logout')
def logout() -> flask.Response():
    pass

@app.route('/details/<int:finding_id>', methods=["GET"])
def details(finding_id: int) -> flask.Response():
    finding = Finding.query.filter(Finding.id == finding_id).first()
    logger.debug(finding.diff_text)

    repo_url_path = urlparse(finding.repo_url).path.lstrip("/")
    taxonomy = finding.taxonomy.name if finding.taxonomy else "A"
    return flask.render_template("details.html",
        repo_url=finding.repo_url,
        repo_url_path=repo_url_path,
        repo_message=finding.repo_message,
        diffstring=finding.diff_text,
        fix_commit=finding.fix_commit,
        previous_commit=finding.previous_commit,
        semgrep_results_on_diff=finding.semgrep_results_on_diff,
        triage_status=finding.triage_status.value,
        reviewer_notes=finding.reviewer_notes,
        taxonomy=taxonomy,
        finding_id=finding_id,
    )

@app.route('/update/<int:finding_id>', methods=["POST"])
def update(finding_id: int) -> flask.Response():
    triage_status = flask.request.form.get("triage_status")
    reviewer_notes = flask.request.form.get("reviewer_notes")
    taxonomy = flask.request.form.get("taxonomy")
    updates = {}
    if triage_status:
        updates["triage_status"] = TriageStatus(triage_status)
    if reviewer_notes:
        updates["reviewer_notes"] = reviewer_notes
    if taxonomy:
        updates["taxonomy"] = taxonomy

    db.session.query(Finding).filter(Finding.id == finding_id).update(updates)
    db.session.commit()

    return flask.redirect(flask.url_for("details", finding_id=finding_id))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--no-ssl":
        app.run()
    else:
        app.run(host="0.0.0.0", ssl_context="adhoc")
