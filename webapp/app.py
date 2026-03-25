from flask import Flask, jsonify, request, render_template_string, send_file, session, redirect, url_for
from flask_cors import CORS
import sqlite3
import os
from pathlib import Path
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'
CORS(app)

# 用户配置
USERS = {
    'admin': 'Jh2044695'
}

# 登录验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'daily.db')
RESOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'resource')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# 登录页面
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if username in USERS and USERS[username] == password:
            session['username'] = username
            return jsonify({'success': True, 'message': '登录成功'})
        else:
            return jsonify({'success': False, 'message': '用户名或密码错误'}), 401
    
    return render_template_string(LOGIN_TEMPLATE)

# 登出
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# 浏览页面（无需登录，只读）
@app.route('/view')
def view():
    return render_template_string(VIEW_TEMPLATE)

# 主页（需要登录，可编辑）
@app.route('/')
@login_required
def index():
    return render_template_string(HTML_TEMPLATE)

# API: 获取日期列表（公开访问）
@app.route('/api/dates')
def get_dates():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT date FROM digital_paper ORDER BY date DESC")
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(dates)

# API: 获取指定日期的版面列表（公开访问）
@app.route('/api/pages/<date>')
def get_pages(date):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT page_no, page_name, pdf 
        FROM digital_paper 
        WHERE date = ? 
        ORDER BY CAST(page_no AS INTEGER)
    """, (date,))
    rows = cursor.fetchall()
    conn.close()
    
    pages = []
    for row in rows:
        # 格式化版面号为 0x 格式
        page_no = row['page_no']
        try:
            page_no = str(int(page_no)).zfill(2)
        except (ValueError, TypeError):
            page_no = str(page_no) if page_no else '00'
        
        pages.append({
            'page_no': page_no,
            'page_name': row['page_name'],
            'pdf': row['pdf']
        })
    return jsonify(pages)

# API: 获取指定日期和版面的文章列表（不含内容，公开访问）
@app.route('/api/papers/<date>/<page_no>')
def get_papers(date, page_no):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 将传入的 page_no（如 "01"）转换为整数（如 1），以便与数据库中的值匹配
    try:
        page_no_int = int(page_no)
    except (ValueError, TypeError):
        page_no_int = page_no
    
    cursor.execute("""
        SELECT id, date, title, author, collaborator, photo, page_no, page_name, 
               site_id, is_xinhua, is_pic, pdf,
               left_top_x, left_top_y, left_bottom_x, left_bottom_y,
               right_bottom_x, right_bottom_y, right_top_x, right_top_y
        FROM digital_paper 
        WHERE date = ? AND CAST(page_no AS INTEGER) = ?
        ORDER BY id
    """, (date, page_no_int))
    rows = cursor.fetchall()
    conn.close()
    
    papers = []
    for row in rows:
        # 格式化版面号为 0x 格式
        page_no = row['page_no']
        try:
            page_no = str(int(page_no)).zfill(2)
        except (ValueError, TypeError):
            page_no = str(page_no) if page_no else '00'
        
        papers.append({
            'id': row['id'],
            'date': row['date'],
            'title': row['title'],
            'author': row['author'],
            'collaborator': row['collaborator'],
            'photo': row['photo'],
            'page_no': page_no,
            'page_name': row['page_name'],
            'site_id': row['site_id'],
            'is_xinhua': row['is_xinhua'],
            'is_pic': row['is_pic'],
            'pdf': row['pdf'],
            'hotzone': {
                'left_top_x': row['left_top_x'],
                'left_top_y': row['left_top_y'],
                'left_bottom_x': row['left_bottom_x'],
                'left_bottom_y': row['left_bottom_y'],
                'right_bottom_x': row['right_bottom_x'],
                'right_bottom_y': row['right_bottom_y'],
                'right_top_x': row['right_top_x'],
                'right_top_y': row['right_top_y']
            }
        })
    return jsonify(papers)

# API: 获取单篇文章详情（含内容，公开访问）
@app.route('/api/paper/<int:paper_id>')
def get_paper_detail(paper_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, date, title, author, collaborator, photo, page_no, page_name, 
               site_id, is_xinhua, is_pic, content, pdf,
               left_top_x, left_top_y, left_bottom_x, left_bottom_y,
               right_bottom_x, right_bottom_y, right_top_x, right_top_y
        FROM digital_paper 
        WHERE id = ?
    """, (paper_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'error': 'Not found'}), 404
    
    # 格式化版面号为 0x 格式
    page_no = row['page_no']
    try:
        page_no = str(int(page_no)).zfill(2)
    except (ValueError, TypeError):
        page_no = str(page_no) if page_no else '00'
    
    return jsonify({
        'id': row['id'],
        'date': row['date'],
        'title': row['title'],
        'author': row['author'],
        'collaborator': row['collaborator'],
        'photo': row['photo'],
        'page_no': page_no,
        'page_name': row['page_name'],
        'site_id': row['site_id'],
        'is_xinhua': row['is_xinhua'],
        'is_pic': row['is_pic'],
        'content': row['content'],
        'pdf': row['pdf'],
        'hotzone': {
            'left_top_x': row['left_top_x'],
            'left_top_y': row['left_top_y'],
            'left_bottom_x': row['left_bottom_x'],
            'left_bottom_y': row['left_bottom_y'],
            'right_bottom_x': row['right_bottom_x'],
            'right_bottom_y': row['right_bottom_y'],
            'right_top_x': row['right_top_x'],
            'right_top_y': row['right_top_y']
        }
    })

# API: 更新文章
@app.route('/api/paper/<int:paper_id>', methods=['PUT'])
@login_required
def update_paper(paper_id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE digital_paper 
            SET title = ?, author = ?, collaborator = ?, photo = ?, 
                page_no = ?, page_name = ?, site_id = ?, is_xinhua = ?, is_pic = ?, content = ?
            WHERE id = ?
        """, (
            data.get('title'),
            data.get('author'),
            data.get('collaborator'),
            data.get('photo'),
            data.get('page_no'),
            data.get('page_name'),
            data.get('site_id'),
            data.get('is_xinhua', 0),
            data.get('is_pic', 0),
            data.get('content'),
            paper_id
        ))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '更新成功'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

# API: 删除文章
@app.route('/api/paper/<int:paper_id>', methods=['DELETE'])
@login_required
def delete_paper(paper_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM digital_paper WHERE id = ?", (paper_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

# API: 更新文章热区坐标
@app.route('/api/paper/<int:paper_id>/hotzone', methods=['PUT'])
@login_required
def update_hotzone(paper_id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE digital_paper 
            SET left_top_x = ?, left_top_y = ?,
                left_bottom_x = ?, left_bottom_y = ?,
                right_bottom_x = ?, right_bottom_y = ?,
                right_top_x = ?, right_top_y = ?
            WHERE id = ?
        """, (
            data.get('left_top_x', 0),
            data.get('left_top_y', 0),
            data.get('left_bottom_x', 0),
            data.get('left_bottom_y', 0),
            data.get('right_bottom_x', 0),
            data.get('right_bottom_y', 0),
            data.get('right_top_x', 0),
            data.get('right_top_y', 0),
            paper_id
        ))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '热区更新成功'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

