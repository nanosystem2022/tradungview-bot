from flask import Blueprint, render_template

errors_bp = Blueprint('errors', __name__)

@errors_bp.app_errorhandler(Exception)
def handle_error(error):
    return render_template('error.html', error=error), 500
