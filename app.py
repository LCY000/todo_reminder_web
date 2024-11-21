#b11109005
#2024.10.31完成，大概做了11小時

# app.py
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from models import db, User, Task
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 初始化資料庫
with app.app_context():
    db.create_all()

# 自訂過濾器：將 datetime 轉換為 HTML datetime-local 格式
@app.template_filter('datetime_local')
def datetime_local(dt):
    return dt.strftime('%Y-%m-%dT%H:%M') if dt else ''

@app.route('/')
def index():
    if current_user.is_authenticated:
        todos = Task.query.filter_by(user_id=current_user.id, status='todo', is_deleted=False).order_by(Task.order).all()
        reminders = Task.query.filter_by(user_id=current_user.id, status='reminder', is_deleted=False).order_by(Task.order).all()
    else:
        todos = []
        reminders = []
    return render_template('index.html', todos=todos, reminders=reminders)

# 新增task
@app.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form.get('content')
        status = request.form['status']
        time = request.form.get('time')

        # 找到該使用者目前最大的 task_id，若無任務則從 1 開始
        last_task = Task.query.filter_by(user_id=current_user.id).order_by(Task.task_id.desc()).first()
        new_task_id = last_task.task_id + 1 if last_task else 1

        task_time = datetime.fromisoformat(time) if time else None

        new_task = Task(
            user_id=current_user.id,
            task_id=new_task_id,
            title=title,
            content=content,
            status=status,
            time=task_time,
            order=len(Task.query.filter_by(user_id=current_user.id, status=status).all())
        )
        db.session.add(new_task)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('create.html')

# 更新task
@app.route('/edit/<int:user_id>/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit(user_id, task_id):
    task = Task.query.filter_by(user_id=user_id, task_id=task_id).first_or_404()
    if request.method == 'POST':
        task.title = request.form['title']
        task.content = request.form.get('content')
        task.status = request.form['status']
        time = request.form.get('time')
        task.time = datetime.fromisoformat(time) if time else None
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit.html', task=task)

# 刪除task
@app.route('/delete/<int:user_id>/<int:task_id>')
@login_required
def delete(user_id, task_id):
    task = Task.query.filter_by(user_id=user_id, task_id=task_id).first_or_404()
    task.is_deleted = True
    db.session.commit()
    return redirect(url_for('index'))

# 最近刪除頁面
@app.route('/deleted')
@login_required
def deleted():
    deleted_tasks = Task.query.filter_by(user_id=current_user.id, is_deleted=True).all()
    return render_template('deleted.html', deleted_tasks=deleted_tasks)

# 還原任務
@app.route('/restore/<int:user_id>/<int:task_id>')
@login_required
def restore_task(user_id, task_id):
    task = Task.query.filter_by(user_id=user_id, task_id=task_id).first_or_404()
    task.is_deleted = False
    db.session.commit()
    return redirect(url_for('deleted'))

# 永久刪除任務
@app.route('/hard_delete_task/<int:user_id>/<int:task_id>')
@login_required
def hard_delete_task(user_id, task_id):
    task = Task.query.filter_by(user_id=user_id, task_id=task_id).first_or_404()
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('deleted'))

# 更新清單先後排序
@app.route('/update_order', methods=['POST'])
@login_required
def update_order():
    data = request.get_json()

    # 更新每個 task 的順序和狀態
    for item in data:
        task = Task.query.filter_by(user_id=item['user_id'], task_id=item['task_id']).first()
        if task:
            task.order = item['order']  # 更新順序
            task.status = item['status']  # 更新狀態
    db.session.commit()

    return jsonify({'message': '順序更新成功'}), 200


# User帳號相關
# 註冊頁面
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # 檢查 Email 是否已存在
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('此 Email 已被註冊，請使用其他 Email', 'error')
            return redirect(url_for('register'))

        # 如果 Email 不存在，創建新用戶
        new_user = User(username=username, email=email)
        new_user.set_password(password)

        db.session.add(new_user)
        try:
            db.session.commit()
            flash('註冊成功，請登入', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('註冊時出現問題，請稍後再試', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

# 登入頁面
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('登入失敗，請檢查電子郵件和密碼')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# 更新帳戶
@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form.get('password')  # 可選的密碼更新

        # 檢查新的 email 是否已被其他帳號使用
        if email != current_user.email:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('此電子郵件已被使用，請使用其他電子郵件')
                return redirect(url_for('account'))

        # 更新使用者名稱和電子郵件
        current_user.username = username
        current_user.email = email

        # 如果有輸入新密碼，則更新密碼
        if password:
            current_user.set_password(password)

        db.session.commit()
        flash('帳戶更新成功')
        return redirect(url_for('account'))
    
    return render_template('account.html', user=current_user)

# 刪除帳戶
@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    user = current_user

    try:
        # 刪除該使用者的所有任務
        from models import Task  
        Task.query.filter_by(user_id=user.id).delete()

        # 刪除該使用者
        db.session.delete(user)
        db.session.commit()

        # 登出並跳轉回主頁
        logout_user()
        flash('帳戶已刪除', 'success')
        return redirect(url_for('login'))
    except Exception as e:
        db.session.rollback()
        flash('刪除帳戶失敗，請稍後再試', 'error')
        return redirect(url_for('account'))

if __name__ == '__main__':
    # app.run(debug=True)
    app.run()
