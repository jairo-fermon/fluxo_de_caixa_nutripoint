from datetime import datetime
from html import escape


APP_TITLE = "Nutripoint Finance"


def format_currency(value: float) -> str:
    amount = f"{float(value):,.2f}"
    amount = amount.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {amount}"


def format_percent(value: float) -> str:
    return f"{float(value) * 100:.2f}%".replace(".", ",")


def format_date(value: str | None) -> str:
    if not value:
        return "-"
    try:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y")
    except ValueError:
        return value


def format_datetime(value: str | None) -> str:
    if not value:
        return "-"
    try:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return value


def format_competence(value: str | None) -> str:
    if not value:
        return ""
    months = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    try:
        parsed = datetime.fromisoformat(value)
        return f"{months[parsed.month - 1]}/{str(parsed.year)[-2:]}"
    except ValueError:
        return value


def build_line_chart_svg(points: list[dict]) -> str:
    width = 720
    height = 260
    padding = 28
    if not points:
        return '<div class="empty-chart">Sem dados no período.</div>'
    max_value = max(max(item["entradas"], item["saidas"]) for item in points) or 1
    inner_w = width - padding * 2
    inner_h = height - padding * 2

    def point_path(field: str) -> str:
        coords = []
        total = max(len(points) - 1, 1)
        for index, item in enumerate(points):
            x = padding + (inner_w * index / total)
            y = padding + inner_h - ((item[field] / max_value) * inner_h)
            coords.append(f"{x:.1f},{y:.1f}")
        return " ".join(coords)

    labels = "".join(
        f'<text x="{padding + (inner_w * i / max(len(points)-1,1)):.1f}" y="{height - 6}" text-anchor="middle" class="chart-label">{escape(format_date(item["date"]))}</text>'
        for i, item in enumerate(points)
    )
    return f"""
    <svg viewBox="0 0 {width} {height}" class="chart-svg" role="img" aria-label="Entradas e saídas por dia">
        <line x1="{padding}" y1="{height-padding}" x2="{width-padding}" y2="{height-padding}" class="chart-axis"></line>
        <line x1="{padding}" y1="{padding}" x2="{padding}" y2="{height-padding}" class="chart-axis"></line>
        <polyline fill="none" stroke="#7fd35d" stroke-width="4" points="{point_path('entradas')}"></polyline>
        <polyline fill="none" stroke="#c12771" stroke-width="4" points="{point_path('saidas')}"></polyline>
        {labels}
    </svg>
    """


def build_bar_chart_svg(revenue: float, expenses: float) -> str:
    width = 420
    height = 240
    max_value = max(revenue, expenses, 1)
    rev_h = 160 * (revenue / max_value)
    exp_h = 160 * (expenses / max_value)
    return f"""
    <svg viewBox="0 0 {width} {height}" class="chart-svg" role="img" aria-label="Comparativo de entradas e saídas">
        <line x1="50" y1="190" x2="370" y2="190" class="chart-axis"></line>
        <rect x="95" y="{190-rev_h:.1f}" width="80" height="{rev_h:.1f}" fill="#7fd35d" rx="12"></rect>
        <rect x="245" y="{190-exp_h:.1f}" width="80" height="{exp_h:.1f}" fill="#c12771" rx="12"></rect>
        <text x="135" y="212" text-anchor="middle" class="chart-label">Entradas</text>
        <text x="285" y="212" text-anchor="middle" class="chart-label">Saídas</text>
        <text x="135" y="{180-rev_h:.1f}" text-anchor="middle" class="chart-value">{escape(format_currency(revenue))}</text>
        <text x="285" y="{180-exp_h:.1f}" text-anchor="middle" class="chart-value">{escape(format_currency(expenses))}</text>
    </svg>
    """


def selected(current: str, value: str) -> str:
    return " selected" if current == value else ""


def nav_items(user):
    items = [
        ("/dashboard", "Painel"),
        ("/lancamentos", "Lançamentos"),
        ("/fluxo-caixa", "Fluxo de Caixa"),
        ("/dre", "DRE"),
        ("/conciliacao", "Conciliação"),
    ]
    if user["role"] == "admin":
        items.extend([("/admin/referencias", "Referências"), ("/admin/auditoria", "Auditoria")])
    return items


