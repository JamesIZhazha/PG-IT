import os, sqlite3, json, time, hashlib, hmac, base64
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, g, request, redirect, url_for, render_template, session, send_file, jsonify, flash
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import qrcode
from io import BytesIO


APP_SECRET = os.environ.get("CM_SECRET", "change-me-secret")  # HMAC 密钥
DB_PATH = "classmint.db"

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-key")
bcrypt = Bcrypt(app)

# 配置CORS，允许所有来源的跨域请求
CORS(app, origins=['*'], methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

# 添加Jinja2过滤器
@app.template_filter('from_json')
def from_json_filter(value):
    """将JSON字符串转换为Python对象"""
    try:
        return json.loads(value) if value else None
    except (json.JSONDecodeError, TypeError):
        return None

@app.template_filter('timestamp_to_datetime')
def timestamp_to_datetime_filter(timestamp):
    """将时间戳转换为可读的日期时间格式"""
    try:
        if timestamp:
            dt = datetime.fromtimestamp(int(timestamp))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        return 'N/A'
    except (ValueError, TypeError):
        return 'N/A'

# Database connection
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
    return g.db

from datetime import datetime

@app.template_filter("datetime")
def _fmt(ts: int):
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "-"


@app.teardown_appcontext
def close_db(_e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE, password_hash TEXT
    );
    CREATE TABLE IF NOT EXISTS tokens (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      token TEXT UNIQUE, amount INTEGER, one_time INTEGER,
      expires_at INTEGER, issued_by INTEGER, status TEXT DEFAULT 'ACTIVE',
      created_at INTEGER, description TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS claims (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      token_id INTEGER, claimer TEXT, amount INTEGER, created_at INTEGER
    );
    CREATE TABLE IF NOT EXISTS ledger (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      tx_id INTEGER, prev_hash TEXT, record_hash TEXT, created_at INTEGER,
      block_data TEXT
    );
    CREATE TABLE IF NOT EXISTS user_balances (
      user_id INTEGER PRIMARY KEY,
      balance INTEGER DEFAULT 0,
      updated_at INTEGER
    );
    CREATE TABLE IF NOT EXISTS shop_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      description TEXT,
      price INTEGER NOT NULL,
      category TEXT DEFAULT 'general',
      image_url TEXT,
      stock INTEGER DEFAULT -1,
      status TEXT DEFAULT 'ACTIVE',
      created_at INTEGER,
      updated_at INTEGER
    );
    CREATE TABLE IF NOT EXISTS purchases (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      item_id INTEGER NOT NULL,
      quantity INTEGER DEFAULT 1,
      total_price INTEGER NOT NULL,
      status TEXT DEFAULT 'COMPLETED',
      created_at INTEGER,
      FOREIGN KEY (user_id) REFERENCES users(id),
      FOREIGN KEY (item_id) REFERENCES shop_items(id)
    );
    """)
    
    # Check and add missing columns
    try:
        db.execute("SELECT description FROM tokens LIMIT 1")
    except sqlite3.OperationalError:
        db.execute("ALTER TABLE tokens ADD COLUMN description TEXT DEFAULT ''")
    
    try:
        db.execute("SELECT block_data FROM ledger LIMIT 1")
    except sqlite3.OperationalError:
        db.execute("ALTER TABLE ledger ADD COLUMN block_data TEXT")
    
    # Default admin
    u = db.execute("SELECT 1 FROM users WHERE username='admin'").fetchone()
    if not u:
        pw = bcrypt.generate_password_hash("admin123").decode()
        db.execute("INSERT INTO users (username, password_hash) VALUES (?,?)", ("admin", pw))
        db.commit()
        print("已创建默认教师账号: admin / admin123")
    
    # Default students
    students = [
        ("student1", "student123"),
        ("student2", "student123"), 
        ("student3", "student123")
    ]
    
    for username, password in students:
        u = db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone()
        if not u:
            pw = bcrypt.generate_password_hash(password).decode()
            db.execute("INSERT INTO users (username, password_hash) VALUES (?,?)", (username, pw))
            db.commit()
    
    if students:
        print("已创建默认学生账号: student1,student2,student3 / student123")
    
    # Initialize student account balances
    db.execute("INSERT OR IGNORE INTO user_balances (user_id, balance, updated_at) VALUES (1, 0, ?)", (now_ts(),))
    db.commit()
    
    # Initialize default shop items
    default_items = [
        ("🍎 Apple", "Fresh red apple", 500, "food", None, 50),
        ("📚 Book", "Educational book", 2000, "education", None, 20),
        ("🎁 Gift Card", "Special gift card", 1000, "general", None, 100),
        ("☕ Coffee", "Hot coffee", 800, "food", None, 30),
        ("🎮 Game Time", "Extra game time", 1500, "entertainment", None, -1),
        ("🏆 Trophy", "Achievement trophy", 3000, "reward", None, 10)
    ]
    
    for name, description, price, category, image_url, stock in default_items:
        existing = db.execute("SELECT 1 FROM shop_items WHERE name=?", (name,)).fetchone()
        if not existing:
            db.execute("""
                INSERT INTO shop_items (name, description, price, category, image_url, stock, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, description, price, category, image_url, stock, now_ts(), now_ts()))
            db.commit()

