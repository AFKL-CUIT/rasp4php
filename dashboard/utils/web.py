from rasp.core.app import RASP_APP
from dashboard.core.webapp import WEBAPP
from dashboard.models.users import Users

from functools import wraps
from flask import jsonify, redirect, url_for, request, session, abort

def json_data(data, status_code: int = 200):
    res_data = {
        "status": status_code,
        "data": data
    }
    return jsonify(res_data)

def get_page_and_size(get_data: dict):
    page = get_data.get('page', 1)
    if not isinstance(page, int):
        page = 1
    size = get_data.get('size', 10)
    if not isinstance(size, int):
        size = 10
    return int(page), int(size)

def get_pagination(page, size):
    start = (page - 1) * size
    end = start + size
    return start, end

def not_install_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if RASP_APP.is_installed:
            return abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_data" not in session:
            return redirect(url_for('login_page', next=request.url))
        
        user = session["user_data"]
        if isinstance(user, dict) and user["username"] != "":
            return f(*args, **kwargs)
        
        return redirect(url_for('login_page', next=request.url))
        
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_data" not in session:
            return redirect(url_for('login_page', next=request.url))
        
        user = session["user_data"]
        if (
            not isinstance(user, dict) and 
            user["permission"] != Users.ADMIN_USER
        ):
            return abort(403)
        
        return f(*args, **kwargs)

    return decorated_function