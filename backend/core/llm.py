"""
GenData — LLM 集成层
"""
import json, re, httpx
from config import LLM_API_KEY, LLM_API_URL, LLM_MODEL

SYSTEM_PROMPT = """你是一个专业的数据库仿真数据生成专家。你的工作是根据用户提供的 SQL CREATE TABLE 语句，分析表结构和字段含义，输出每个字段的填充规则。

注意：
1. 字段名 hint：user_name → 用户名, mobile → 手机号, id_card → 身份证, email → 邮箱, address → 地址
2. 外键关系需要生成关联数据：例如 order.user_id 需要引用 user.id
3. 日期/时间字段要生成合理范围
4. 枚举字段要合理分布
5. 数值字段要有合理范围
6. 文本字段不要重复，要多样化

输出 JSON 格式，每个表的每个字段给出：
- field: 字段名
- type: 数据类型
- gen_type: 生成类型 (name/phone/email/address/id_card/date/enum/text/int/float/fk_ref/ip/url/uuid/fixed)
- rules: 生成规则描述
- enum_values: 如果是枚举，列出可能值
- fk_table: 如果是外键，关联的表名
- fk_field: 如果是外键，关联的字段名
- min/max: 数值范围
"""

def clean_json(text: str) -> str:
    """从 LLM 回复中提取 JSON"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()

async def analyze_schema(schema_sql: str) -> dict:
    """分析 SQL Schema，返回每个表的字段生成规则"""
    if not LLM_API_KEY:
        return _fallback_parse(schema_sql)

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                LLM_API_URL,
                headers={
                    "Authorization": f"Bearer {LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"请分析以下 SQL 表结构，输出每个字段的生成规则（JSON 格式）：\n\n{schema_sql}"},
                    ],
                    "temperature": 0.1,
                },
            )
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            content = clean_json(content)
            result = json.loads(content)

            # 确保格式统一
            if isinstance(result, dict) and "tables" in result:
                return result
            if isinstance(result, list):
                return {"tables": result}
            return result

    except Exception as e:
        return _fallback_parse(schema_sql)

def _fallback_parse(schema_sql: str) -> dict:
    """无LLM时的兜底解析——基于字段名匹配"""
    tables = {}
    current_table = None

    for line in schema_sql.split("\n"):
        line = line.strip()

        # 匹配 CREATE TABLE
        m = re.match(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:`?\w+`?\.)?`?(\w+)`?\s*\(", line, re.I)
        if m:
            current_table = m.group(1)
            tables[current_table] = {"fields": []}
            continue

        if not current_table:
            continue

        # 匹配字段行
        m = re.match(r"`?(\w+)`?\s+(\w+(?:\([^)]*\))?)\s*,?\s*$", line, re.I)
        if m:
            field_name = m.group(1)
            field_type = m.group(2).upper()
            rule = _infer_rule(field_name, field_type)
            tables[current_table]["fields"].append(rule)

        # 匹配外键
        m = re.search(r"FOREIGN\s+KEY\s*\(`?(\w+)`?\)\s*REFERENCES\s+`?(\w+)`?\s*\(`?(\w+)`?\)", line, re.I)
        if m:
            fk_field = m.group(1)
            fk_table = m.group(2)
            fk_ref = m.group(3)
            for f in tables[current_table]["fields"]:
                if f["field"] == fk_field:
                    f["gen_type"] = "fk_ref"
                    f["fk_table"] = fk_table
                    f["fk_field"] = fk_ref

    return {"tables": list(tables.values())}

def _infer_rule(field_name: str, field_type: str) -> dict:
    """基于字段名推断生成规则"""
    name = field_name.lower()
    rule = {"field": field_name, "type": field_type, "gen_type": "text"}

    # 名称推断
    if any(k in name for k in ["name", "username", "nickname", "nick", "fullname"]):
        rule["gen_type"] = "name"
    elif any(k in name for k in ["phone", "mobile", "tel", "cellphone"]):
        rule["gen_type"] = "phone"
    elif any(k in name for k in ["email", "mail"]):
        rule["gen_type"] = "email"
    elif any(k in name for k in ["address", "addr", "location", "street", "city"]):
        rule["gen_type"] = "address"
    elif any(k in name for k in ["id_card", "idcard", "identity", "sfz"]):
        rule["gen_type"] = "id_card"
    elif any(k in name for k in ["date", "time", "created_at", "updated_at", "timestamp"]):
        rule["gen_type"] = "date"
    elif any(k in name for k in ["ip", "ip_address"]):
        rule["gen_type"] = "ip"
    elif any(k in name for k in ["url", "link", "website"]):
        rule["gen_type"] = "url"
    elif any(k in name for k in ["uuid", "guid"]):
        rule["gen_type"] = "uuid"
    elif any(k in name for k in ["status", "state", "type", "category", "level"]):
        rule["gen_type"] = "enum"
        rule["enum_values"] = ["active", "inactive", "pending", "closed"]
    elif any(k in name for k in ["price", "amount", "cost", "fee", "money"]):
        rule["gen_type"] = "float"
        rule["min"] = 0
        rule["max"] = 10000
    elif any(k in name for k in ["age", "count", "num", "quantity", "qty"]):
        rule["gen_type"] = "int"
        rule["min"] = 0
        rule["max"] = 1000
    elif "id" == name or name.endswith("_id") and name != "id":
        rule["gen_type"] = "int"
        rule["min"] = 1
        rule["max"] = 100000
    elif name == "id":
        rule["gen_type"] = "int"
        rule["min"] = 1
        rule["max"] = 1000000
    elif "description" in name or "desc" in name or "comment" in name or "note" in name:
        rule["gen_type"] = "text"
    elif "int" in field_type.lower() or "integer" in field_type.lower():
        rule["gen_type"] = "int"
        rule["min"] = 0
        rule["max"] = 1000
    elif "float" in field_type.lower() or "double" in field_type.lower() or "decimal" in field_type.lower():
        rule["gen_type"] = "float"
        rule["min"] = 0
        rule["max"] = 10000
    elif "date" in field_type.lower() or "time" in field_type.lower():
        rule["gen_type"] = "date"
    else:
        rule["gen_type"] = "text"

    return rule
