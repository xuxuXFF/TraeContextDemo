"""模拟代码库目录树 —— 用嵌套 dict 表示文件路径和内容。

结构示意（简化）：
mock_codebase = {
    "src/": {
        "api/": {
            "routes.py": "...内容...",
            "schemas.py": "...",
        },
        "services/": {
            "auth_service.py": "...",
            "order_service.py": "...",
        },
        "utils/": {
            "db.py": "...",
            "cache.py": "...",
        },
    },
    "tests/": {...},
}
"""


def _build_tree() -> dict:
    """构建一个模拟电商后端的代码库。"""
    return {
        "src/": {
            "api/": {
                "routes.py": (
                    "# API 路由定义\n"
                    "from fastapi import APIRouter\n"
                    "from .schemas import UserCreate, OrderCreate\n"
                    "from ..services.auth_service import AuthService\n"
                    "from ..services.order_service import OrderService\n\n"
                    "router = APIRouter()\n\n"
                    "@router.post('/login')\n"
                    "def login(req: LoginRequest):\n"
                    "    return AuthService.authenticate(req.username, req.password)\n\n"
                    "@router.post('/orders')\n"
                    "def create_order(req: OrderCreate):\n"
                    "    return OrderService.create(req)\n\n"
                    "@router.get('/orders/{order_id}')\n"
                    "def get_order(order_id: str):\n"
                    "    return OrderService.get_by_id(order_id)\n"
                ),
                "schemas.py": (
                    "# Pydantic 数据模型\n"
                    "from pydantic import BaseModel, EmailStr\n\n"
                    "class LoginRequest(BaseModel):\n"
                    "    username: str\n"
                    "    password: str\n\n"
                    "class UserCreate(BaseModel):\n"
                    "    username: str\n"
                    "    email: EmailStr\n"
                    "    password: str\n\n"
                    "class OrderCreate(BaseModel):\n"
                    "    user_id: str\n"
                    "    items: list[Item]\n"
                    "    total_price: float\n"
                    "    address: str\n"
                ),
                "deps.py": (
                    "# FastAPI 依赖注入\n"
                    "from fastapi import Depends, HTTPException\n"
                    "from ..utils.cache import get_current_user\n\n"
                    "def require_auth(user=Depends(get_current_user)):\n"
                    "    if not user:\n"
                    "        raise HTTPException(status_code=401, detail='Unauthorized')\n"
                    "    return user\n"
                ),
            },
            "services/": {
                "auth_service.py": (
                    "# 认证服务\n"
                    "from ..utils.db import get_db\n"
                    "from ..utils.cache import redis\n\n"
                    "class AuthService:\n"
                    "    @staticmethod\n"
                    "    def authenticate(username: str, password: str):\n"
                    "        db = get_db()\n"
                    "        user = db.users.find_one({'username': username})\n"
                    "        if not user or not _verify(password, user['password_hash']):\n"
                    "            raise AuthError('invalid credentials')\n"
                    "        token = _issue_token(user['_id'])\n"
                    "        redis.setex(f'token:{token}', 3600, user['_id'])\n"
                    "        return {'access_token': token}\n\n"
                    "    @staticmethod\n"
                    "    def _verify(pwd: str, pwd_hash: str) -> bool:\n"
                    "        import hashlib\n"
                    "        return hashlib.sha256(pwd.encode()).hexdigest() == pwd_hash\n"
                ),
                "order_service.py": (
                    "# 订单服务\n"
                    "from ..utils.db import get_db\n"
                    "from ..utils.cache import redis\n\n"
                    "class OrderService:\n"
                    "    @staticmethod\n"
                    "    def create(req):\n"
                    "        db = get_db()\n"
                    "        order_id = _gen_id()\n"
                    "        doc = {'_id': order_id, 'user_id': req.user_id,\n"
                    "               'items': req.items, 'status': 'pending'}\n"
                    "        db.orders.insert_one(doc)\n"
                    "        # 发布事件供支付服务监听\n"
                    "        _publish_event('order_created', order_id)\n"
                    "        return {'order_id': order_id, 'status': 'created'}\n\n"
                    "    @staticmethod\n"
                    "    def get_by_id(order_id: str):\n"
                    "        cached = redis.get(f'order:{order_id}')\n"
                    "        if cached:\n"
                    "            return cached\n"
                    "        db = get_db()\n"
                    "        order = db.orders.find_one({'_id': order_id})\n"
                    "        return order\n"
                ),
                "payment_service.py": (
                    "# 支付服务\n"
                    "from ..utils.db import get_db\n\n"
                    "class PaymentService:\n"
                    "    @staticmethod\n"
                    "    def pay(order_id: str, channel: str):\n"
                    "        db = get_db()\n"
                    "        order = db.orders.find_one({'_id': order_id})\n"
                    "        if not order:\n"
                    "            raise OrderNotFoundError\n"
                    "        # 调用第三方支付网关\n"
                    "        result = _call_gateway(channel, order['total_price'])\n"
                    "        if result.ok:\n"
                    "            db.orders.update_one({'_id': order_id},\n"
                    "                                  {'$set': {'status': 'paid'}})\n"
                    "        return result\n"
                ),
            },
            "utils/": {
                "db.py": (
                    "# 数据库连接管理\n"
                    "from pymongo import MongoClient\n\n"
                    "_client = None\n\n"
                    "def get_db():\n"
                    "    global _client\n"
                    "    if _client is None:\n"
                    "        _client = MongoClient('mongodb://localhost:27017')\n"
                    "    return _client['ecommerce']\n\n"
                    "def close_db():\n"
                    "    global _client\n"
                    "    if _client:\n"
                    "        _client.close()\n"
                ),
                "cache.py": (
                    "# Redis 缓存封装\n"
                    "import redis\n\n"
                    "redis = redis.Redis(host='localhost', port=6379, decode_responses=True)\n\n"
                    "def get_current_user(token: str):\n"
                    "    user_id = redis.get(f'token:{token}')\n"
                    "    if user_id:\n"
                    "        return {'user_id': user_id}\n"
                    "    return None\n"
                ),
                "logger.py": (
                    "# 日志配置\n"
                    "import logging\n\n"
                    "def setup_logging(level='INFO'):\n"
                    "    logging.basicConfig(\n"
                    "        level=getattr(logging, level),\n"
                    "        format='%(asctime)s %(levelname)s %(name)s: %(message)s'\n"
                    "    )\n"
                ),
            },
        },
        "tests/": {
            "test_auth.py": (
                "# 认证测试\n"
                "import pytest\n"
                "from src.services.auth_service import AuthService\n\n"
                "def test_auth_success():\n"
                "    result = AuthService.authenticate('test_user', 'correct_pwd')\n"
                "    assert 'access_token' in result\n\n"
                "def test_auth_fail():\n"
                "    with pytest.raises(Exception):\n"
                "        AuthService.authenticate('test_user', 'wrong_pwd')\n"
            ),
            "test_order.py": (
                "# 订单测试\n"
                "import pytest\n"
                "from src.services.order_service import OrderService\n\n"
                "def test_create_order():\n"
                "    result = OrderService.create(fake_req)\n"
                "    assert result['status'] == 'created'\n"
            ),
        },
        "config.py": (
            "# 全局配置\n"
            "import os\n\n"
            "DATABASE_URL = os.environ.get('DATABASE_URL', 'mongodb://localhost:27017')\n"
            "REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')\n"
            "# NOTE: 生产环境必须从安全密钥管理服务读取，禁止硬编码\n"
            "SECRET_KEY = os.environ.get('SECRET_KEY', '')\n"
        ),
        "README.md": (
            "# 电商后端服务\n\n"
            "FastAPI + MongoDB + Redis 技术栈的电商后端示例。\n"
            "运行方式：uvicorn src.api.routes:router --reload\n"
        ),
    }


CODEBASE_TREE = _build_tree()


def flatten_tree(tree: dict, prefix: str = "") -> dict[str, str]:
    """将嵌套 dict 扁平化为 {文件路径: 文件内容}。"""
    flat: dict[str, str] = {}
    for name, value in tree.items():
        full = prefix + name
        if isinstance(value, dict):
            flat.update(flatten_tree(value, full))
        else:
            flat[full] = value
    return flat


def list_all_files(tree: dict) -> list[str]:
    return list(flatten_tree(tree).keys())
