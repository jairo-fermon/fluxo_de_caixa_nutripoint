import re
import unicodedata
from decimal import Decimal, InvalidOperation


TOTAL_KEYWORDS = (
    "valor total",
    "total",
    "total r$",
    "total a pagar",
    "vl total",
    "valor pago",
)


CATEGORY_KEYWORDS = {
    "Agua mineral": ("agua", "mineral"),
    "Carne Bovina": ("carne bovina", "acém", "alcatra", "contra file", "contrafile", "picanha"),
    "Embalagem/Etiqueta": ("embalagem", "etiqueta", "marmita", "pote", "sacola"),
    "Filé Mignon": ("file mignon", "filé mignon"),
    "Frango": ("frango", "peito de frango", "coxa", "sobrecoxa"),
    "Matéria prima": ("hortifruti", "fornecedor", "atacadao", "assai", "mercado", "supermercado"),
    "Peixe": ("tilapia", "peixe"),
    "Salmão": ("salmao", "salmão"),
    "Frete": ("frete", "entrega", "transportadora"),
    "Imposto": ("imposto", "das", "simples nacional", "tributo"),
    "Taxa Cartão": ("taxa cartao", "taxa cartão", "adquirente", "stone", "cielo"),
    "Taxa Ifood": ("ifood",),
    "Aluguel": ("aluguel", "locacao", "locação"),
    "Cagece": ("cagece", "agua e esgoto", "água e esgoto"),
    "Contador": ("contador", "contabilidade", "escritorio contabil", "escritório contábil"),
    "Energia": ("enel", "energia", "conta de luz"),
    "Gás": ("gas", "gás", "ultragaz", "nacional gas"),
    "Internet": ("internet", "fibra", "provedor", "brisanet", "claro", "vivo", "oi"),
    "Marketing": ("trafego", "tráfego", "facebook ads", "google ads", "marketing"),
    "Plano de Saúde": ("hapvida", "unimed", "plano de saude", "plano de saúde"),
    "Salários": ("salario", "salário", "folha", "pagamento funcionario", "pagamento funcionário"),
    "Sistema ERP": ("erp", "sistema", "software"),
    "Tarifas bancárias": ("tarifa bancaria", "tarifa bancária", "pacote de servicos", "pacote de serviços"),
    "Despesa Diversa": ("diversos", "diversa"),
}


PAYMENT_METHOD_HINTS = (
    ("pix", "PIX"),
    ("boleto", "Boleto"),
    ("debito", "Empresarial Débito"),
    ("débito", "Empresarial Débito"),
    ("credito", "Empresarial Crédito"),
    ("crédito", "Empresarial Crédito"),
)


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return normalized.lower()


def parse_brazilian_amount(raw: str) -> float | None:
    cleaned = re.sub(r"[^0-9,.\-]", "", raw or "")
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    return float(value)


def find_receipt_total(text: str) -> float | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    candidates: list[float] = []
    for line in lines:
        normalized = normalize_text(line)
        if any(keyword in normalized for keyword in TOTAL_KEYWORDS):
            matches = re.findall(r"(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2}|\d+\.\d{2}|\d+,\d{2})", line)
            for match in matches:
                amount = parse_brazilian_amount(match)
                if amount is not None:
                    candidates.append(amount)
    if candidates:
        return max(candidates)
    all_amounts = []
    for match in re.findall(r"(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2}|\d+\.\d{2}|\d+,\d{2})", text):
        amount = parse_brazilian_amount(match)
        if amount is not None:
            all_amounts.append(amount)
    return max(all_amounts) if all_amounts else None


def find_receipt_date(text: str) -> str:
    match = re.search(r"\b(\d{2})[\/\-](\d{2})[\/\-](\d{4})\b", text)
    if not match:
        return ""
    day, month, year = match.groups()
    return f"{year}-{month}-{day}"


def infer_payment_method(text: str, payment_methods: list[dict]) -> str:
    normalized = normalize_text(text)
    available = {normalize_text(item["name"]): item["name"] for item in payment_methods}
    for hint, target in PAYMENT_METHOD_HINTS:
        if hint in normalized:
            target_key = normalize_text(target)
            if target_key in available:
                return available[target_key]
    for key, original in available.items():
        if key and key in normalized:
            return original
    return ""


def infer_category(text: str, categories: list[dict]) -> tuple[str, str]:
    normalized = normalize_text(text)
    by_name = {item["name"]: item["dre_group"] for item in categories if item["entry_type"] == "DESPESA"}
    for category_name, keywords in CATEGORY_KEYWORDS.items():
        if category_name not in by_name:
            continue
        if any(keyword in normalized for keyword in keywords):
            return category_name, by_name[category_name]
    for item in categories:
        if item["entry_type"] != "DESPESA":
            continue
        category_key = normalize_text(item["name"])
        if category_key and category_key in normalized:
            return item["name"], item["dre_group"]
    return "", ""


def build_notes(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    merchant = lines[0]
    excerpt = " | ".join(lines[:5])
    return f"Cupom lido automaticamente. Estabelecimento: {merchant}. Texto: {excerpt[:400]}"


def analyze_receipt_text(text: str, categories: list[dict], payment_methods: list[dict]) -> dict:
    parsed_date = find_receipt_date(text)
    category_name, dre_group = infer_category(text, categories)
    payment_method = infer_payment_method(text, payment_methods)
    total = find_receipt_total(text)
    notes = build_notes(text)
    return {
        "fact_date": parsed_date,
        "entry_type": "DESPESA",
        "dre_group": dre_group,
        "category_name": category_name,
        "payment_method": payment_method,
        "gross_amount": f"{total:.2f}" if total is not None else "",
        "payment_date": parsed_date,
        "competence_month": parsed_date,
        "notes": notes,
        "status": "planejado",
        "ocr_text": text.strip(),
    }