def render_layout(title: str, content: str, user=None, flash: str = "", flash_kind: str = "success") -> bytes:
    body_class = "auth-shell" if user is None else "app-shell"
    navigation = ""
    user_box = ""
    theme_toggle = """
    <button type="button" class="theme-toggle" id="theme-toggle" aria-label="Alternar tema" title="Alternar tema">
        <span class="theme-toggle-icon" id="theme-toggle-icon">◐</span>
    </button>
    """

    if user:
        link_parts = []
        pending_count = int(user.get("pending_users", 0) or 0)
        for href, label in nav_items(user):
            badge = ""
            if href == "/admin/usuarios" and pending_count:
                badge = f'<span class="nav-badge">{pending_count}</span>'
            link_parts.append(f'<a href="{href}" class="nav-link"><span>{label}</span>{badge}</a>')
        links = "".join(link_parts)
        quick_links = ['<a href="/minha-conta" class="brand-quick-link">Minha conta</a>']
        if user["role"] == "admin":
            badge = f'<span class="nav-badge">{pending_count}</span>' if pending_count else ""
            quick_links.append(f'<a href="/admin/usuarios" class="brand-quick-link">Usuários{badge}</a>')
        quick_links_html = "".join(quick_links)
        navigation = f"""
        <aside class="sidebar">
            <div class="brand">
                <img src="/static/nutripoint.jpg" alt="Nutripoint" class="brand-logo">
                <div>
                    <strong>{APP_TITLE}</strong>
                    <p>Gestão financeira inteligente</p>
                    <div class="brand-quick-links">{quick_links_html}</div>
                </div>
            </div>
            <nav class="nav">{links}</nav>
        </aside>
        """
        role_label = "Administrador" if user["role"] == "admin" else "Usuário"
        user_box = f"""
        <div class="topbar">
            <div>
                <h1>{escape(title)}</h1>
            </div>
            <div class="topbar-actions">
                {theme_toggle}
                <div class="user-chip">
                    <div>
                        <strong>{escape(user["name"])}</strong>
                        <p>{role_label}</p>
                    </div>
                    <a href="/logout" class="button button-secondary">Sair</a>
                </div>
            </div>
        </div>
        """
    else:
        user_box = f'<div class="topbar topbar-auth"><div></div>{theme_toggle}</div>'

    flash_class = "flash flash-error" if flash_kind == "error" else "flash"
    flash_html = f'<div class="{flash_class}">{escape(flash)}</div>' if flash else ""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)} | {APP_TITLE}</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body class="{body_class}">
    {navigation}
    <main class="main">
        {user_box}
        {flash_html}
        {content}
    </main>
    <script>
    (function() {{
      const storageKey = 'nutripoint-theme';
      const root = document.body;
      const button = document.getElementById('theme-toggle');
      const icon = document.getElementById('theme-toggle-icon');
      function applyTheme(theme) {{
        root.setAttribute('data-theme', theme);
        if (icon) {{
          icon.textContent = theme === 'light' ? '☀' : '☾';
        }}
      }}
      const saved = localStorage.getItem(storageKey) || 'light';
      applyTheme(saved);
      if (button) {{
        button.addEventListener('click', function() {{
          const current = root.getAttribute('data-theme') || 'light';
          const next = current === 'dark' ? 'light' : 'dark';
          localStorage.setItem(storageKey, next);
          applyTheme(next);
        }});
      }}
    }})();
    </script>