# Authentication
def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not session.get("uid"):
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrapper

# Utility functions
def now_ts(): return int(time.time())
def sha256(s: bytes) -> str: return hashlib.sha256(s).hexdigest()
def b64url(data: bytes) -> str: return base64.urlsafe_b64encode(data).decode().rstrip("=")
def sign_payload(payload: dict) -> str:
    """Generate token: CM1.<payload_b64>.<sig>"""
    p = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    sig = hmac.new(APP_SECRET.encode(), p, hashlib.sha256).digest()
    return f"CM1.{b64url(p)}.{b64url(sig)}"

def verify_token_sig(token: str) -> dict | None:
    try:
        prefix, p64, s64 = token.split(".")
        if prefix != "CM1": return None
        p = base64.urlsafe_b64decode(p64 + "==")
        s = base64.urlsafe_b64decode(s64 + "==")
        if not hmac.compare_digest(hmac.new(APP_SECRET.encode(), p, hashlib.sha256).digest(), s):
            return None
        return json.loads(p.decode())
    except Exception:
        return None

def add_block(tx_id: int, claim_data: dict = None):
    """Add new block to blockchain"""
    db = get_db()
    prev = db.execute("SELECT record_hash FROM ledger ORDER BY id DESC LIMIT 1").fetchone()
    prev_hash = prev["record_hash"] if prev else ""
    
    # 使用统一的时间戳
    current_time = now_ts()
    
    # Build block data
    block_data = {
        "tx_id": tx_id,
        "timestamp": current_time,
        "prev_hash": prev_hash,
        "claim_data": claim_data
    }
    
    payload = json.dumps(block_data, separators=(",", ":"))
    # 修复：使用相同的时间戳进行哈希计算
    record_hash = sha256((prev_hash + payload + str(current_time)).encode())
    
    db.execute("INSERT INTO ledger (tx_id, prev_hash, record_hash, created_at, block_data) VALUES (?,?,?,?,?)",
               (tx_id, prev_hash, record_hash, current_time, payload))
    db.commit()
    return record_hash