# 提供PDF文件（公开访问）
@app.route('/pdf/<path:filename>')
def serve_pdf(filename):
    pdf_path = os.path.join(RESOURCE_DIR, filename)
    if os.path.exists(pdf_path):
        return send_file(pdf_path, mimetype='application/pdf')
    return jsonify({'error': 'PDF not found'}), 404

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录 - 舟山日报</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
        }
        .login-header {
            text-align: center;
            margin-bottom: 30px;
        }
        .login-header h1 {
            font-size: 24px;
            color: #333;
            margin-bottom: 10px;
        }
        .login-header p {
            color: #666;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-size: 14px;
        }
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 1px solid #d9d9d9;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        .form-group input:focus {
            outline: none;
            border-color: #1890ff;
        }
        .login-btn {
            width: 100%;
            padding: 12px;
            background: #1890ff;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
        }
        .login-btn:hover {
            background: #40a9ff;
        }
        .login-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .error-message {
            color: #ff4d4f;
            font-size: 14px;
            margin-top: 10px;
            text-align: center;
            display: none;
        }
        .error-message.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <h1>📰 舟山日报</h1>
            <p>电子报管理系统</p>
        </div>
        <form id="loginForm">
            <div class="form-group">
                <label for="username">用户名</label>
                <input type="text" id="username" name="username" placeholder="请输入用户名" required>
            </div>
            <div class="form-group">
                <label for="password">密码</label>
                <input type="password" id="password" name="password" placeholder="请输入密码" required>
            </div>
            <button type="submit" class="login-btn">登录</button>
            <div class="error-message" id="errorMsg"></div>
        </form>
    </div>
    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const errorMsg = document.getElementById('errorMsg');
            const loginBtn = document.querySelector('.login-btn');
            
            loginBtn.disabled = true;
            loginBtn.textContent = '登录中...';
            
            try {
                const res = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                
                const result = await res.json();
                
                if (result.success) {
                    window.location.href = '/';
                } else {
                    errorMsg.textContent = result.message;
                    errorMsg.classList.add('active');
                }
            } catch (e) {
                errorMsg.textContent = '登录失败，请重试';
                errorMsg.classList.add('active');
            } finally {
                loginBtn.disabled = false;
                loginBtn.textContent = '登录';
            }
        });
    </script>
