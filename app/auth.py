from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db, bcrypt
from app.models import User
from config import Config

auth_bp = Blueprint('auth', __name__)


# ── Signup ───────────────────────────────────────────────────────────────────
@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name         = request.form.get('name',         '').strip()
        email        = request.form.get('email',        '').strip().lower()
        password     = request.form.get('password',     '').strip()
        denomination = request.form.get('denomination', 'Protestant (General)')

        if not name or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('auth/signup.html',
                                   denominations=Config.DENOMINATIONS)

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('auth/signup.html',
                                   denominations=Config.DENOMINATIONS)

        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please log in.', 'danger')
            return render_template('auth/signup.html',
                                   denominations=Config.DENOMINATIONS)

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(
            name         = name,
            email        = email,
            password     = hashed_pw,
            denomination = denomination
        )
        db.session.add(user)
        db.session.commit()

        flash('Account created! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/signup.html', denominations=Config.DENOMINATIONS)


# ── Login ────────────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email',    '').strip().lower()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('Both fields are required.', 'danger')
            return render_template('auth/login.html')

        user = User.query.filter_by(email=email).first()
        if not user or not bcrypt.check_password_hash(user.password, password):
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html')

        session['user_id']       = user.id
        session['user_name']     = user.name
        session['user_email']    = user.email
        session['denomination']  = user.denomination

        flash(f'Welcome back, {user.name}!', 'success')
        return redirect(url_for('chat.index'))

    return render_template('auth/login.html')


# ── Logout ───────────────────────────────────────────────────────────────────
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out. God bless!', 'info')
    return redirect(url_for('auth.login'))


# ── Update denomination ───────────────────────────────────────────────────────
@auth_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    from app.utils import get_current_user, login_required
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        denomination = request.form.get('denomination', user.denomination)
        user.denomination = denomination
        session['denomination'] = denomination
        db.session.commit()
        flash('Denomination updated!', 'success')

    return render_template('auth/settings.html',
                           denominations=Config.DENOMINATIONS,
                           user=user)