# Page routes
@app.route("/login", methods=["GET","POST"])
def login():
    init_db()
    if request.method == "POST":
        username = request.form.get("username","")
        password = request.form.get("password","")
        db = get_db()
        row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if row and bcrypt.check_password_hash(row["password_hash"], password):
            session["uid"] = row["id"]; session["uname"] = row["username"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    tokens = db.execute("SELECT * FROM tokens ORDER BY id DESC LIMIT 50").fetchall()
    claims = db.execute("SELECT c.*, t.token FROM claims c LEFT JOIN tokens t ON t.id=c.token_id ORDER BY c.id DESC LIMIT 20").fetchall()
    
    # Get statistics
    total_tokens = db.execute("SELECT COUNT(*) as count FROM tokens").fetchone()["count"]
    total_claims = db.execute("SELECT COUNT(*) as count FROM claims").fetchone()["count"]
    active_amount = db.execute("SELECT COALESCE(SUM(amount), 0) as total FROM tokens WHERE status='ACTIVE'").fetchone()["total"]
    blockchain_length = db.execute("SELECT COUNT(*) as count FROM ledger").fetchone()["count"]
    
    # Get page parameter
    page = request.args.get('page', 'dashboard')
    
    # If page is records, get additional data
    purchases = None
    if page == 'records':
        purchases = db.execute("""
            SELECT 
                p.id, p.user_id, p.item_id, p.quantity, p.total_price, p.status, p.created_at,
                u.username, si.name as item_name, si.category, si.price
            FROM purchases p
            LEFT JOIN users u ON p.user_id = u.id
            LEFT JOIN shop_items si ON p.item_id = si.id
            ORDER BY p.created_at DESC
        """).fetchall()
    
    return render_template("dashboard_new.html", 
                         tokens=tokens, 
                         claims=claims, 
                         purchases=purchases,
                         uname=session.get("uname"),
                         current_page=page,
                         stats={
                             "total_tokens": total_tokens,
                             "total_claims": total_claims,
                             "active_amount": active_amount,
                             "blockchain_length": blockchain_length
                         })

@app.route("/token/new", methods=["POST"])
@login_required
def token_new():
    try:
        # Convert amount from yuan to cents
        amount_yuan = float(request.form.get("amount", "0"))
        amount_cents = int(amount_yuan * 100)
        
        if amount_cents <= 0:
            flash("Amount must be greater than 0")
            return redirect(url_for("dashboard"))
            
        one_time = 1  # 所有令牌都是一次性的，符合区块链特性
        minutes = int(request.form.get("expire_minutes", "60"))
        description = request.form.get("description", "").strip()
        
        if minutes <= 0:
            flash("Expiration time must be greater than 0 minutes")
            return redirect(url_for("dashboard"))
        
        payload = {
            "amount": amount_cents, 
            "one": one_time, 
            "exp": now_ts() + minutes*60, 
            "nonce": sha256(os.urandom(16)),
            "desc": description
        }
        
        token_str = sign_payload(payload)
        db = get_db()
        db.execute("INSERT INTO tokens (token, amount, one_time, expires_at, issued_by, status, created_at, description) VALUES (?,?,?,?,?,?,?,?)",
                   (token_str, amount_cents, one_time, payload["exp"], session["uid"], "ACTIVE", now_ts(), description))
        db.commit()
        
        flash(f"Successfully generated ¥{amount_yuan:.2f} reward token!")
        return redirect(url_for("dashboard"))
        
    except ValueError:
        flash("Please enter a valid amount")
        return redirect(url_for("dashboard"))
    except Exception as e:
        flash(f"Failed to generate token: {str(e)}")
        return redirect(url_for("dashboard"))

@app.route("/token/qr/<int:token_id>")
@login_required
def token_qr(token_id:int):
    db = get_db()
    row = db.execute("SELECT token FROM tokens WHERE id=?", (token_id,)).fetchone()
    if not row: return "Not found", 404
    
    # Generate QR code
    url_text = f"https://classmint.local/claim?token={row['token']}"
    img = qrcode.make(url_text)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

@app.route("/qr/<token_str>")
@login_required
def qr_by_token(token_str: str):
    """Generate QR code by token string (for template compatibility)"""
    db = get_db()
    row = db.execute("SELECT token FROM tokens WHERE token=?", (token_str,)).fetchone()
    if not row: return "Not found", 404
    
    # Generate QR code
    url_text = f"https://classmint.local/claim?token={row['token']}"
    img = qrcode.make(url_text)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

@app.route("/token/void/<int:token_id>", methods=["POST"])
@login_required
def token_void(token_id:int):
    db = get_db()
    db.execute("UPDATE tokens SET status='VOID' WHERE id=? AND status='ACTIVE'", (token_id,))
    db.commit()
    flash("Token has been voided")
    return redirect(url_for("dashboard"))

@app.route("/blockchain")
@login_required
def blockchain_view():
    """Blockchain visualization page"""
    db = get_db()
    blocks = db.execute("SELECT * FROM ledger ORDER BY id ASC").fetchall()
    return render_template("blockchain.html", blocks=blocks, uname=session.get("uname"))

@app.route("/token-records")
@login_required
def token_records_view():
    """Token records page - redirects to dashboard with records page active"""
    return redirect(url_for("dashboard", page="records"))

# API endpoints
@app.route("/api/token/create", methods=["POST"])
def api_token_create():
    # Authentication required: header X-Admin-Key = APP_SECRET
    if request.headers.get("X-Admin-Key") != APP_SECRET:
        return jsonify({"detail":"unauthorized"}), 401
    
    try:
        data = request.get_json(force=True)
        amount_yuan = float(data.get("amount", 0))
        amount_cents = int(amount_yuan * 100)
        
        if amount_cents <= 0:
            return jsonify({"detail": "amount must be positive"}), 400
            
        one_time = 1  # 所有令牌都是一次性的，符合区块链特性
        minutes = int(data.get("expire_minutes", 60))
        description = data.get("description", "")
        
        if minutes <= 0:
            return jsonify({"detail": "expire_minutes must be positive"}), 400
        
        payload = {
            "amount": amount_cents, 
            "one": one_time, 
            "exp": now_ts() + minutes*60, 
            "nonce": sha256(os.urandom(16)),
            "desc": description
        }
        
        token_str = sign_payload(payload)
        db = get_db()
        db.execute("INSERT INTO tokens (token, amount, one_time, expires_at, issued_by, status, created_at, description) VALUES (?,?,?,?,?,?,?,?)",
                   (token_str, amount_cents, one_time, payload["exp"], 0, "ACTIVE", now_ts(), description))
        db.commit()
        tid = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        
        return jsonify({
            "token_id": tid, 
            "token": token_str,
            "amount_yuan": amount_yuan,
            "expires_at": payload["exp"]
        })
        
    except ValueError:
        return jsonify({"detail": "invalid amount"}), 400
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@app.route("/api/claim", methods=["POST"])
def api_claim():
    """Claim token"""
    try:
        data = request.get_json(force=True)
        token_str = (data.get("token") or "").strip()
        claimer = str(data.get("user_id") or data.get("claimer") or "unknown")

        if not token_str:
            return jsonify({"detail": "token is required"}), 400

        db = get_db()
        
        try:
            db.execute("BEGIN TRANSACTION")
            t = db.execute("SELECT * FROM tokens WHERE token=?", (token_str,)).fetchone()
            
            if not t: 
                db.rollback()
                return jsonify({"detail":"invalid token"}), 400
            if t["status"] != "ACTIVE": 
                db.rollback()
                return jsonify({"detail":"token inactive"}), 400
            if now_ts() > t["expires_at"]: 
                db.rollback()
                return jsonify({"detail":"token expired"}), 400

            existing_claim = db.execute("SELECT claimer FROM claims WHERE token_id=? LIMIT 1", (t["id"],)).fetchone()
            
            if existing_claim:
                db.rollback()
                return jsonify({"detail":f"Token already claimed by {existing_claim['claimer']}"}), 400
            
            db.execute("UPDATE tokens SET status='USED' WHERE id=? AND status='ACTIVE'", (t["id"],))
            if db.execute("SELECT changes()").fetchone()[0] == 0:
                db.rollback()
                return jsonify({"detail":"Token already claimed"}), 400

            # 记录领取
            db.execute("INSERT INTO claims (token_id, claimer, amount, created_at) VALUES (?,?,?,?)",
                       (t["id"], claimer, t["amount"], now_ts()))
            tx_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

            # 更新用户余额
            db.execute("""
                INSERT INTO user_balances (user_id, balance, updated_at) 
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET 
                    balance = balance + ?,
                    updated_at = ?
            """, (int(claimer), t["amount"], now_ts(), t["amount"], now_ts()))

            # 构建区块链数据
            claim_data = {
                "claimer": claimer,
                "amount": t["amount"],
                "token_id": t["id"],
                "description": t["description"] if "description" in t.keys() else ""
            }

            # 写入区块链
            block_hash = add_block(tx_id, claim_data)

            # 提交事务
            db.commit()
            
            return jsonify({
                "ok": True,
                "amount": t["amount"],
                "amount_yuan": t["amount"] / 100,
                "tx_id": tx_id,
                "block_hash": block_hash,
                "description": t["description"] if "description" in t.keys() else ""
            })
            
        except Exception as e:
            db.rollback()
            raise e

    except Exception as e:
        return jsonify({"detail": f"claim failed: {str(e)}"}), 500

@app.route("/api/ledger/verify")
def api_ledger_verify():
    """Verify blockchain integrity"""
    try:
        db = get_db()
        rows = db.execute("SELECT * FROM ledger ORDER BY id ASC").fetchall()
        
        if not rows:
            return jsonify({"ok": True, "length": 0, "message": "Blockchain is empty"})
        
        prev = ""
        for r in rows:
            try:
                # Parse block data
                if r["block_data"]:
                    block_data = json.loads(r["block_data"])
                else:
                    # Compatible with old data
                    block_data = {"tx_id": r["tx_id"]}
                
                payload = json.dumps(block_data, separators=(",", ":"))
                expect = sha256((prev + payload + str(r["created_at"])).encode())
                
                if expect != r["record_hash"]:
                    return jsonify({
                        "ok": False, 
                        "broken_at": r["id"],
                        "expected_hash": expect,
                        "actual_hash": r["record_hash"],
                        "message": "Hash mismatch"
                    })
                prev = r["record_hash"]
                
            except (json.JSONDecodeError, TypeError) as e:
                # If data format has issues, use basic verification
                payload = json.dumps({"tx_id": r["tx_id"]}, separators=(",", ":"))
                expect = sha256((prev + payload + str(r["created_at"])).encode())
                
                if expect != r["record_hash"]:
                    return jsonify({
                        "ok": False,
                        "broken_at": r["id"],
                        "message": "Block data format error, but hash verification failed"
                    })
                prev = r["record_hash"]
        
        return jsonify({
            "ok": True, 
            "length": len(rows),
            "message": "All blocks verified successfully",
            "last_hash": prev
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/ledger/status")
def api_ledger_status():
    """Get blockchain status information"""
    try:
        db = get_db()
        total_blocks = db.execute("SELECT COUNT(*) as count FROM ledger").fetchone()["count"]
        total_transactions = db.execute("SELECT COUNT(*) as count FROM claims").fetchone()["count"]
        total_amount = db.execute("SELECT COALESCE(SUM(amount), 0) as total FROM claims").fetchone()["total"]
        
        # Get the latest few blocks
        recent_blocks = db.execute("""
            SELECT l.*, c.claimer, c.amount 
            FROM ledger l 
            LEFT JOIN claims c ON l.tx_id = c.id 
            ORDER BY l.id DESC 
            LIMIT 5
        """).fetchall()
        
        return jsonify({
            "ok": True,
            "total_blocks": total_blocks,
            "total_transactions": total_transactions,
            "total_amount": total_amount,
            "total_amount_yuan": total_amount / 100,
            "recent_blocks": [
                {
                    "block_id": b["id"],
                    "tx_id": b["tx_id"],
                    "hash": b["record_hash"],
                    "timestamp": b["created_at"],
                    "claimer": b["claimer"],
                    "amount": b["amount"]
                } for b in recent_blocks
            ]
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# 学生端API接口
@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    """Student login"""
    try:
        data = request.get_json(force=True)
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        
        if not username or not password:
            return jsonify({"ok": False, "message": "Username and password are required"}), 400
        
        db = get_db()
        
        # 查询学生账户
        row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        
        if not row:
            return jsonify({"ok": False, "message": "Invalid username or password"}), 401
        
        # 验证密码
        if not bcrypt.check_password_hash(row["password_hash"], password):
            return jsonify({"ok": False, "message": "Invalid username or password"}), 401
        
        if not username.startswith("student"):
            return jsonify({"ok": False, "message": "This is not a student account"}), 403
        
        db.execute("""
            INSERT OR IGNORE INTO user_balances (user_id, balance, updated_at) 
            VALUES (?, 0, ?)
        """, (row["id"], now_ts()))
        db.commit()
        
        return jsonify({
            "ok": True, 
            "user_id": row["id"], 
            "username": row["username"]
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/user/balance", methods=["GET"])
def api_user_balance():
    """获取用户余额接口"""
    try:
        user_id = int(request.args.get("user_id", 1))
        
        db = get_db()
        
        # 获取用户信息
        user_row = db.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()
        if not user_row:
            return jsonify({"ok": False, "error": "User not found"}), 404
        
        # 获取用户余额
        balance_row = db.execute("SELECT balance FROM user_balances WHERE user_id = ?", (user_id,)).fetchone()
        balance = balance_row["balance"] if balance_row else 0
        
        # 获取最近的交易记录
        recent_txs = db.execute("""
            SELECT c.id, c.claimer, c.amount, t.token, c.created_at 
            FROM claims c
            LEFT JOIN tokens t ON c.token_id = t.id
            WHERE c.claimer = ?
            ORDER BY c.created_at DESC 
            LIMIT 10
        """, (str(user_id),)).fetchall()
        
        recent = []
        for tx in recent_txs:
            recent.append({
                "id": tx["id"],
                "user_id": user_id,
                "amount": tx["amount"],
                "type": "earn",
                "token": tx["token"] or f"TX_{tx['id']}",
                "created_at": tx["created_at"]
            })
        
        return jsonify({
            "ok": True,
            "user_id": user_id,
            "username": user_row["username"],
            "balance": balance,
            "recent": recent
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/students", methods=["GET"])
def api_list_students():
    """获取所有学生账户列表"""
    try:
        db = get_db()
        
        students = db.execute("""
            SELECT u.id, u.username, COALESCE(ub.balance, 0) as balance, ub.updated_at
            FROM users u
            LEFT JOIN user_balances ub ON u.id = ub.user_id
            WHERE u.username LIKE 'student%'
            ORDER BY u.id
        """).fetchall()
        
        result = []
        for student in students:
            result.append({
                "id": student["id"],
                "username": student["username"],
                "balance": student["balance"],
                "updated_at": student["updated_at"]
            })
        
        return jsonify({
            "ok": True,
            "students": result
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# 商店管理API
@app.route("/api/shop/items", methods=["GET"])
def api_shop_items():
    """获取商店商品列表"""
    try:
        db = get_db()
        
        items = db.execute("""
            SELECT id, name, description, price, category, image_url, stock, status, created_at
            FROM shop_items 
            WHERE status = 'ACTIVE'
            ORDER BY category, name
        """).fetchall()
        
        result = []
        for item in items:
            result.append({
                "id": item["id"],
                "name": item["name"],
                "description": item["description"],
                "price": item["price"],
                "category": item["category"],
                "image_url": item["image_url"],
                "stock": item["stock"],
                "status": item["status"],
                "created_at": item["created_at"]
            })
        
        return jsonify({
            "ok": True,
            "items": result
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/admin/shop/items", methods=["GET"])
@login_required
def api_admin_shop_items():
    """Get all shop items"""
    try:
        db = get_db()
        
        items = db.execute("""
            SELECT id, name, description, price, category, image_url, stock, status, created_at, updated_at
            FROM shop_items 
            ORDER BY status DESC, category, name
        """).fetchall()
        
        result = []
        for item in items:
            result.append({
                "id": item["id"],
                "name": item["name"],
                "description": item["description"],
                "price": item["price"],
                "category": item["category"],
                "image_url": item["image_url"],
                "stock": item["stock"],
                "status": item["status"],
                "created_at": item["created_at"],
                "updated_at": item["updated_at"]
            })
        
        return jsonify({
            "ok": True,
            "items": result
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/admin/shop/items", methods=["POST"])
@login_required
def api_admin_shop_add_item():
    """Add shop item"""
    try:
        data = request.get_json(force=True)
        name = data.get("name", "").strip()
        description = data.get("description", "").strip()
        price = int(data.get("price", 0))
        category = data.get("category", "general").strip()
        stock = int(data.get("stock", -1))
        
        if not name or price <= 0:
            return jsonify({"ok": False, "message": "Name and price are required"}), 400
        
        db = get_db()
        
        db.execute("""
            INSERT INTO shop_items (name, description, price, category, stock, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
        """, (name, description, price, category, stock, now_ts(), now_ts()))
        db.commit()
        
        return jsonify({
            "ok": True,
            "message": "Item added successfully"
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/admin/shop/items/<int:item_id>", methods=["PUT"])
@login_required
def api_admin_shop_update_item(item_id):
    """Update shop item"""
    try:
        data = request.get_json(force=True)
        name = data.get("name", "").strip()
        description = data.get("description", "").strip()
        price = int(data.get("price", 0))
        category = data.get("category", "general").strip()
        stock = int(data.get("stock", -1))
        status = data.get("status", "ACTIVE").strip()
        
        if not name or price <= 0:
            return jsonify({"ok": False, "message": "Name and price are required"}), 400
        
        db = get_db()
        
        # 检查商品是否存在
        item = db.execute("SELECT id FROM shop_items WHERE id=?", (item_id,)).fetchone()
        if not item:
            return jsonify({"ok": False, "message": "Item not found"}), 404
        
        db.execute("""
            UPDATE shop_items 
            SET name=?, description=?, price=?, category=?, stock=?, status=?, updated_at=?
            WHERE id=?
        """, (name, description, price, category, stock, status, now_ts(), item_id))
        db.commit()
        
        return jsonify({
            "ok": True,
            "message": "Item updated successfully"
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/admin/shop/items/<int:item_id>", methods=["DELETE"])
@login_required
def api_admin_shop_delete_item(item_id):
    """Delete shop item"""
    try:
        db = get_db()
        
        # 检查商品是否存在
        item = db.execute("SELECT id FROM shop_items WHERE id=?", (item_id,)).fetchone()
        if not item:
            return jsonify({"ok": False, "message": "Item not found"}), 404
        
        db.execute("UPDATE shop_items SET status='INACTIVE', updated_at=? WHERE id=?", (now_ts(), item_id))
        db.commit()
        
        return jsonify({
            "ok": True,
            "message": "Item deleted successfully"
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/shop/purchase", methods=["POST"])
def api_shop_purchase():
    """Purchase item"""
    try:
        data = request.get_json(force=True)
        user_id = int(data.get("user_id", 0))
        item_id = int(data.get("item_id", 0))
        quantity = int(data.get("quantity", 1))
        
        if not user_id or not item_id:
            return jsonify({"ok": False, "message": "Missing user_id or item_id"}), 400
        
        db = get_db()
        
        # 获取商品信息
        item = db.execute("SELECT * FROM shop_items WHERE id=? AND status='ACTIVE'", (item_id,)).fetchone()
        if not item:
            return jsonify({"ok": False, "message": "Item not found"}), 404
        
        # 检查库存
        if item["stock"] != -1 and item["stock"] < quantity:
            return jsonify({"ok": False, "message": "Insufficient stock"}), 400
        
        # 计算总价
        total_price = item["price"] * quantity
        
        # 检查用户余额
        balance_row = db.execute("SELECT balance FROM user_balances WHERE user_id=?", (user_id,)).fetchone()
        current_balance = balance_row["balance"] if balance_row else 0
        
        if current_balance < total_price:
            return jsonify({"ok": False, "message": "Insufficient balance"}), 400
        
        try:
            db.execute("BEGIN TRANSACTION")
            db.execute("""
                INSERT INTO purchases (user_id, item_id, quantity, total_price, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, item_id, quantity, total_price, now_ts()))
            purchase_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
            
            # 更新用户余额
            db.execute("""
                UPDATE user_balances 
                SET balance = balance - ?, updated_at = ?
                WHERE user_id = ?
            """, (total_price, now_ts(), user_id))
            
            if item["stock"] != -1:
                db.execute("UPDATE shop_items SET stock = stock - ? WHERE id = ?", (quantity, item_id))
            
            purchase_data = {
                "type": "purchase",
                "user_id": user_id,
                "item_id": item_id,
                "item_name": item["name"],
                "quantity": quantity,
                "total_price": total_price,
                "description": f"Purchased {quantity}x {item['name']}"
            }
            
            # 写入区块链
            block_hash = add_block(purchase_id, purchase_data)
            
            # 提交事务
            db.commit()
            
        except Exception as e:
            db.rollback()
            raise e
        
        # 获取更新后的余额
        new_balance_row = db.execute("SELECT balance FROM user_balances WHERE user_id=?", (user_id,)).fetchone()
        new_balance = new_balance_row["balance"] if new_balance_row else 0
        
        return jsonify({
            "ok": True,
            "message": "Purchase successful",
            "item_name": item["name"],
            "quantity": quantity,
            "total_price": total_price,
            "new_balance": new_balance,
            "purchase_id": purchase_id,
            "block_hash": block_hash
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# 排行榜API
@app.route("/api/leaderboard", methods=["GET"])
def api_leaderboard():
    """Leaderboard"""
    try:
        db = get_db()
        
        # 获取所有学生的余额排行
        students = db.execute("""
            SELECT u.id, u.username, COALESCE(ub.balance, 0) as balance
            FROM users u
            LEFT JOIN user_balances ub ON u.id = ub.user_id
            WHERE u.username LIKE 'student%'
            ORDER BY balance DESC, u.username
        """).fetchall()
        
        result = []
        for i, student in enumerate(students, 1):
            result.append({
                "rank": i,
                "user_id": student["id"],
                "username": student["username"],
                "balance": student["balance"]
            })
        
        return jsonify({
            "ok": True,
            "students": result
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# 教师端购买记录API
@app.route("/api/admin/purchases", methods=["GET"])
@login_required
def api_admin_purchases():
    """Get all purchases"""
    try:
        db = get_db()
        
        # 获取购买记录，包含学生和商品信息
        purchases = db.execute("""
            SELECT 
                p.id,
                p.user_id,
                p.item_id,
                p.quantity,
                p.total_price,
                p.status,
                p.created_at,
                u.username,
                si.name as item_name,
                si.category,
                si.price
            FROM purchases p
            LEFT JOIN users u ON p.user_id = u.id
            LEFT JOIN shop_items si ON p.item_id = si.id
            ORDER BY p.created_at DESC
        """).fetchall()
        
        # 转换为字典列表
        purchase_list = []
        for p in purchases:
            purchase_list.append({
                "id": p["id"],
                "user_id": p["user_id"],
                "item_id": p["item_id"],
                "quantity": p["quantity"],
                "total_price": p["total_price"],
                "status": p["status"],
                "created_at": p["created_at"],
                "username": p["username"],
                "item_name": p["item_name"],
                "category": p["category"],
                "price": p["price"]
            })
        
        return jsonify({
            "ok": True,
            "purchases": purchase_list
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# 学生列表API（用于筛选器）
@app.route("/api/students", methods=["GET"])
@login_required
def api_students():
    """Get students"""
    try:
        db = get_db()
        
        students = db.execute("""
            SELECT id, username
            FROM users
            WHERE username LIKE 'student%'
            ORDER BY username
        """).fetchall()
        
        student_list = []
        for s in students:
            student_list.append({
                "id": s["id"],
                "username": s["username"]
            })
        
        return jsonify({
            "ok": True,
            "students": student_list
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# 验证特定Transaction ID
@app.route("/api/ledger/verify/<int:tx_id>")
def api_ledger_verify_transaction(tx_id):
    """Verify transaction"""
    try:
        db = get_db()
        
        ledger_row = db.execute("SELECT * FROM ledger WHERE tx_id = ?", (tx_id,)).fetchone()
        if not ledger_row:
            return jsonify({"ok": False, "error": f"Transaction ID {tx_id} not found"}), 404
        claim_row = db.execute("SELECT * FROM claims WHERE id = ?", (tx_id,)).fetchone()
        purchase_row = db.execute("SELECT * FROM purchases WHERE id = ?", (tx_id,)).fetchone()
        
        result = {
            "ok": True,
            "transaction_id": tx_id,
            "block_hash": ledger_row["record_hash"],
            "valid": "Yes",
            "created_at": ledger_row["created_at"],
            "transaction_type": "unknown",
            "user_id": None,
            "amount": None,
            "description": ""
        }
        
        if claim_row:
            result.update({
                "transaction_type": "claim",
                "user_id": claim_row["claimer"],
                "amount": claim_row["amount"],
                "description": f"Token claim by user {claim_row['claimer']}"
            })
        elif purchase_row:
            result.update({
                "transaction_type": "purchase",
                "user_id": purchase_row["user_id"],
                "amount": purchase_row["total_price"],
                "description": f"Purchase by user {purchase_row['user_id']}"
            })
        else:
            result["description"] = "Transaction record not found"
            result["valid"] = "No"
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# Startup entry point
if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=5051, debug=True, use_reloader=False)