</body>
</html>
'''

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>舟山日报</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #e8e8e8;
            min-height: 100vh;
            padding: 20px;
        }
        .app-wrapper {
            max-width: 1400px;
            margin: 0 auto;
            background: #f0f2f5;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            overflow: hidden;
            height: calc(100vh - 40px);
            display: flex;
            flex-direction: column;
        }
        .header {
            background: #fff;
            padding: 10px 20px;
            border-bottom: 1px solid #e8e8e8;
            display: flex;
            gap: 15px;
            align-items: center;
            height: 60px;
            flex-shrink: 0;
        }
        .header h1 { 
            font-size: 18px; 
            color: #333;
            margin-right: 20px;
        }
        select, button {
            padding: 6px 12px;
            border: 1px solid #d9d9d9;
            border-radius: 4px;
            font-size: 14px;
            background: #fff;
        }
        button {
            background: #1890ff;
            color: white;
            border: none;
            cursor: pointer;
        }
        button:hover { background: #40a9ff; }
        .main-container {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        .left-panel {
            flex: 1;
            background: #333;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .pdf-toolbar {
            background: #444;
            padding: 10px;
            display: flex;
            gap: 10px;
            align-items: center;
            color: #fff;
        }
        .pdf-container {
            flex: 1;
            overflow: auto;
            position: relative;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            padding: 20px;
        }
        #pdfCanvas {
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        }
        .hotzone-overlay {
            position: absolute;
            border: 2px solid transparent;
            cursor: pointer;
            transition: all 0.2s;
        }
        .hotzone-overlay:hover {
            border-color: #1890ff;
            background: rgba(24, 144, 255, 0.1);
        }
        .hotzone-overlay.active {
            border-color: #ff4d4f;
            background: rgba(255, 77, 79, 0.1);
        }
        .selection-box {
            position: absolute;
            border: 2px dashed #1890ff;
            background: rgba(24, 144, 255, 0.2);
            pointer-events: none;
            z-index: 100;
        }
        .selection-controls {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .selection-mode {
            background: #52c41a !important;
        }
        .selection-mode.active {
            background: #ff4d4f !important;
        }
        .toast-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 2000;
            justify-content: center;
            align-items: center;
        }
        .toast-modal.active { display: flex; }
        .toast-panel {
            background: white;
            padding: 30px 40px;
            border-radius: 8px;
            text-align: center;
            min-width: 300px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }
        .toast-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
        .toast-message {
            font-size: 16px;
            color: #333;
            margin-bottom: 20px;
        }
        .toast-success { color: #52c41a; }
        .toast-error { color: #ff4d4f; }
        .confirm-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 2000;
            justify-content: center;
            align-items: center;
        }
        .confirm-modal.active { display: flex; }
        .confirm-panel {
            background: white;
            padding: 30px 40px;
            border-radius: 8px;
            text-align: center;
            min-width: 300px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }
        .confirm-message {
            font-size: 16px;
            color: #333;
            margin-bottom: 25px;
        }
        .confirm-buttons {
            display: flex;
            gap: 15px;
            justify-content: center;
        }
        .confirm-buttons button {
            padding: 8px 24px;
            font-size: 14px;
        }
        .confirm-buttons .btn-save {
            background: #52c41a;
        }
        .confirm-buttons .btn-save:hover {
            background: #73d13d;
        }
        .confirm-buttons .btn-cancel {
            background: #999;
        }
        .confirm-buttons .btn-cancel:hover {
            background: #bbb;
        }
        .right-panel {
            width: 400px;
            background: #fff;
            border-left: 1px solid #e8e8e8;
            display: flex;
            flex-direction: column;
        }
        .page-tabs {
            display: flex;
            overflow-x: auto;
            border-bottom: 1px solid #e8e8e8;
            background: #fafafa;
        }
        .page-tab {
            padding: 12px 20px;
            cursor: pointer;
            white-space: nowrap;
            border-right: 1px solid #e8e8e8;
            font-size: 13px;
        }
        .page-tab:hover { background: #e6f7ff; }
        .page-tab.active { 
            background: #1890ff; 
            color: white;
        }
        .article-list {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }
        .article-item {
            padding: 12px;
            border: 1px solid #e8e8e8;
            border-radius: 4px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .article-item:hover {
            border-color: #1890ff;
            background: #e6f7ff;
        }
        .article-item.active {
            border-color: #ff4d4f;
            background: #fff1f0;
        }
        .article-item.selected-for-hotzone {
            border-color: #1890ff;
            background: #e6f7ff;
            box-shadow: 0 0 0 2px #1890ff;
        }
        .article-title {
            font-weight: bold;
            color: #333;
            margin-bottom: 6px;
            font-size: 14px;
        }
        .article-meta {
            font-size: 12px;
            color: #666;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .article-meta span {
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
        }
        .tag-xinhua { 
            background: #fff2e8 !important; 
            color: #fa8c16; 
        }
        .tag-pic { 
            background: #f6ffed !important; 
            color: #52c41a; 
        }
        .content-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .content-modal.active { display: flex; }
        .content-panel {
            background: white;
            width: 80%;
            max-width: 800px;
            height: 80%;
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .content-header {
            padding: 20px;
            border-bottom: 1px solid #e8e8e8;
            display: flex;
            justify-content: space-between;
            align-items: start;
        }
        .content-title {
            font-size: 18px;
            font-weight: bold;
            color: #333;
            flex: 1;
            margin-right: 20px;
        }
        .content-actions {
            display: flex;
            gap: 10px;
        }
        .content-body {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            line-height: 1.8;
            font-size: 15px;
            color: #333;
        }
        .close-btn {
            background: #ff4d4f;
        }
        .close-btn:hover { background: #ff7875; }
        .edit-btn { background: #52c41a; }
        .edit-btn:hover { background: #73d13d; }
        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #999;
        }
        .edit-form {
            display: none;
        }
        .edit-form.active { display: block; }
        .form-row {
            margin-bottom: 15px;
        }
        .form-row label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #666;
        }
        .form-row input, .form-row textarea {
            width: 100%;
            padding: 8px;
            border: 1px solid #d9d9d9;
            border-radius: 4px;
        }
        .form-row textarea {
            min-height: 200px;
            resize: vertical;
        }
    </style>
</head>
<body>
    <div class="app-wrapper">
        <div class="header">
            <h1>📰 舟山日报</h1>
            <input type="date" id="dateSelect" onchange="onDateChange()" style="padding: 6px 12px; border: 1px solid #d9d9d9; border-radius: 4px; font-size: 14px;">
        </div>
        
        <div class="main-container">
        <div class="left-panel">
            <div class="pdf-toolbar">
                <span id="pdfInfo">请选择日期加载PDF</span>
                <div class="selection-controls">
                    <button id="selectionBtn" class="selection-mode" onclick="toggleSelectionMode()">📐 框选热区</button>
                </div>
            </div>
            <div class="pdf-container" id="pdfContainer">
                <div class="empty-state">
                    <p>请选择日期并加载数据</p>
                </div>
            </div>
        </div>
        
        <div class="right-panel">
            <div class="page-tabs" id="pageTabs"></div>
            <div class="article-list" id="articleList">
                <div class="empty-state">
                    <p>请选择日期和版面</p>
                </div>
            </div>
        </div>
        </div>
    </div>
    
    <!-- Toast 提示框 -->
    <div class="toast-modal" id="toastModal">
        <div class="toast-panel">
            <div class="toast-icon" id="toastIcon"></div>
            <div class="toast-message" id="toastMessage"></div>
            <button onclick="closeToast()">确定</button>
        </div>
    </div>
    
    <!-- 确认对话框 -->
    <div class="confirm-modal" id="confirmModal">
        <div class="confirm-panel">
            <div class="confirm-message" id="confirmMessage"></div>
            <div class="confirm-buttons">
                <button class="btn-save" onclick="onConfirmYes()">💾 保存</button>
                <button class="btn-cancel" onclick="onConfirmNo()">❌ 取消</button>
            </div>
        </div>
    </div>
    
    <div class="content-modal" id="contentModal">
        <div class="content-panel">
            <div class="content-header">
                <div class="content-title" id="modalTitle"></div>
                <div class="content-actions">
                    <button class="edit-btn" onclick="toggleEdit()">✏️ 编辑</button>
                    <button class="close-btn" onclick="closeModal()">✕ 关闭</button>
                </div>
            </div>
            <div class="content-body" id="modalContent"></div>
            <div class="content-body edit-form" id="editForm">
                <div class="form-row">
                    <label>标题</label>
                    <input type="text" id="editTitle">
                </div>
                <div class="form-row">
                    <label>作者</label>
                    <input type="text" id="editAuthor">
                </div>
                <div class="form-row">
                    <label>通讯员</label>
                    <input type="text" id="editCollaborator">
                </div>
                <div class="form-row">
                    <label>摄影</label>
                    <input type="text" id="editPhoto">
                </div>
                <div class="form-row">
                    <label>内容</label>
                    <textarea id="editContent"></textarea>
                </div>
                <div class="form-row">
                    <button class="edit-btn" onclick="saveEdit()">💾 保存</button>
                    <button onclick="toggleEdit()">取消</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        
        let currentDate = '';
        let currentPage = '';
        let currentPdf = null;
        let currentScale = 1.5;
        let articles = [];
        let currentArticleId = null;
        let pdfDimensions = { width: 0, height: 0 };
        
        // 框选相关变量
        let isSelectionMode = false;
        let isSelecting = false;
        let selectionStart = { x: 0, y: 0 };
        let selectionEnd = { x: 0, y: 0 };
        let selectionBox = null;
        let selectedArticleId = null;

        // Toast 提示函数
        function showToast(message, isSuccess = true) {
            const modal = document.getElementById('toastModal');
            const icon = document.getElementById('toastIcon');
            const msg = document.getElementById('toastMessage');

            icon.textContent = isSuccess ? '✅' : '❌';
            icon.className = 'toast-icon ' + (isSuccess ? 'toast-success' : 'toast-error');
            msg.textContent = message;

            modal.classList.add('active');
        }

        function closeToast() {
            document.getElementById('toastModal').classList.remove('active');
        }

        // 确认对话框相关变量和函数
        let confirmYesCallback = null;
        let confirmNoCallback = null;

        function showConfirmDialog(message, onYes, onNo) {
            const modal = document.getElementById('confirmModal');
            const msg = document.getElementById('confirmMessage');
            
            msg.textContent = message;
            confirmYesCallback = onYes;
            confirmNoCallback = onNo;
            
            modal.classList.add('active');
        }

        function closeConfirmDialog() {
            document.getElementById('confirmModal').classList.remove('active');
            confirmYesCallback = null;
            confirmNoCallback = null;
        }

        function onConfirmYes() {
            if (confirmYesCallback) {
                confirmYesCallback();
            }
            closeConfirmDialog();
        }

        function onConfirmNo() {
            if (confirmNoCallback) {
                confirmNoCallback();
            }
            closeConfirmDialog();
        }
        
        // 加载日期列表并设置日期选择器的范围
        async function loadDates() {
            try {
                const res = await fetch('/api/dates');
                const dates = await res.json();
                const dateInput = document.getElementById('dateSelect');
                
                if (dates.length > 0) {
                    // 设置最小和最大日期
                    dateInput.min = dates[dates.length - 1];  // 最早的日期
                    dateInput.max = dates[0];  // 最新的日期
                }
            } catch (e) {
                console.error('加载日期失败:', e);
            }
        }
        
        // 日期选择变化时自动加载
        async function onDateChange() {
            const date = document.getElementById('dateSelect').value;
            if (!date) return;
            await loadDate(date);
        }
        
        // 加载指定日期的数据
        async function loadDate(date) {
            if (!date) return;
            currentDate = date;
            
            try {
                const res = await fetch(`/api/pages/${date}`);
                const pages = await res.json();
                renderPageTabs(pages);
            } catch (e) {
                console.error('加载版面失败:', e);
            }
        }
        
        // 渲染版面标签
        function renderPageTabs(pages) {
            const tabs = document.getElementById('pageTabs');
            tabs.innerHTML = '';
            
            pages.forEach((page, index) => {
                const tab = document.createElement('div');
                tab.className = 'page-tab' + (index === 0 ? ' active' : '');
                const formattedPageNo = formatPageNo(page.page_no);
                tab.textContent = `${page.page_name} (${formattedPageNo})`;
                tab.onclick = () => selectPage(page);
                tabs.appendChild(tab);
            });
            
            if (pages.length > 0) {
                selectPage(pages[0]);
            }
        }
        
        // 格式化版面号为 0x 格式
        function formatPageNo(pageNo) {
            try {
                const num = parseInt(pageNo);
                return String(num).padStart(2, '0');
            } catch (e) {
                return pageNo || '00';
            }
        }
        
        // 切换框选模式
        function toggleSelectionMode() {
            isSelectionMode = !isSelectionMode;
            const btn = document.getElementById('selectionBtn');
            const saveBtn = document.getElementById('saveHotzoneBtn');
            const cancelBtn = document.getElementById('cancelSelectionBtn');
            
            if (isSelectionMode) {
                btn.textContent = '❌ 退出框选';
                btn.classList.add('active');
                
                // 重新渲染文章列表以显示 radio 按钮
                renderArticleList();
                
                initSelectionHandlers();
            } else {
                cancelSelection();
            }
        }
        
        // 初始化框选事件处理器
        function initSelectionHandlers() {
            const container = document.getElementById('pdfContainer');
            
            container.addEventListener('mousedown', onSelectionStart);
            container.addEventListener('mousemove', onSelectionMove);
            container.addEventListener('mouseup', onSelectionEnd);
        }
        
        // 开始框选
        function onSelectionStart(e) {
            if (!isSelectionMode || !selectedArticleId) return;
            
            const container = document.getElementById('pdfContainer');
            const rect = container.getBoundingClientRect();
            
            isSelecting = true;
            selectionStart = {
                x: e.clientX - rect.left,
                y: e.clientY - rect.top
            };
            
            // 创建选择框
            if (selectionBox) selectionBox.remove();
            selectionBox = document.createElement('div');
            selectionBox.className = 'selection-box';
            selectionBox.style.left = selectionStart.x + 'px';
            selectionBox.style.top = selectionStart.y + 'px';
            container.appendChild(selectionBox);
        }
        
        // 框选移动
        function onSelectionMove(e) {
            if (!isSelecting || !selectionBox) return;
            
            const container = document.getElementById('pdfContainer');
            const rect = container.getBoundingClientRect();
            
            selectionEnd = {
                x: e.clientX - rect.left,
                y: e.clientY - rect.top
            };
            
            const left = Math.min(selectionStart.x, selectionEnd.x);
            const top = Math.min(selectionStart.y, selectionEnd.y);
            const width = Math.abs(selectionEnd.x - selectionStart.x);
            const height = Math.abs(selectionEnd.y - selectionStart.y);
            
            selectionBox.style.left = left + 'px';
            selectionBox.style.top = top + 'px';
            selectionBox.style.width = width + 'px';
            selectionBox.style.height = height + 'px';
        }
        
        // 结束框选
        function onSelectionEnd(e) {
            if (!isSelecting) return;
            isSelecting = false;
            
            // 框选完成后弹出确认对话框
            if (selectionBox && selectedArticleId) {
                showConfirmDialog('是否保存框选的热区坐标？', 
                    () => { saveHotzone(); },  // 确认保存
                    () => { cancelSelection(); }  // 取消，退出框选模式
                );
            }
        }
        
        // 取消框选
        function cancelSelection() {
            isSelectionMode = false;
            isSelecting = false;
            selectedArticleId = null;
            
            const btn = document.getElementById('selectionBtn');
            
            btn.textContent = '📐 框选热区';
            btn.classList.remove('active');
            
            if (selectionBox) {
                selectionBox.remove();
                selectionBox = null;
            }
            
            // 移除事件监听器
            const container = document.getElementById('pdfContainer');
            container.removeEventListener('mousedown', onSelectionStart);
            container.removeEventListener('mousemove', onSelectionMove);
            container.removeEventListener('mouseup', onSelectionEnd);
            
            // 重新渲染文章列表以隐藏 radio 按钮
            renderArticleList();
            
            // 恢复 PDF 信息栏
            const pdfInfo = document.getElementById('pdfInfo');
            if (articles.length > 0) {
                pdfInfo.textContent = `${articles[0].pdf.split('/').pop()} - 第1页`;
            }
        }
        
        // 保存热区坐标
        async function saveHotzone() {
            if (!selectedArticleId || !selectionBox) {
                alert('请先框选热区区域');
                return;
            }
            
            const canvas = document.getElementById('pdfCanvas');
            if (!canvas) {
                alert('PDF未加载');
                return;
            }
            
            // 获取选择框的位置和尺寸（相对于容器）
            const boxLeft = parseInt(selectionBox.style.left);
            const boxTop = parseInt(selectionBox.style.top);
            const boxWidth = parseInt(selectionBox.style.width);
            const boxHeight = parseInt(selectionBox.style.height);
            
            // 获取canvas相对于容器的位置
            const container = document.getElementById('pdfContainer');
            const canvasRect = canvas.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();
            const canvasOffsetX = canvasRect.left - containerRect.left;
            const canvasOffsetY = canvasRect.top - containerRect.top;
            
            // 计算选择框相对于canvas的位置
            const relativeLeft = boxLeft - canvasOffsetX;
            const relativeTop = boxTop - canvasOffsetY;
            const relativeRight = relativeLeft + boxWidth;
            const relativeBottom = relativeTop + boxHeight;
            
            // 从所有文章中计算PDF的实际尺寸
            let maxX = 0, maxY = 0;
            articles.forEach(article => {
                const hz = article.hotzone;
                if (!hz) return;
                const allX = [hz.left_top_x, hz.left_bottom_x, hz.right_bottom_x, hz.right_top_x];
                const allY = [hz.left_top_y, hz.left_bottom_y, hz.right_bottom_y, hz.right_top_y];
                maxX = Math.max(maxX, ...allX);
                maxY = Math.max(maxY, ...allY);
            });
            
            const pdfOriginalWidth = maxX > 0 ? maxX : 1000;
            const pdfOriginalHeight = maxY > 0 ? maxY : 1400;
            
            // 计算实际缩放比例
            const scaleX = canvas.width / pdfOriginalWidth;
            const scaleY = canvas.height / pdfOriginalHeight;
            
            // 将显示坐标转换为原始PDF坐标
            const originalLeft = Math.round(relativeLeft / scaleX);
            const originalTop = Math.round(relativeTop / scaleY);
            const originalRight = Math.round(relativeRight / scaleX);
            const originalBottom = Math.round(relativeBottom / scaleY);
            
            // 构建热区坐标（左上、左下、右下、右上）
            const hotzoneData = {
                left_top_x: originalLeft,
                left_top_y: originalTop,
                left_bottom_x: originalLeft,
                left_bottom_y: originalBottom,
                right_bottom_x: originalRight,
                right_bottom_y: originalBottom,
                right_top_x: originalRight,
                right_top_y: originalTop
            };
            
            try {
                const res = await fetch(`/api/paper/${selectedArticleId}/hotzone`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(hotzoneData)
                });
                const result = await res.json();
                
                if (result.success) {
                    showToast('热区更新成功！', true);
                    // 刷新当前版面以显示新的热区
                    const page = { page_no: currentPage, page_name: articles[0]?.page_name || '', pdf: articles[0]?.pdf || '' };
                    await selectPage(page);
                    cancelSelection();
                } else {
                    showToast('热区更新失败: ' + result.message, false);
                }
            } catch (e) {
                showToast('保存失败: ' + e.message, false);
            }
        }
        
        // 选择版面
        async function selectPage(page) {
            currentPage = formatPageNo(page.page_no);
            
            // 更新标签样式
            const formattedPageNo = formatPageNo(page.page_no);
            document.querySelectorAll('.page-tab').forEach(tab => {
                tab.classList.remove('active');
                if (tab.textContent.includes(`(${formattedPageNo})`)) {
                    tab.classList.add('active');
                }
            });
            
            // 加载PDF
            await loadPDF(page.pdf);
            
            // 加载文章列表
            try {
                const res = await fetch(`/api/papers/${currentDate}/${page.page_no}`);
                articles = await res.json();
                renderArticleList();
                renderHotzones();
            } catch (e) {
                console.error('加载文章失败:', e);
            }
        }
        
        // 加载PDF
        async function loadPDF(pdfPath) {
            const container = document.getElementById('pdfContainer');
            container.innerHTML = '<div class="empty-state"><p>加载PDF中...</p></div>';
            
            try {
                const pdfUrl = `/pdf/${pdfPath}`;
                currentPdf = await pdfjsLib.getDocument(pdfUrl).promise;
                
                const page = await currentPdf.getPage(1);
                
                // 获取容器尺寸，计算自适应缩放比例
                const containerWidth = container.clientWidth - 40; // 减去padding
                const containerHeight = container.clientHeight - 40;
                
                // 获取PDF原始尺寸 (scale=1)
                const originalViewport = page.getViewport({ scale: 1 });
                
                // 计算缩放比例，使PDF适应容器
                const scaleX = containerWidth / originalViewport.width;
                const scaleY = containerHeight / originalViewport.height;
                const scale = Math.min(scaleX, scaleY, 1.5); // 最大放大到1.5倍
                
                currentScale = scale;
                const viewport = page.getViewport({ scale: scale });
                
                pdfDimensions.width = viewport.width;
                pdfDimensions.height = viewport.height;
                
                const canvas = document.createElement('canvas');
                canvas.id = 'pdfCanvas';
                canvas.width = viewport.width;
                canvas.height = viewport.height;
                canvas.style.maxWidth = '100%';
                canvas.style.height = 'auto';
                
                container.innerHTML = '';
                container.appendChild(canvas);
                
                const ctx = canvas.getContext('2d');
                await page.render({ canvasContext: ctx, viewport }).promise;
                
                document.getElementById('pdfInfo').textContent = 
                    `${pdfPath.split('/').pop()} - 第1页 (缩放: ${(scale*100).toFixed(0)}%)`;
            } catch (e) {
                container.innerHTML = '<div class="empty-state"><p>PDF加载失败</p></div>';
                console.error('PDF加载失败:', e);
            }
        }
        
        // 渲染文章列表
        function renderArticleList() {
            const list = document.getElementById('articleList');
            
            if (articles.length === 0) {
                list.innerHTML = '<div class="empty-state"><p>该版面暂无文章</p></div>';
                return;
            }
            
            list.innerHTML = articles.map(article => {
                const isSelected = selectedArticleId === article.id;
                const radioHtml = isSelectionMode ? `
                    <input type="radio" name="articleSelect" value="${article.id}" 
                        ${isSelected ? 'checked' : ''} 
                        onclick="event.stopPropagation(); selectArticleForHotzone(${article.id})"
                        style="margin-right: 8px; cursor: pointer;">
                ` : '';
                const selectedClass = isSelected && isSelectionMode ? 'selected-for-hotzone' : '';
                
                return `
                <div class="article-item ${selectedClass}" data-id="${article.id}" onclick="selectArticle(${article.id})">
                    <div class="article-title" style="display: flex; align-items: center;">
                        ${radioHtml}
                        ${escapeHtml(article.title)}
                        ${article.is_xinhua ? '<span class="tag-xinhua">新华社</span>' : ''}
                        ${article.is_pic ? '<span class="tag-pic">图片</span>' : ''}
                    </div>
                    <div class="article-meta">
                        <span>✍️ ${article.author || '无'}</span>
                        ${article.collaborator ? `<span>📢 ${article.collaborator}</span>` : ''}
                        ${article.photo ? `<span>📷 ${article.photo}</span>` : ''}
                    </div>
                </div>
            `}).join('');
        }
        
        // 渲染热区
        function renderHotzones() {
            const container = document.getElementById('pdfContainer');
            const canvas = document.getElementById('pdfCanvas');
            if (!canvas) return;
            
            // 清除旧的热区
            container.querySelectorAll('.hotzone-overlay').forEach(el => el.remove());
            
            // 获取canvas相对于container的位置
            const canvasRect = canvas.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();
            const canvasOffsetX = canvasRect.left - containerRect.left;
            const canvasOffsetY = canvasRect.top - containerRect.top;
            
            // 从所有文章中计算PDF的实际尺寸
            let maxX = 0, maxY = 0;
            articles.forEach(article => {
                const hz = article.hotzone;
                if (!hz) return;
                const allX = [hz.left_top_x, hz.left_bottom_x, hz.right_bottom_x, hz.right_top_x];
                const allY = [hz.left_top_y, hz.left_bottom_y, hz.right_bottom_y, hz.right_top_y];
                maxX = Math.max(maxX, ...allX);
                maxY = Math.max(maxY, ...allY);
            });
            
            // 使用实际的最大坐标作为PDF尺寸基准
            // 如果数据库中有坐标数据，使用最大坐标值；否则使用默认值
            const pdfOriginalWidth = maxX > 0 ? maxX : 1000;
            const pdfOriginalHeight = maxY > 0 ? maxY : 1400;
            
            // 计算实际缩放比例 = 当前显示尺寸 / 原始尺寸
            const scaleX = canvas.width / pdfOriginalWidth;
            const scaleY = canvas.height / pdfOriginalHeight;
            
            articles.forEach(article => {
                const hz = article.hotzone;
                if (!hz || hz.left_top_x === 0) return;
                
                const overlay = document.createElement('div');
                overlay.className = 'hotzone-overlay';
                overlay.dataset.id = article.id;
                
                // 热区坐标顺序：左上、左下、右下、右上
                // PDF坐标原点在左上角，与CSS坐标系一致
                // 计算热区的边界框
                const allX = [hz.left_top_x, hz.left_bottom_x, hz.right_bottom_x, hz.right_top_x];
                const allY = [hz.left_top_y, hz.left_bottom_y, hz.right_bottom_y, hz.right_top_y];
                
                const minX = Math.min(...allX);
                const maxX_local = Math.max(...allX);
                const minY = Math.min(...allY);
                const maxY_local = Math.max(...allY);
                
                const width = maxX_local - minX;
                const height = maxY_local - minY;
                
                // 将原始坐标转换为显示坐标（相对于PDF内容的左上角）
                // PDF坐标原点在左上角，与CSS坐标系一致，无需翻转Y轴
                const displayX = minX * scaleX + canvasOffsetX;
                const displayY = minY * scaleY + canvasOffsetY;
                const displayWidth = width * scaleX;
                const displayHeight = height * scaleY;
                
                overlay.style.left = displayX + 'px';
                overlay.style.top = displayY + 'px';
                overlay.style.width = displayWidth + 'px';
                overlay.style.height = displayHeight + 'px';
                
                overlay.onclick = (e) => {
                    e.stopPropagation();
                    selectArticle(article.id);
                };
                
                container.appendChild(overlay);
            });
        }
        
        // 选择文章（用于框选热区）
        function selectArticleForHotzone(id) {
            selectedArticleId = id;
            const article = articles.find(a => a.id === id);
            if (article) {
                // 重新渲染列表以更新选中状态
                renderArticleList();
                // 显示提示
                const info = document.getElementById('pdfInfo');
                info.innerHTML = `已选择: ${escapeHtml(article.title.substring(0, 20))}${article.title.length > 20 ? '...' : ''} - 请在PDF上拖拽绘制热区`;
            }
        }
        
        // 选择文章
        async function selectArticle(id) {
            currentArticleId = id;
            
            // 高亮列表项
            document.querySelectorAll('.article-item').forEach(item => {
                item.classList.toggle('active', parseInt(item.dataset.id) === id);
            });
            
            // 高亮热区
            document.querySelectorAll('.hotzone-overlay').forEach(zone => {
                zone.classList.toggle('active', parseInt(zone.dataset.id) === id);
            });
            
            // 加载详情
            try {
                const res = await fetch(`/api/paper/${id}`);
                const article = await res.json();
                showModal(article);
            } catch (e) {
                console.error('加载文章详情失败:', e);
            }
        }
        
        // 显示详情弹窗
        function showModal(article) {
            document.getElementById('modalTitle').innerHTML = `
                ${escapeHtml(article.title)}
                ${article.is_xinhua ? '<span class="tag-xinhua">新华社</span>' : ''}
                ${article.is_pic ? '<span class="tag-pic">图片</span>' : ''}
            `;
            document.getElementById('modalContent').innerHTML = `
                <div style="margin-bottom: 15px; color: #666; font-size: 13px;">
                    <span>✍️ ${article.author || '无'}</span>
                    ${article.collaborator ? `<span style="margin-left: 15px;">📢 ${article.collaborator}</span>` : ''}
                    ${article.photo ? `<span style="margin-left: 15px;">📷 ${article.photo}</span>` : ''}
                    <span style="margin-left: 15px;">📄 ${article.page_name}</span>
                </div>
                <div>${escapeHtml(article.content).replace(/\\n/g, '<br>')}</div>
            `;
            
            // 填充编辑表单
            document.getElementById('editTitle').value = article.title;
            document.getElementById('editAuthor').value = article.author || '';
            document.getElementById('editCollaborator').value = article.collaborator || '';
            document.getElementById('editPhoto').value = article.photo || '';
            document.getElementById('editContent').value = article.content;
            
            document.getElementById('contentModal').classList.add('active');
            document.getElementById('editForm').classList.remove('active');
            document.getElementById('modalContent').style.display = 'block';
        }
        
        // 关闭弹窗
        function closeModal() {
            document.getElementById('contentModal').classList.remove('active');
            currentArticleId = null;
            
            // 取消高亮
            document.querySelectorAll('.article-item').forEach(item => item.classList.remove('active'));
            document.querySelectorAll('.hotzone-overlay').forEach(zone => zone.classList.remove('active'));
        }
        
        // 切换编辑模式
        function toggleEdit() {
            const editForm = document.getElementById('editForm');
            const modalContent = document.getElementById('modalContent');
            
            if (editForm.classList.contains('active')) {
                editForm.classList.remove('active');
                modalContent.style.display = 'block';
            } else {
                editForm.classList.add('active');
                modalContent.style.display = 'none';
            }
        }
        
        // 保存编辑
        async function saveEdit() {
            if (!currentArticleId) return;
            
            const data = {
                title: document.getElementById('editTitle').value,
                author: document.getElementById('editAuthor').value,
                collaborator: document.getElementById('editCollaborator').value,
                photo: document.getElementById('editPhoto').value,
                content: document.getElementById('editContent').value,
                page_no: currentPage,
                page_name: articles.find(a => a.id === currentArticleId)?.page_name || '',
                site_id: 1,
                is_xinhua: 0,
                is_pic: 0
            };
            
            try {
                const res = await fetch(`/api/paper/${currentArticleId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await res.json();
                
                if (result.success) {
                    alert('保存成功');
                    // 刷新当前版面
                    const page = { page_no: currentPage, page_name: data.page_name, pdf: articles[0]?.pdf || '' };
                    await selectPage(page);
                    closeModal();
                } else {
                    alert('保存失败: ' + result.message);
                }
            } catch (e) {
                alert('保存失败');
            }
        }
        
        // HTML转义
        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // 点击弹窗外部关闭
        document.getElementById('contentModal').onclick = (e) => {
            if (e.target.id === 'contentModal') closeModal();
        };
        
        // 获取今天日期
        function getTodayDate() {
            const today = new Date();
            const year = today.getFullYear();
            const month = String(today.getMonth() + 1).padStart(2, '0');
            const day = String(today.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        }
        
        // 自动加载今天
        async function autoLoadToday() {
            await loadDates();
            const today = getTodayDate();
            const dateInput = document.getElementById('dateSelect');
            
            // 检查今天是否在可选范围内
            if (today >= dateInput.min && today <= dateInput.max) {
                dateInput.value = today;
                await loadDate(today);
            }
        }
        
        // 初始化
        autoLoadToday();
    </script>
</body>
</html>
'''

