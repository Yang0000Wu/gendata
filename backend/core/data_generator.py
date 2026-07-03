"""
GenData — 数据生成引擎
"""
import random, csv, json, io, os, uuid
from datetime import datetime, timedelta

CHINESE_SURNAMES = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳丰鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄"
CHINESE_GIVEN = "伟芳娜秀英敏静丽强磊洋勇艳杰娟军秀兰霞平刚桂英文华建华飞玉兰斌梅鑫"

CITIES = ["北京","上海","深圳","广州","杭州","成都","武汉","南京","西安","重庆","苏州","长沙","厦门","青岛","大连","天津","郑州","合肥","福州","昆明"]

def gen_name():
    surname = random.choice(CHINESE_SURNAMES)
    given = "".join(random.choices(CHINESE_GIVEN, k=random.randint(1, 2)))
    return surname + given

def gen_phone():
    prefixes = ["13","15","17","18","19"]
    return random.choice(prefixes) + "".join([str(random.randint(0,9)) for _ in range(9)])

def gen_email():
    domains = ["qq.com","163.com","gmail.com","outlook.com","aliyun.com","company.cn"]
    return "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=random.randint(4,12))) + "@" + random.choice(domains)

def gen_address():
    city = random.choice(CITIES)
    district = "".join(random.choices(CHINESE_SURNAMES + CHINESE_GIVEN, k=2)) + "区"
    road = "".join(random.choices(CHINESE_SURNAMES + CHINESE_GIVEN, k=2)) + "路"
    num = str(random.randint(1, 999))
    return f"{city}{district}{road}{num}号"

def gen_id_card():
    area = str(random.randint(110000, 659000))
    birth = datetime(1970,1,1) + timedelta(days=random.randint(0, 365*50))
    birth_str = birth.strftime("%Y%m%d")
    seq = str(random.randint(100, 999))
    code = area + birth_str + seq
    # 简单校验码
    weights = [7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2]
    total = sum(int(code[i]) * weights[i] for i in range(17))
    check = "10X98765432"[total % 11]
    return code + check

def gen_date(start_year=1990, end_year=2026):
    start = datetime(start_year,1,1)
    end = datetime(end_year,12,31)
    delta = end - start
    return (start + timedelta(days=random.randint(0, delta.days))).strftime("%Y-%m-%d")

def gen_datetime(start_year=2020, end_year=2026):
    start = datetime(start_year,1,1)
    end = datetime(end_year,12,31)
    delta = end - start
    d = start + timedelta(days=random.randint(0, delta.days))
    h = random.randint(0,23)
    m = random.randint(0,59)
    s = random.randint(0,59)
    return d.replace(hour=h, minute=m, second=s).strftime("%Y-%m-%d %H:%M:%S")

def gen_ip():
    return f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"

def gen_uuid():
    return str(uuid.uuid4())

def gen_url():
    domains = ["example.com","test.com","demo.cn","sample.org","myapp.io","api.service.com"]
    paths = ["/api/v1","/users","/data","/files","/callback","/webhook"]
    return f"https://{random.choice(domains)}{random.choice(paths)}/{random.randint(100,999)}"

GENERATORS = {
    "name": lambda r: gen_name(),
    "phone": lambda r: gen_phone(),
    "email": lambda r: gen_email(),
    "address": lambda r: gen_address(),
    "id_card": lambda r: gen_id_card(),
    "date": lambda r: gen_date(),
    "datetime": lambda r: gen_datetime(),
    "int": lambda r, f: random.randint(int(f.get("min", 0)), int(f.get("max", 1000))),
    "float": lambda r, f: round(random.uniform(float(f.get("min", 0)), float(f.get("max", 10000))), 2),
    "text": lambda r: "".join(random.choices("这是一段模拟文本数据用于测试ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", k=random.randint(10, 50))),
    "enum": lambda r, f: random.choice(f.get("enum_values", ["value_a","value_b","value_c"])),
    "ip": lambda r: gen_ip(),
    "uuid": lambda r: gen_uuid(),
    "url": lambda r: gen_url(),
    "fixed": lambda r, f: f.get("value", ""),
}

def _gen_value(field: dict, fk_cache: dict):
    """生成单个字段的值"""
    gt = field.get("gen_type", "text")

    if gt == "fk_ref":
        fk_table = field.get("fk_table")
        fk_field = field.get("fk_field", "id")
        if fk_table and fk_table in fk_cache:
            return random.choice(fk_cache[fk_table])
        return random.randint(1, 10000)

    if gt in ("int", "float", "enum", "fixed"):
        return GENERATORS[gt](None, field)

    return GENERATORS.get(gt, GENERATORS["text"])(None)

def _gen_value_str(field: dict, fk_cache: dict) -> str:
    v = _gen_value(field, fk_cache)
    return str(v)

def generate_data(schema: dict, row_count: int) -> dict:
    """
    根据 schema 生成数据
    schema 格式：{"tables": [{"name": "users", "fields": [...]}, ...]}
    返回每个表的数据列表
    """
    tables = schema.get("tables", [])
    result = {}
    table_order = {}  # 父表先生成

    # 第一遍：找到没有外键的表先生成
    for t in tables:
        tname = t.get("name", "table")
        has_fk = any(f.get("gen_type") == "fk_ref" for f in t.get("fields", []))
        table_order[tname] = has_fk

    fk_cache = {}  # {table_name: [id_value, ...]}

    # 先生成父表（无外键依赖）
    for t in tables:
        tname = t.get("name", "table")
        if table_order.get(tname, False):
            continue
        rows = []
        for i in range(row_count):
            row = {}
            for f in t.get("fields", []):
                val = _gen_value_str(f, fk_cache)
                # 如果是 ID 字段，记录到 fk_cache
                if f.get("field", "").lower() in ("id", f"{tname.lower()}_id"):
                    fk_cache.setdefault(tname, []).append(val)
                row[f.get("field", "col")] = val
            rows.append(row)
        result[tname] = rows

    # 再生成子表（有外键依赖的）
    for t in tables:
        tname = t.get("name", "table")
        if not table_order.get(tname, False):
            continue
        rows = []
        for i in range(row_count):
            row = {}
            for f in t.get("fields", []):
                val = _gen_value_str(f, fk_cache)
                row[f.get("field", "col")] = val
            rows.append(row)
        result[tname] = rows

    return result

def export_csv(data: dict) -> dict:
    """导出为 CSV，返回 {table_name: csv_string}"""
    result = {}
    for tname, rows in data.items():
        if not rows:
            result[tname] = ""
            continue
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        result[tname] = output.getvalue()
    return result

def export_json(data: dict) -> dict:
    """导出为 JSON"""
    result = {}
    for tname, rows in data.items():
        result[tname] = json.dumps(rows, ensure_ascii=False, indent=2)
    return result

def export_sql(data: dict, schema: dict) -> dict:
    """导出为 INSERT SQL"""
    result = {}
    for t in schema.get("tables", []):
        tname = t.get("name", "table")
        rows = data.get(tname, [])
        if not rows:
            result[tname] = ""
            continue
        fields = ", ".join(f"`{f.get('field', 'col')}`" for f in t.get("fields", []))
        placeholders = ", ".join(["?" for _ in t.get("fields", [])])
        lines = [f"INSERT INTO `{tname}` ({fields}) VALUES"]
        values = []
        for row in rows:
            vals = ", ".join(f"'{str(v).replace(chr(39), chr(39)*2)}'" for v in row.values())
            values.append(f"({vals})")
        lines.append(",\n".join(values) + ";")
        result[tname] = "\n".join(lines)
    return result