</body>
</html>
"""
    return html.encode("utf-8")


def login_page(error: str = "") -> bytes:
    content = f"""
    <section class="auth-stage">
        <section class="auth-card auth-card-centered">
            <img src="/static/nutripoint.jpg" alt="Nutripoint" class="auth-logo">
            <h1>Nutripoint Finance</h1>
            <p>Faça login para acessar lançamentos, fluxo de caixa, DRE e administração do sistema.</p>
            {'<div class="flash flash-error">' + escape(error) + '</div>' if error else ''}
            <form method="post" action="/login" class="form-grid">
                <label>
                    E-mail
                    <input type="email" name="email" placeholder="voce@empresa.com" required>
                </label>
                <label>
                    Senha
                    <input type="password" name="password" placeholder="Digite sua senha" required>
                </label>
                <button type="submit" class="button">Entrar</button>
            </form>
            <div class="auth-links">
                <a href="/criar-conta" class="button button-secondary">Criar conta</a>
            </div>
        </section>
    </section>
    """
    return render_layout("Login", content)


def register_page(error: str = "", flash_kind: str = "success") -> bytes:
    flash_class = "flash flash-error" if flash_kind == "error" else "flash"
    flash_html = f'<div class="{flash_class}">{escape(error)}</div>' if error else ""
    content = f"""
    <section class="auth-stage">
        <section class="auth-card auth-card-centered">
            <img src="/static/nutripoint.jpg" alt="Nutripoint" class="auth-logo">
            <div class="hero-badge">Solicitação de acesso</div>
            <h1>Criar conta</h1>
            <p>Preencha seus dados. O acesso será liberado após aprovação do administrador.</p>
            {flash_html}
            <form method="post" action="/register" class="form-grid">
                <label>Nome<input type="text" name="name" required></label>
                <label>E-mail<input type="email" name="email" placeholder="voce@empresa.com" required></label>
                <label>Senha<input type="password" name="password" placeholder="Crie uma senha" required></label>
                <button type="submit" class="button">Solicitar acesso</button>
            </form>
            <div class="auth-links">
                <a href="/" class="button button-secondary">Voltar ao login</a>
            </div>
        </section>
    </section>
    """
    return render_layout("Criar conta", content)


def dashboard_page(user, metrics) -> bytes:
    cards = [
        ("Saldo inicial", format_currency(metrics["opening_balance"])),
        ("Entradas líquidas", format_currency(metrics["revenue"])),
        ("Saídas", format_currency(metrics["expenses"])),
        ("Saldo projetado", format_currency(metrics["balance"])),
        ("Lançamentos", str(metrics["total_entries"])),
        ("Pendências de conciliação", str(metrics["pending_conciliation"])),
    ]
    cards_html = "".join(
        f'<article class="stat-card"><p>{label}</p><strong>{value}</strong></article>'
        for label, value in cards
    )

    filters = metrics.get("filters", {"date_from": "", "date_to": ""})
    line_chart = build_line_chart_svg(metrics.get("timeline", []))
    bar_chart = build_bar_chart_svg(metrics["revenue"], metrics["expenses"])
    content = f"""
    <section class="panel">
        <h2>Filtro de período</h2>
        <form method="get" action="/dashboard" class="form-grid two-columns">
            <label>Data inicial<input type="date" name="date_from" value="{escape(filters['date_from'])}"></label>
            <label>Data final<input type="date" name="date_to" value="{escape(filters['date_to'])}"></label>
            <div class="actions-row">
                <button type="submit" class="button">Aplicar</button>
                <a href="/dashboard" class="button button-secondary">Resetar</a>
            </div>
        </form>
    </section>
    <section class="stats-grid">{cards_html}</section>
    <section class="panel-grid">
        <article class="panel">
            <h2>Evolução diária</h2>
            <p>Entradas e saídas do período selecionado.</p>
            {line_chart}
            <div class="legend-row">
                <span><i class="legend-dot legend-green"></i> Entradas</span>
                <span><i class="legend-dot legend-orange"></i> Saídas</span>
            </div>
        </article>
        <article class="panel">
            <h2>Comparativo</h2>
            <p>Visão rápida do peso de entradas e saídas no período.</p>
            {bar_chart}
        </article>
    </section>
    """
    return render_layout("Painel", content, user=user)


def cash_entries_page(user, context: dict) -> bytes:
    filters = context["filters"]
    form = context["form"]
    categories = context["categories"]
    payment_methods = context["payment_methods"]
    receive_methods = context["receive_methods"]
    entry = context.get("editing_entry")
    revenue_categories = [item for item in categories if item["entry_type"] == "RECEITA"]
    expense_groups = sorted({item["dre_group"] for item in categories if item["entry_type"] == "DESPESA"})
    expense_categories = sorted(
        [item for item in categories if item["entry_type"] == "DESPESA"],
        key=lambda item: item["name"].casefold(),
    )
    rows = []
    for item in context["entries"]:
        rows.append(
            f"""
            <tr>
                <td>{format_date(item['fact_date'])}</td>
                <td>{escape(item['entry_type'])}</td>
                <td>{escape(item['category_name'])}</td>
                <td>{escape(item['dre_group'])}</td>
                <td>{escape(item['payment_method'])}</td>
                <td>{format_currency(item['gross_amount'])}</td>
                <td>{format_percent(item['fee_percent'])}</td>
                <td>{format_currency(item['fee_amount'])}</td>
                <td>{format_currency(item['net_amount'])}</td>
                <td>
                    <div class="table-actions">
                        <a href="/lancamentos?edit={item['id']}" class="link-button">Editar</a>
                        <form method="post" action="/lancamentos/excluir" onsubmit="return confirm('Excluir lançamento?');">
                            <input type="hidden" name="id" value="{item['id']}">
                            <button type="submit" class="link-button danger-link">Excluir</button>
                        </form>
                    </div>
                </td>
            </tr>
            """
        )
    table_html = "".join(rows) if rows else '<tr><td colspan="10" class="empty-state">Nenhum lançamento encontrado.</td></tr>'

    revenue_options = "".join(
        f'<option value="{escape(item["name"])}"{selected(form["category_name"], item["name"])}>{escape(item["name"])}</option>'
        for item in revenue_categories
    )
    expense_category_options = "".join(
        f'<option value="{escape(item["name"])}" data-group="{escape(item["dre_group"])}"{selected(form["category_name"], item["name"])}>{escape(item["name"])}</option>'
        for item in expense_categories
    )
    payment_options = "".join(
        f'<option value="{escape(item["name"])}"{selected(form["payment_method"], item["name"])}>{escape(item["name"])} ({format_percent(item["fee_percent"])})</option>'
        for item in payment_methods
    )
    receive_options = "".join(
        f'<option value="{escape(item["name"])}"{selected(form["payment_method"], item["name"])}>{escape(item["name"])} ({format_percent(item["fee_percent"])})</option>'
        for item in receive_methods
    )
    category_filter_options = "".join(
        f'<option value="{escape(item["name"])}"{selected(filters["category_name"], item["name"])}>{escape(item["name"])}</option>'
        for item in categories
    )

    submit_label = "Atualizar lançamento" if entry else "Salvar lançamento"
    edit_notice = '<div class="subtle-note">Você está editando um lançamento existente.</div>' if entry else ""

    content = f"""
    <section class="panel">
        <article>
            <h2>Lançamento financeiro</h2>
            <p>Estrutura inspirada nas abas <code>INSERIR</code> e <code>Movimentacoes (2)</code>.</p>
            {edit_notice}
            <form method="post" action="/lancamentos/salvar" class="form-grid two-columns">
                <input type="hidden" name="id" value="{entry['id'] if entry else ''}">
                <label>Data do fato<input type="date" name="fact_date" value="{escape(form['fact_date'])}" required></label>
                <label>Tipo
                    <select name="entry_type" id="entry_type" required>
                        <option value=""{selected(form['entry_type'], '')}>Selecione</option>
                        <option value="RECEITA"{selected(form['entry_type'], 'RECEITA')}>RECEITA</option>
                        <option value="DESPESA"{selected(form['entry_type'], 'DESPESA')}>DESPESA</option>
                    </select>
                </label>
                <label id="revenue_category_field">Tipo de receita
                    <select name="category_name_receita" id="category_name_receita">
                        <option value="">Selecione</option>
                        {revenue_options}
                    </select>
                </label>
                <label id="expense_category_field">Categoria
                    <select name="category_name_despesa" id="category_name_despesa">
                        <option value="">Selecione</option>
                        {expense_category_options}
                    </select>
                </label>
                <label id="expense_group_field">Tipo de despesa
                    <select name="dre_group" id="dre_group">
                        <option value="">Selecione uma categoria</option>
                        {''.join(f'<option value="{escape(item)}"{selected(form["dre_group"], item)}>{escape(item)}</option>' for item in expense_groups)}
                    </select>
                </label>
                <input type="hidden" name="category_name" id="category_name" value="{escape(form['category_name'])}">
                <label id="receive_method_field">Forma de recebimento
                    <select name="payment_method_receita" id="payment_method_receita">
                        <option value="">Selecione</option>
                        {receive_options}
                    </select>
                </label>
                <label id="payment_method_field">Forma de pagamento
                    <select name="payment_method_despesa" id="payment_method_despesa">
                        <option value="">Selecione</option>
                        {payment_options}
                    </select>
                </label>
                <input type="hidden" name="payment_method" id="payment_method" value="{escape(form['payment_method'])}">
                <label>Valor bruto<input type="number" step="0.01" min="0" name="gross_amount" value="{escape(form['gross_amount'])}" required></label>
                <label>Data receb./pag.<input type="date" name="payment_date" value="{escape(form['payment_date'])}"></label>
                <label>Mês competência<input type="text" id="competence_month_display" value="{escape(format_competence(form['payment_date'] or form['competence_month']))}" readonly></label>
                <input type="hidden" name="competence_month" id="competence_month" value="{escape(form['payment_date'] or form['competence_month'])}">
                <label>Status
                    <select name="status">
                        <option value="planejado"{selected(form['status'], 'planejado')}>Planejado</option>
                        <option value="realizado"{selected(form['status'], 'realizado')}>Realizado</option>
                    </select>
                </label>
                <label class="field-wide">Observações<textarea name="notes" rows="3">{escape(form['notes'])}</textarea></label>
                <div class="actions-row">
                    <button type="submit" class="button">{submit_label}</button>
                    <a href="/lancamentos" class="button button-secondary">Limpar</a>
                </div>
            </form>
        </article>
    </section>
    <section class="panel">
        <h2>Filtros</h2>
        <form method="get" action="/lancamentos" class="form-grid two-columns">
            <label>Tipo
                <select name="entry_type">
                    <option value="">Todos</option>
                    <option value="RECEITA"{selected(filters['entry_type'], 'RECEITA')}>RECEITA</option>
                    <option value="DESPESA"{selected(filters['entry_type'], 'DESPESA')}>DESPESA</option>
                </select>
            </label>
            <label>Categoria
                <select name="category_name">
                    <option value="">Todas</option>
                    {category_filter_options}
                </select>
            </label>
            <label>Data inicial<input type="date" name="date_from" value="{escape(filters['date_from'])}"></label>
            <label>Data final<input type="date" name="date_to" value="{escape(filters['date_to'])}"></label>
            <div class="actions-row">
                <button type="submit" class="button">Filtrar</button>
                <a href="/lancamentos" class="button button-secondary">Resetar</a>
            </div>
        </form>
    </section>
    <section class="panel">
        <h2>Movimentações</h2>
        <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Data</th>
                    <th>Tipo</th>
                    <th>Categoria</th>
                    <th>Sub categoria</th>
                    <th>Forma</th>
                    <th>Bruto</th>
                    <th>Taxa %</th>
                    <th>Taxa R$</th>
                    <th>Líquido</th>
                    <th>Ações</th>
                </tr>
            </thead>
            <tbody>{table_html}</tbody>
        </table>
        </div>
    </section>
    <script>
    (function() {{
      const entryType = document.getElementById('entry_type');
      const revenueField = document.getElementById('revenue_category_field');
      const expenseGroupField = document.getElementById('expense_group_field');
      const expenseCategoryField = document.getElementById('expense_category_field');
      const receiveField = document.getElementById('receive_method_field');
      const paymentField = document.getElementById('payment_method_field');
      const revenueSelect = document.getElementById('category_name_receita');
      const expenseGroupSelect = document.getElementById('dre_group');
      const expenseSelect = document.getElementById('category_name_despesa');
      const hiddenCategory = document.getElementById('category_name');
      const receiveSelect = document.getElementById('payment_method_receita');
      const paymentSelect = document.getElementById('payment_method_despesa');
      const hiddenMethod = document.getElementById('payment_method');
      const paymentDateInput = document.querySelector('input[name="payment_date"]');
      const competenceHidden = document.getElementById('competence_month');
      const competenceDisplay = document.getElementById('competence_month_display');

      function updateCompetence() {{
        const raw = paymentDateInput.value;
        competenceHidden.value = raw;
        if (!raw) {{
          competenceDisplay.value = '';
          return;
        }}
        const [year, month] = raw.split('-');
        const months = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
        competenceDisplay.value = `${{months[Number(month) - 1]}}/${{year.slice(-2)}}`;
      }}

      function syncExpenseGroupFromCategory() {{
        const selected = expenseSelect.selectedOptions[0];
        const group = selected && selected.dataset.group ? selected.dataset.group : '';
        expenseGroupSelect.value = group;
      }}

      function syncForm() {{
        const isReceita = entryType.value === 'RECEITA';
        const isDespesa = entryType.value === 'DESPESA';
        revenueField.style.display = isReceita ? 'grid' : 'none';
        receiveField.style.display = isReceita ? 'grid' : 'none';
        expenseGroupField.style.display = isDespesa ? 'grid' : 'none';
        expenseCategoryField.style.display = isDespesa ? 'grid' : 'none';
        paymentField.style.display = isDespesa ? 'grid' : 'none';
        if (isReceita) {{
          hiddenCategory.value = revenueSelect.value;
          hiddenMethod.value = receiveSelect.value;
          expenseSelect.required = false;
          expenseGroupSelect.required = false;
          revenueSelect.required = true;
          receiveSelect.required = true;
        }} else if (isDespesa) {{
          syncExpenseGroupFromCategory();
          hiddenCategory.value = expenseSelect.value;
          hiddenMethod.value = paymentSelect.value;
          expenseSelect.required = true;
          expenseGroupSelect.required = false;
          revenueSelect.required = false;
          receiveSelect.required = false;
        }} else {{
          hiddenCategory.value = '';
          hiddenMethod.value = '';
          revenueSelect.required = false;
          receiveSelect.required = false;
          expenseSelect.required = false;
          expenseGroupSelect.required = false;
        }}
      }}

      entryType.addEventListener('change', syncForm);
      revenueSelect.addEventListener('change', syncForm);
      receiveSelect.addEventListener('change', syncForm);
      expenseSelect.addEventListener('change', syncForm);
      paymentSelect.addEventListener('change', syncForm);
      paymentDateInput.addEventListener('change', updateCompetence);
      expenseGroupSelect.setAttribute('disabled', 'disabled');
      updateCompetence();
      syncForm();
    }})();
    </script>
    """
    return render_layout("Lançamentos", content, user=user, flash=context.get("flash", ""), flash_kind=context.get("flash_kind", "success"))


def cash_flow_page(user, rows, filters) -> bytes:
    lines = []
    for item in rows:
        lines.append(
            f"""
            <tr>
                <td>{format_date(item['date'])}</td>
                <td>{format_currency(item['opening'])}</td>
                <td>{format_currency(item['entradas'])}</td>
                <td>{format_currency(item['saidas'])}</td>
                <td>{format_currency(item['closing'])}</td>
            </tr>
            """
        )
    body = "".join(lines) if lines else '<tr><td colspan="5" class="empty-state">Sem lançamentos no período selecionado.</td></tr>'
    content = f"""
    <section class="panel">
        <form method="get" action="/fluxo-caixa" class="form-grid two-columns">
            <label>Data inicial<input type="date" name="start_date" value="{escape(filters['start_date'])}"></label>
            <label>Saldo inicial<input type="number" step="0.01" name="opening_balance" value="{escape(filters['opening_balance'])}"></label>
            <div class="actions-row">
                <button type="submit" class="button">Atualizar</button>
                <a href="/fluxo-caixa" class="button button-secondary">Resetar</a>
            </div>
        </form>
    </section>
    <section class="panel">
        <div class="table-wrap">
        <table>
            <thead>
                <tr><th>Data</th><th>Saldo inicial</th><th>Entradas</th><th>Saídas</th><th>Saldo final</th></tr>
            </thead>
            <tbody>{body}</tbody>
        </table>
        </div>
    </section>
    """
    return render_layout("Fluxo de Caixa", content, user=user)


def dre_page(user, summary, filters) -> bytes:
    rows = [
        ("(+) Receita Bruta", summary["gross_revenue"]),
        ("(-) Impostos", summary["taxes"]),
        ("(=) Receita Líquida", summary["net_revenue"]),
        ("(-) Custos Diretos", summary["direct_costs"]),
        ("(=) Lucro Bruto", summary["gross_profit"]),
        ("(-) Despesas de vendas", summary["selling_expenses"]),
        ("(-) Despesas Operacionais", summary["operating_expenses"]),
        ("(=) Lucro Operacional", summary["operating_profit"]),
        ("(+/-) Receitas / Despesas Diversas", summary["diverse_result"]),
        ("(=) Lucro ou Prejuízo", summary["pre_transfer"]),
        ("(-) Transferência de Lucro", summary["profit_transfer"]),
        ("(=) Lucro ou Prejuízo Final", summary["net_result"]),
    ]
    dre_lines = "".join(
        f"<tr><td>{escape(label)}</td><td>{format_currency(value)}</td></tr>"
        for label, value in rows
    )
    content = f"""
    <section class="panel">
        <form method="get" action="/dre" class="form-grid">
            <label>Mês competência<input type="month" name="competence_month" value="{escape(filters['competence_month'])}"></label>
            <div class="actions-row">
                <button type="submit" class="button">Atualizar</button>
                <a href="/dre" class="button button-secondary">Resetar</a>
            </div>
        </form>
    </section>
    <section class="panel">
        <div class="table-wrap">
        <table>
            <thead>
                <tr><th>Descrição</th><th>Valor</th></tr>
            </thead>
            <tbody>{dre_lines}</tbody>
        </table>
        </div>
    </section>
    """
    return render_layout("DRE", content, user=user)


def conciliation_page(user, summary, filters, payment_methods) -> bytes:
    rows = "".join(
        f"""
        <tr>
            <td>{format_competence(item['competence_month'])}</td>
            <td>{escape(item['entry_type'])}</td>
            <td>{escape(item['payment_method'])}</td>
            <td>{format_date(item['fact_date'])}</td>
            <td>{format_date(item['payment_date'])}</td>
            <td>{escape(item['category_name'])}</td>
            <td>{format_currency(item['net_amount'])}</td>
        </tr>
        """
        for item in summary["rows"]
    )
    if not rows:
        rows = '<tr><td colspan="7" class="empty-state">Nenhuma movimentação encontrada para os filtros informados.</td></tr>'
    payment_options = "".join(
        f'<option value="{escape(name)}"{selected(filters["payment_method"], name)}>{escape(name)}</option>'
        for name in payment_methods
    )
    content = f"""
    <section class="panel">
        <form method="get" action="/conciliacao" class="form-grid two-columns">
            <label>Mês competência<input type="month" name="competence_month" value="{escape(filters['competence_month'])}"></label>
            <label>Tipo
                <select name="entry_type">
                    <option value="">Todos</option>
                    <option value="RECEITA"{selected(filters['entry_type'], 'RECEITA')}>Receita</option>
                    <option value="DESPESA"{selected(filters['entry_type'], 'DESPESA')}>Despesa</option>
                </select>
            </label>
            <label class="field-wide">Forma de pagamento / recebimento
                <select name="payment_method">
                    <option value="">Todas</option>
                    {payment_options}
                </select>
            </label>
            <div class="actions-row">
                <button type="submit" class="button">Filtrar</button>
                <a href="/conciliacao" class="button button-secondary">Limpar</a>
            </div>
        </form>
    </section>
    <section class="panel">
        <div class="mini-stats">
            <article class="mini-stat">
                <span>Total líquido</span>
                <strong>{format_currency(summary["total_net_amount"])}</strong>
            </article>
            <article class="mini-stat">
                <span>Movimentações</span>
                <strong>{len(summary["rows"])}</strong>
            </article>
        </div>
        <div class="table-wrap">
        <table>
            <thead>
                <tr><th>Mês</th><th>Tipo</th><th>Forma</th><th>Data do fato</th><th>Data receb./pag.</th><th>Categoria</th><th>Valor líquido</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        </div>
    </section>
    """
    return render_layout("Conciliação", content, user=user)


def my_account_page(user, flash: str = "", flash_kind: str = "success") -> bytes:
    content = f"""
    <section class="panel account-panel">
        <h2>Minha conta</h2>
        <form method="post" action="/minha-conta" class="form-grid">
            <label>Nome
                <input type="text" name="name" value="{escape(user['name'])}" required>
            </label>
            <label>E-mail
                <input type="email" value="{escape(user['email'])}" disabled>
            </label>
            <label>Nova senha
                <input type="password" name="password" placeholder="Preencha apenas se quiser alterar">
            </label>
            <div class="actions-row">
                <button type="submit" class="button">Salvar alterações</button>
            </div>
        </form>
    </section>
    """
    return render_layout("Minha conta", content, user=user, flash=flash, flash_kind=flash_kind)


def users_page(user, users, flash: str = "", flash_kind: str = "success") -> bytes:
    rows = "".join(
        f"""
        <tr>
            <td>{escape(item['name'])}</td>
            <td>{escape(item['email'])}</td>
            <td>{'Administrador' if item['role'] == 'admin' else 'Usuário'}</td>
            <td>{'Aprovado' if item['approved'] else 'Pendente'}</td>
            <td>
                <div class="table-actions">
                    {'<form method="post" action="/admin/usuarios/aprovar"><input type="hidden" name="id" value="' + str(item['id']) + '"><button type="submit" class="link-button">Aprovar</button></form>' if not item['approved'] else ''}
                    {'' if item['id'] == user['id'] else '<form method="post" action="/admin/usuarios/perfil"><input type="hidden" name="id" value="' + str(item['id']) + '"><input type="hidden" name="role" value="' + ('user' if item['role'] == 'admin' else 'admin') + '"><button type="submit" class="link-button">' + ('Rebaixar para usuário' if item['role'] == 'admin' else 'Promover para admin') + '</button></form>'}
                    <form method="post" action="/admin/usuarios/excluir" onsubmit="return confirm('Remover usuário?');">
                        <input type="hidden" name="id" value="{item['id']}">
                        <button type="submit" class="link-button danger-link">Remover</button>
                    </form>
                </div>
            </td>
        </tr>
        """
        for item in users
    )
    content = f"""
    <section class="panel">
        <h2>Usuários cadastrados</h2>
        <div class="table-wrap">
        <table>
            <thead>
                <tr><th>Nome</th><th>E-mail</th><th>Perfil</th><th>Status</th><th>Ações</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        </div>
    </section>
    """
    return render_layout("Usuários", content, user=user, flash=flash, flash_kind=flash_kind)


def audit_page(user, logs) -> bytes:
    rows = "".join(
        f"""
        <tr>
            <td>{format_datetime(item['created_at'])}</td>
            <td>{escape(item['user_name'] or '-')}</td>
            <td>{escape(item['user_email'] or '-')}</td>
            <td>{escape(item['action'])}</td>
            <td>{escape(item['entity'])}</td>
            <td>{escape(item['details'] or '-')}</td>
            <td>{escape(item['ip_address'] or '-')}</td>
        </tr>
        """
        for item in logs
    )
    content = f"""
    <section class="panel">
        <h2>Log de auditoria</h2>
        <p>Somente administradores conseguem visualizar acessos, aprovações, alterações e exclusões realizadas na plataforma.</p>
        <div class="table-wrap compact-table">
            <table>
                <thead>
                    <tr><th>Data</th><th>Usuário</th><th>E-mail</th><th>Ação</th><th>Área</th><th>Detalhes</th><th>IP</th></tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </section>
    """
    return render_layout("Auditoria", content, user=user)


def references_page(user, context: dict) -> bytes:
    categories = sorted(context["categories"], key=lambda item: item["name"].casefold())
    payment_methods = sorted(context["payment_methods"], key=lambda item: item["name"].casefold())
    receive_methods = sorted(context["receive_methods"], key=lambda item: item["name"].casefold())
    editing_category = context.get("editing_category")
    editing_payment_method = context.get("editing_payment_method")
    editing_receive_method = context.get("editing_receive_method")

    category_rows = "".join(
        f"""
        <tr>
            <td>{escape(item['name'])}</td>
            <td>{escape(item['entry_type'])}</td>
            <td>{escape(item['dre_group'])}</td>
            <td>
                <div class="table-actions">
                    <a href="/admin/referencias?edit_category={item['id']}" class="link-button">Editar</a>
                    <form method="post" action="/admin/referencias/categorias/excluir" onsubmit="return confirm('Excluir categoria?');">
                        <input type="hidden" name="id" value="{item['id']}">
                        <button type="submit" class="link-button danger-link">Excluir</button>
                    </form>
                </div>
            </td>
        </tr>
        """
        for item in categories
    )
    payment_rows = "".join(
        f"""
        <tr>
            <td>{escape(item['name'])}</td>
            <td>{format_percent(item['fee_percent'])}</td>
            <td>
                <div class="table-actions">
                    <a href="/admin/referencias?edit_payment={item['id']}" class="link-button">Editar</a>
                    <form method="post" action="/admin/referencias/formas/excluir" onsubmit="return confirm('Excluir forma de pagamento?');">
                        <input type="hidden" name="id" value="{item['id']}">
                        <button type="submit" class="link-button danger-link">Excluir</button>
                    </form>
                </div>
            </td>
        </tr>
        """
        for item in payment_methods
    )
    receive_rows = "".join(
        f"""
        <tr>
            <td>{escape(item['name'])}</td>
            <td>{format_percent(item['fee_percent'])}</td>
            <td>
                <div class="table-actions">
                    <a href="/admin/referencias?edit_receive={item['id']}" class="link-button">Editar</a>
                    <form method="post" action="/admin/referencias/recebimentos/excluir" onsubmit="return confirm('Excluir forma de recebimento?');">
                        <input type="hidden" name="id" value="{item['id']}">
                        <button type="submit" class="link-button danger-link">Excluir</button>
                    </form>
                </div>
            </td>
        </tr>
        """
        for item in receive_methods
    )
    category_submit = "Atualizar categoria" if editing_category else "Criar categoria"
    payment_submit = "Atualizar forma" if editing_payment_method else "Criar forma"
    receive_submit = "Atualizar recebimento" if editing_receive_method else "Criar recebimento"
    content = f"""
    <section class="panel-grid">
        <article class="panel panel-wide">
            <h2>Categorias</h2>
            <form method="post" action="/admin/referencias/categorias/salvar" class="form-grid">
                <input type="hidden" name="id" value="{editing_category['id'] if editing_category else ''}">
                <label>Nome da categoria<input type="text" name="name" value="{escape(editing_category['name']) if editing_category else ''}" required></label>
                <label>Tipo
                    <select name="entry_type">
                        <option value="RECEITA"{selected(editing_category['entry_type'] if editing_category else 'DESPESA', 'RECEITA')}>RECEITA</option>
                        <option value="DESPESA"{selected(editing_category['entry_type'] if editing_category else 'DESPESA', 'DESPESA')}>DESPESA</option>
                    </select>
                </label>
                <label>Sub categoria DRE<input type="text" name="dre_group" value="{escape(editing_category['dre_group']) if editing_category else ''}" required></label>
                <div class="actions-row">
                    <button type="submit" class="button">{category_submit}</button>
                    <a href="/admin/referencias" class="button button-secondary">Limpar</a>
                </div>
            </form>
            <div class="table-wrap compact-table">
                <table class="reference-table">
                    <thead><tr><th>Categoria</th><th>Tipo</th><th>Sub categoria</th><th>Ações</th></tr></thead>
                    <tbody>{category_rows}</tbody>
                </table>
            </div>
        </article>
    </section>
    <section class="panel-grid">
        <article class="panel">
            <h2>Formas de recebimento</h2>
            <form method="post" action="/admin/referencias/recebimentos/salvar" class="form-grid">
                <input type="hidden" name="id" value="{editing_receive_method['id'] if editing_receive_method else ''}">
                <label>Nome da forma<input type="text" name="name" value="{escape(editing_receive_method['name']) if editing_receive_method else ''}" required></label>
                <label>Taxa percentual
                    <input type="number" step="0.0001" min="0" name="fee_percent" value="{editing_receive_method['fee_percent'] if editing_receive_method else '0'}" required>
                </label>
                <div class="actions-row">
                    <button type="submit" class="button">{receive_submit}</button>
                    <a href="/admin/referencias" class="button button-secondary">Limpar</a>
                </div>
            </form>
            <div class="table-wrap compact-table">
                <table class="reference-table">
                    <thead><tr><th>Forma recebimento</th><th>Taxa</th><th>Ações</th></tr></thead>
                    <tbody>{receive_rows}</tbody>
                </table>
            </div>
        </article>
        <article class="panel">
            <h2>Formas de pagamento</h2>
            <form method="post" action="/admin/referencias/formas/salvar" class="form-grid">
                <input type="hidden" name="id" value="{editing_payment_method['id'] if editing_payment_method else ''}">
                <label>Nome da forma<input type="text" name="name" value="{escape(editing_payment_method['name']) if editing_payment_method else ''}" required></label>
                <label>Taxa percentual
                    <input type="number" step="0.0001" min="0" name="fee_percent" value="{editing_payment_method['fee_percent'] if editing_payment_method else '0'}" required>
                </label>
                <div class="actions-row">
                    <button type="submit" class="button">{payment_submit}</button>
                    <a href="/admin/referencias" class="button button-secondary">Limpar</a>
                </div>
            </form>
            <div class="table-wrap compact-table">
                <table class="reference-table">
                    <thead><tr><th>Forma</th><th>Taxa</th><th>Ações</th></tr></thead>
                    <tbody>{payment_rows}</tbody>
                </table>
            </div>
        </article>
    </section>
    """
    return render_layout("Referências", content, user=user, flash=context.get("flash", ""), flash_kind=context.get("flash_kind", "success"))