VIEW_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>舟山日报 - 浏览</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #e8e8e8;
            min-height: 100vh;
            padding: 20px;
        }
        .app-wrapper {
            max-width: 1400px;
            margin: 0 auto;
            background: #f0f2f5;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            overflow: hidden;
            height: calc(100vh - 40px);
            display: flex;
            flex-direction: column;
        }
        .header {
            background: #fff;
            padding: 10px 20px;
            border-bottom: 1px solid #e8e8e8;
            display: flex;
            gap: 15px;
            align-items: center;
            height: 60px;
            flex-shrink: 0;
        }
        .header h1 { 
            font-size: 18px; 
            color: #333;
            margin-right: 20px;
        }
        .header input[type="date"] {
            padding: 6px 12px;
            border: 1px solid #d9d9d9;
            border-radius: 4px;
            font-size: 14px;
        }
        .header .login-link {
            margin-left: auto;
            color: #1890ff;
            text-decoration: none;
            font-size: 14px;
        }
        .header .login-link:hover {
            text-decoration: underline;
        }
        .main-container {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        .left-panel {
            flex: 1;
            background: #333;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .pdf-toolbar {
            background: #444;
            padding: 10px;
            display: flex;
            gap: 10px;
            align-items: center;
            color: #fff;
        }
        .pdf-container {
            flex: 1;
            overflow: auto;
            position: relative;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            padding: 20px;
        }
        #pdfCanvas {
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        }
        .hotzone-overlay {
            position: absolute;
            border: 2px solid transparent;
            cursor: pointer;
            transition: all 0.2s;
        }
        .hotzone-overlay:hover {
            border-color: #1890ff;
            background: rgba(24, 144, 255, 0.1);
        }
        .hotzone-overlay.active {
            border-color: #ff4d4f;
            background: rgba(255, 77, 79, 0.1);
        }
        .right-panel {
            width: 400px;
            background: #fff;
            border-left: 1px solid #e8e8e8;
            display: flex;
            flex-direction: column;
        }
        .page-tabs {
            display: flex;
            overflow-x: auto;
            border-bottom: 1px solid #e8e8e8;
            background: #fafafa;
        }
        .page-tab {
            padding: 12px 20px;
            cursor: pointer;
            white-space: nowrap;
            border-right: 1px solid #e8e8e8;
            font-size: 13px;
        }
        .page-tab:hover { background: #e6f7ff; }
        .page-tab.active { 
            background: #1890ff; 
            color: white;
        }
        .article-list {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }
        .article-item {
            padding: 12px;
            border: 1px solid #e8e8e8;
            border-radius: 4px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .article-item:hover {
            border-color: #1890ff;
            background: #e6f7ff;
        }
        .article-item.active {
            border-color: #ff4d4f;
            background: #fff1f0;
        }
        .article-title {
            font-weight: bold;
            color: #333;
            margin-bottom: 6px;
            font-size: 14px;
        }
        .article-meta {
            font-size: 12px;
            color: #666;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .article-meta span {
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
        }
        .tag-xinhua { 
            background: #fff2e8 !important; 
            color: #fa8c16; 
        }
        .tag-pic { 
            background: #f6ffed !important; 
            color: #52c41a; 
        }
        .content-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .content-modal.active { display: flex; }
        .content-panel {
            background: white;
            width: 80%;
            max-width: 800px;
            height: 80%;
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .content-header {
            padding: 20px;
            border-bottom: 1px solid #e8e8e8;
            display: flex;
            justify-content: space-between;
            align-items: start;
        }
        .content-title {
            font-size: 18px;
            font-weight: bold;
            color: #333;
            flex: 1;
            margin-right: 20px;
        }
        .content-actions {
            display: flex;
            gap: 10px;
        }
        .content-body {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            line-height: 1.8;
            font-size: 15px;
            color: #333;
        }
        .close-btn {
            background: transparent;
            color: #999;
            border: none;
            font-size: 24px;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.2s;
            padding: 0;
            line-height: 1;
        }
        .close-btn:hover {
            background: #f5f5f5;
            color: #666;
        }
        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="app-wrapper">
        <div class="header">
            <h1>📰 舟山日报 - 浏览模式</h1>
            <input type="date" id="dateSelect" onchange="onDateChange()">
            <a href="/login" class="login-link">管理员登录 →</a>
        </div>
        
        <div class="main-container">
        <div class="left-panel">
            <div class="pdf-toolbar">
                <span id="pdfInfo">请选择日期加载PDF</span>
            </div>
            <div class="pdf-container" id="pdfContainer">
                <div class="empty-state">
                    <p>请选择日期加载数据</p>
                </div>
            </div>
        </div>
        
        <div class="right-panel">
            <div class="page-tabs" id="pageTabs"></div>
            <div class="article-list" id="articleList">
                <div class="empty-state">
                    <p>请选择日期和版面</p>
                </div>
            </div>
        </div>
        </div>
    </div>
    
    <div class="content-modal" id="contentModal">
        <div class="content-panel">
            <div class="content-header">
                <div class="content-title" id="modalTitle"></div>
                <div class="content-actions">
                    <button class="close-btn" onclick="closeModal()" title="关闭">×</button>
                </div>
            </div>
            <div class="content-body" id="modalContent"></div>
        </div>
    </div>

    <script>
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        
        let currentDate = '';
        let currentPage = '';
        let currentPdf = null;
        let currentScale = 1.5;
        let articles = [];
        let currentArticleId = null;
        let pdfDimensions = { width: 0, height: 0 };

        // 加载日期列表并设置日期选择器的范围
        async function loadDates() {
            try {
                const res = await fetch('/api/dates');
                const dates = await res.json();
                const dateInput = document.getElementById('dateSelect');
                
                if (dates.length > 0) {
                    dateInput.min = dates[dates.length - 1];
                    dateInput.max = dates[0];
                }
            } catch (e) {
                console.error('加载日期失败:', e);
            }
        }

        // 日期选择变化时自动加载
        async function onDateChange() {
            const date = document.getElementById('dateSelect').value;
            if (!date) return;
            await loadDate(date);
        }

        // 加载指定日期的数据
        async function loadDate(date) {
            if (!date) return;
            currentDate = date;
            
            try {
                const res = await fetch(`/api/pages/${date}`);
                const pages = await res.json();
                renderPageTabs(pages);
            } catch (e) {
                console.error('加载版面失败:', e);
            }
        }

        // 渲染版面标签
        function renderPageTabs(pages) {
            const tabs = document.getElementById('pageTabs');
            tabs.innerHTML = '';
            
            pages.forEach((page, index) => {
                const tab = document.createElement('div');
                tab.className = 'page-tab' + (index === 0 ? ' active' : '');
                const formattedPageNo = formatPageNo(page.page_no);
                tab.textContent = `${page.page_name} (${formattedPageNo})`;
                tab.onclick = () => selectPage(page);
                tabs.appendChild(tab);
            });
            
            if (pages.length > 0) {
                selectPage(pages[0]);
            }
        }

        // 格式化版面号为 0x 格式
        function formatPageNo(pageNo) {
            try {
                const num = parseInt(pageNo);
                return String(num).padStart(2, '0');
            } catch (e) {
                return pageNo || '00';
            }
        }

        // 选择版面
        async function selectPage(page) {
            currentPage = formatPageNo(page.page_no);
            
            const formattedPageNo = formatPageNo(page.page_no);
            document.querySelectorAll('.page-tab').forEach(tab => {
                tab.classList.remove('active');
                if (tab.textContent.includes(`(${formattedPageNo})`)) {
                    tab.classList.add('active');
                }
            });
            
            await loadPDF(page.pdf);
            
            try {
                const res = await fetch(`/api/papers/${currentDate}/${page.page_no}`);
                articles = await res.json();
                renderArticleList();
                renderHotzones();
            } catch (e) {
                console.error('加载文章失败:', e);
            }
        }

        // 加载PDF
        async function loadPDF(pdfPath) {
            const container = document.getElementById('pdfContainer');
            container.innerHTML = '<div class="empty-state"><p>加载PDF中...</p></div>';
            
            try {
                const pdfUrl = `/pdf/${pdfPath}`;
                currentPdf = await pdfjsLib.getDocument(pdfUrl).promise;
                
                const page = await currentPdf.getPage(1);
                
                const containerWidth = container.clientWidth - 40;
                const containerHeight = container.clientHeight - 40;
                
                const originalViewport = page.getViewport({ scale: 1 });
                
                const scaleX = containerWidth / originalViewport.width;
                const scaleY = containerHeight / originalViewport.height;
                const scale = Math.min(scaleX, scaleY, 1.5);
                
                currentScale = scale;
                const viewport = page.getViewport({ scale: scale });
                
                pdfDimensions.width = viewport.width;
                pdfDimensions.height = viewport.height;
                
                const canvas = document.createElement('canvas');
                canvas.id = 'pdfCanvas';
                canvas.width = viewport.width;
                canvas.height = viewport.height;
                canvas.style.maxWidth = '100%';
                canvas.style.height = 'auto';
                
                container.innerHTML = '';
                container.appendChild(canvas);
                
                const ctx = canvas.getContext('2d');
                await page.render({ canvasContext: ctx, viewport }).promise;
                
                document.getElementById('pdfInfo').textContent = 
                    `${pdfPath.split('/').pop()} - 第1页 (缩放: ${(scale*100).toFixed(0)}%)`;
            } catch (e) {
                container.innerHTML = '<div class="empty-state"><p>PDF加载失败</p></div>';
                console.error('PDF加载失败:', e);
            }
        }

        // 渲染文章列表
        function renderArticleList() {
            const list = document.getElementById('articleList');
            
            if (articles.length === 0) {
                list.innerHTML = '<div class="empty-state"><p>该版面暂无文章</p></div>';
                return;
            }
            
            list.innerHTML = articles.map(article => `
                <div class="article-item" data-id="${article.id}" onclick="selectArticle(${article.id})">
                    <div class="article-title">
                        ${escapeHtml(article.title)}
                        ${article.is_xinhua ? '<span class="tag-xinhua">新华社</span>' : ''}
                        ${article.is_pic ? '<span class="tag-pic">图片</span>' : ''}
                    </div>
                    <div class="article-meta">
                        <span>✍️ ${article.author || '无'}</span>
                        ${article.collaborator ? `<span>📢 ${article.collaborator}</span>` : ''}
                        ${article.photo ? `<span>📷 ${article.photo}</span>` : ''}
                    </div>
                </div>
            `).join('');
        }

        // 渲染热区
        function renderHotzones() {
            const container = document.getElementById('pdfContainer');
            const canvas = document.getElementById('pdfCanvas');
            if (!canvas) return;
            
            container.querySelectorAll('.hotzone-overlay').forEach(el => el.remove());
            
            const canvasRect = canvas.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();
            const canvasOffsetX = canvasRect.left - containerRect.left;
            const canvasOffsetY = canvasRect.top - containerRect.top;
            
            let maxX = 0, maxY = 0;
            articles.forEach(article => {
                const hz = article.hotzone;
                if (!hz) return;
                const allX = [hz.left_top_x, hz.left_bottom_x, hz.right_bottom_x, hz.right_top_x];
                const allY = [hz.left_top_y, hz.left_bottom_y, hz.right_bottom_y, hz.right_top_y];
                maxX = Math.max(maxX, ...allX);
                maxY = Math.max(maxY, ...allY);
            });
            
            const pdfOriginalWidth = maxX > 0 ? maxX : 1000;
            const pdfOriginalHeight = maxY > 0 ? maxY : 1400;
            
            const scaleX = canvas.width / pdfOriginalWidth;
            const scaleY = canvas.height / pdfOriginalHeight;
            
            articles.forEach(article => {
                const hz = article.hotzone;
                if (!hz || hz.left_top_x === 0) return;
                
                const overlay = document.createElement('div');
                overlay.className = 'hotzone-overlay';
                overlay.dataset.id = article.id;
                
                const allX = [hz.left_top_x, hz.left_bottom_x, hz.right_bottom_x, hz.right_top_x];
                const allY = [hz.left_top_y, hz.left_bottom_y, hz.right_bottom_y, hz.right_top_y];
                
                const minX = Math.min(...allX);
                const maxX_local = Math.max(...allX);
                const minY = Math.min(...allY);
                const maxY_local = Math.max(...allY);
                
                const width = maxX_local - minX;
                const height = maxY_local - minY;
                
                const displayX = minX * scaleX + canvasOffsetX;
                const displayY = minY * scaleY + canvasOffsetY;
                const displayWidth = width * scaleX;
                const displayHeight = height * scaleY;
                
                overlay.style.left = displayX + 'px';
                overlay.style.top = displayY + 'px';
                overlay.style.width = displayWidth + 'px';
                overlay.style.height = displayHeight + 'px';
                
                overlay.onclick = (e) => {
                    e.stopPropagation();
                    selectArticle(article.id);
                };
                
                container.appendChild(overlay);
            });
        }

        // 选择文章
        async function selectArticle(id) {
            currentArticleId = id;
            
            document.querySelectorAll('.article-item').forEach(item => {
                item.classList.toggle('active', parseInt(item.dataset.id) === id);
            });
            
            document.querySelectorAll('.hotzone-overlay').forEach(zone => {
                zone.classList.toggle('active', parseInt(zone.dataset.id) === id);
            });
            
            try {
                const res = await fetch(`/api/paper/${id}`);
                const article = await res.json();
                showModal(article);
            } catch (e) {
                console.error('加载文章详情失败:', e);
            }
        }

        // 显示详情弹窗
        function showModal(article) {
            document.getElementById('modalTitle').innerHTML = `
                ${escapeHtml(article.title)}
                ${article.is_xinhua ? '<span class="tag-xinhua">新华社</span>' : ''}
                ${article.is_pic ? '<span class="tag-pic">图片</span>' : ''}
            `;
            document.getElementById('modalContent').innerHTML = `
                <div style="margin-bottom: 15px; color: #666; font-size: 13px;">
                    <span>✍️ ${article.author || '无'}</span>
                    ${article.collaborator ? `<span style="margin-left: 15px;">📢 ${article.collaborator}</span>` : ''}
                    ${article.photo ? `<span style="margin-left: 15px;">📷 ${article.photo}</span>` : ''}
                    <span style="margin-left: 15px;">📄 ${article.page_name}</span>
                </div>
                <div>${escapeHtml(article.content).replace(/\\n/g, '<br>')}</div>
            `;
            
            document.getElementById('contentModal').classList.add('active');
        }

        // 关闭弹窗
        function closeModal() {
            document.getElementById('contentModal').classList.remove('active');
            currentArticleId = null;
            
            document.querySelectorAll('.article-item').forEach(item => item.classList.remove('active'));
            document.querySelectorAll('.hotzone-overlay').forEach(zone => zone.classList.remove('active'));
        }

        // HTML转义
        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // 点击弹窗外部关闭
        document.getElementById('contentModal').onclick = (e) => {
            if (e.target.id === 'contentModal') closeModal();
        };

        // 获取今天日期
        function getTodayDate() {
            const today = new Date();
            const year = today.getFullYear();
            const month = String(today.getMonth() + 1).padStart(2, '0');
            const day = String(today.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        }

        // 自动加载今天
        async function autoLoadToday() {
            await loadDates();
            const today = getTodayDate();
            const dateInput = document.getElementById('dateSelect');
            
            if (today >= dateInput.min && today <= dateInput.max) {
                dateInput.value = today;
                await loadDate(today);
            }
        }

        // 初始化
        autoLoadToday();
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
