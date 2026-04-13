from datetime import date
from http import cookies
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from app.db import (
    approve_user,
    cash_flow_summary,
    conciliation_summary,
    count_pending_users,
    create_category,
    create_audit_log,
    create_payment_method,
    create_receive_method,
    create_session,
    dashboard_metrics,
    delete_category,
    delete_cash_entry,
    delete_payment_method,
    delete_receive_method,
    delete_session,
    delete_user,
    dre_summary,
    get_cash_entry,
    get_category_by_id,
    get_opening_balance,
    get_payment_method_by_id,
    get_receive_method_by_id,
    get_user_by_email,
    get_user_by_session,
    initialize_database,
    list_audit_logs,
    list_cash_entries,
    list_categories,
    list_payment_methods,
    list_receive_methods,
    list_users,
    register_user,
    save_cash_entry,
    set_opening_balance,
    update_category,
    update_payment_method,
    update_receive_method,
    update_user_name,
    update_user_password,
    update_user_role,
    verify_password,
)
from app.views import (
    audit_page,
    cash_entries_page,
    cash_flow_page,
    conciliation_page,
    dashboard_page,
    dre_page,
    login_page,
    my_account_page,
    register_page,
    references_page,
    users_page,
)


STATIC_DIR = Path(__file__).resolve().parent / "static"


def parse_form(environ):
    try:
        size = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        size = 0
    raw = environ["wsgi.input"].read(size).decode("utf-8")
    parsed = parse_qs(raw)
    return {key: values[0] for key, values in parsed.items()}


def parse_query(environ):
    parsed = parse_qs(environ.get("QUERY_STRING", ""))
    return {key: values[0] for key, values in parsed.items()}


def read_cookie(environ, name: str):
    raw_cookie = environ.get("HTTP_COOKIE", "")
    if not raw_cookie:
        return None
    jar = cookies.SimpleCookie()
    jar.load(raw_cookie)
    morsel = jar.get(name)
    return morsel.value if morsel else None


def html_response(start_response, body: bytes, status="200 OK", headers=None):
    headers = headers or []
    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))]
    response_headers.extend(headers)
    start_response(status, response_headers)
    return [body]


def redirect(start_response, location: str, headers=None):
    headers = headers or []
    headers.append(("Location", location))
    start_response("302 Found", headers)
    return [b""]


def static_response(start_response, path: Path):
    if not path.exists() or not path.is_file():
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return ["Arquivo não encontrado".encode("utf-8")]
    content = path.read_bytes()
    content_type = "text/css; charset=utf-8" if path.suffix == ".css" else "application/octet-stream"
    start_response("200 OK", [("Content-Type", content_type), ("Content-Length", str(len(content)))])
    return [content]


def current_user(environ):
    token = read_cookie(environ, "session_token")
    if not token:
        return None
    user = get_user_by_session(token)
    if not user:
        return None
    payload = dict(user)
    if payload["role"] == "admin":
        payload["pending_users"] = count_pending_users()
    return payload


def client_ip(environ) -> str:
    forwarded = environ.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return environ.get("REMOTE_ADDR", "")


def log_access(user, environ, area: str):
    create_audit_log("acesso", area, user=user, details=f"Acesso a {area}", ip_address=client_ip(environ))


def require_auth(environ, start_response):
    user = current_user(environ)
    if not user:
        return None, redirect(start_response, "/")
    return user, None


def require_admin(environ, start_response):
    user, response = require_auth(environ, start_response)
    if response:
        return None, response
    if user["role"] != "admin":
        return None, html_response(start_response, "Acesso negado".encode("utf-8"), status="403 Forbidden")
    return user, None


def default_entry_form(entry=None):
    return {
        "fact_date": entry["fact_date"] if entry else date.today().isoformat(),
        "entry_type": entry["entry_type"] if entry else "",
        "dre_group": entry["dre_group"] if entry else "",
        "category_name": entry["category_name"] if entry else "",
        "payment_method": entry["payment_method"] if entry else "",
        "gross_amount": f"{entry['gross_amount']:.2f}" if entry else "",
        "payment_date": entry["payment_date"] if entry else "",
        "competence_month": entry["competence_month"] if entry else "",
        "notes": entry["notes"] if entry and entry["notes"] else "",
        "status": entry["status"] if entry else "planejado",
    }


def build_entries_context(query, flash="", flash_kind="success"):
    filters = {
        "entry_type": query.get("entry_type", ""),
        "category_name": query.get("category_name", ""),
        "date_from": query.get("date_from", ""),
        "date_to": query.get("date_to", ""),
    }
    editing_entry = None
    if query.get("edit"):
        try:
            editing_entry = get_cash_entry(int(query["edit"]))
        except ValueError:
            editing_entry = None
    return {
        "filters": filters,
        "form": default_entry_form(editing_entry),
        "editing_entry": editing_entry,
        "entries": list_cash_entries(filters),
        "categories": list_categories(),
        "payment_methods": list_payment_methods(),
        "receive_methods": list_receive_methods(),
        "flash": flash,
        "flash_kind": flash_kind,
    }


def build_references_context(query, flash="", flash_kind="success"):
    editing_category = None
    editing_payment_method = None
    editing_receive_method = None
    if query.get("edit_category"):
        try:
            editing_category = get_category_by_id(int(query["edit_category"]))
        except ValueError:
            editing_category = None
    if query.get("edit_payment"):
        try:
            editing_payment_method = get_payment_method_by_id(int(query["edit_payment"]))
        except ValueError:
            editing_payment_method = None
    if query.get("edit_receive"):
        try:
            editing_receive_method = get_receive_method_by_id(int(query["edit_receive"]))
        except ValueError:
            editing_receive_method = None
    return {
        "categories": list_categories(),
        "payment_methods": list_payment_methods(),
        "receive_methods": list_receive_methods(),
        "opening_balance": f"{get_opening_balance():.2f}",
        "editing_category": editing_category,
        "editing_payment_method": editing_payment_method,
        "editing_receive_method": editing_receive_method,
        "flash": flash,
        "flash_kind": flash_kind,
    }


def application(environ, start_response):
    initialize_database()
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET").upper()

    if path.startswith("/static/"):
        file_path = STATIC_DIR / path.replace("/static/", "", 1)
        return static_response(start_response, file_path)

    if path == "/" and method == "GET":
        if current_user(environ):
            return redirect(start_response, "/dashboard")
        return html_response(start_response, login_page())

    if path == "/criar-conta" and method == "GET":
        return html_response(start_response, register_page())

    if path == "/login" and method == "POST":
        form = parse_form(environ)
        user = get_user_by_email(form.get("email", "").strip().lower())
        if not user or not verify_password(form.get("password", ""), user["password_hash"]):
            create_audit_log(
                "login_falhou",
                "autenticacao",
                details=f"Tentativa com e-mail {form.get('email', '').strip().lower()}",
                ip_address=client_ip(environ),
            )
            return html_response(start_response, login_page("E-mail ou senha inválidos."))
        if not user["approved"]:
            create_audit_log(
                "login_bloqueado",
                "autenticacao",
                user=user,
                details="Conta aguardando aprovação.",
                ip_address=client_ip(environ),
            )
            return html_response(start_response, login_page("Sua conta ainda está aguardando aprovação do administrador."))
        token = create_session(user["id"])
        create_audit_log("login", "autenticacao", user=user, details="Login realizado com sucesso.", ip_address=client_ip(environ))
        cookie = cookies.SimpleCookie()
        cookie["session_token"] = token
        cookie["session_token"]["path"] = "/"
        cookie["session_token"]["httponly"] = True
        return redirect(start_response, "/dashboard", headers=[("Set-Cookie", cookie.output(header="").strip())])

    if path == "/register" and method == "POST":
        form = parse_form(environ)
        try:
            register_user(
                form.get("name", "").strip(),
                form.get("email", "").strip().lower(),
                form.get("password", ""),
            )
            created_user = get_user_by_email(form.get("email", "").strip().lower())
            create_audit_log(
                "cadastro_solicitado",
                "usuario",
                user=created_user,
                entity_id=created_user["id"] if created_user else None,
                details="Nova conta criada e aguardando aprovação.",
                ip_address=client_ip(environ),
            )
            return html_response(start_response, register_page("Conta criada. Aguarde a aprovação do administrador."))
        except Exception:
            return html_response(start_response, register_page("Não foi possível criar a conta. Verifique se o e-mail já existe.", flash_kind="error"), status="400 Bad Request")

    if path == "/logout" and method == "GET":
        user = current_user(environ)
        token = read_cookie(environ, "session_token")
        if token:
            delete_session(token)
        if user:
            create_audit_log("logout", "autenticacao", user=user, details="Logout realizado.", ip_address=client_ip(environ))
        cookie = cookies.SimpleCookie()
        cookie["session_token"] = ""
        cookie["session_token"]["path"] = "/"
        cookie["session_token"]["expires"] = "Thu, 01 Jan 1970 00:00:00 GMT"
        return redirect(start_response, "/", headers=[("Set-Cookie", cookie.output(header="").strip())])

    if path == "/dashboard" and method == "GET":
        user, response = require_auth(environ, start_response)
        if response:
            return response
        log_access(user, environ, "dashboard")
        filters = parse_query(environ)
        return html_response(
            start_response,
            dashboard_page(
                user,
                dashboard_metrics(filters.get("date_from"), filters.get("date_to")),
            ),
        )

    if path == "/minha-conta" and method == "GET":
        user, response = require_auth(environ, start_response)
        if response:
            return response
        log_access(user, environ, "minha_conta")
        return html_response(start_response, my_account_page(user))

    if path == "/minha-conta" and method == "POST":
        user, response = require_auth(environ, start_response)
        if response:
            return response
        form = parse_form(environ)
        try:
            new_name = form.get("name", "").strip()
            new_password = form.get("password", "").strip()
            if new_name:
                update_user_name(user["id"], new_name)
            if new_password:
                update_user_password(user["id"], new_password)
            create_audit_log(
                "minha_conta_atualizada",
                "usuario",
                user=user,
                entity_id=user["id"],
                details="Dados da própria conta atualizados.",
                ip_address=client_ip(environ),
            )
            refreshed_user = current_user(environ) or user
            return html_response(start_response, my_account_page(refreshed_user, flash="Dados atualizados com sucesso."))
        except Exception:
            refreshed_user = current_user(environ) or user
            return html_response(
                start_response,
                my_account_page(refreshed_user, flash="Não foi possível atualizar sua conta.", flash_kind="error"),
                status="400 Bad Request",
            )

    if path == "/lancamentos" and method == "GET":
        user, response = require_auth(environ, start_response)
        if response:
            return response
        log_access(user, environ, "lancamentos")
        context = build_entries_context(parse_query(environ))
        return html_response(start_response, cash_entries_page(user, context))

    if path == "/lancamentos/salvar" and method == "POST":
        user, response = require_auth(environ, start_response)
        if response:
            return response
        form = parse_form(environ)
        try:
            entry_id = int(form["id"]) if form.get("id") else None
            saved_id = save_cash_entry(
                {
                    "fact_date": form.get("fact_date", ""),
                    "entry_type": form.get("entry_type", "RECEITA"),
                    "dre_group": form.get("dre_group", "RECEITA"),
                    "category_name": form.get("category_name", ""),
                    "payment_method": form.get("payment_method", ""),
                    "gross_amount": float(form.get("gross_amount", "0").replace(",", ".")),
                    "payment_date": form.get("payment_date", ""),
                    "competence_month": form.get("payment_date", ""),
                    "notes": form.get("notes", "").strip(),
                    "status": form.get("status", "planejado"),
                },
                user["id"],
                entry_id=entry_id,
            )
            create_audit_log(
                "lancamento_atualizado" if entry_id else "lancamento_criado",
                "lancamento",
                user=user,
                entity_id=saved_id,
                details=f"{form.get('entry_type', '').strip()} - {form.get('category_name', '').strip()}",
                ip_address=client_ip(environ),
            )
            context = build_entries_context({}, flash="Lançamento salvo com sucesso.")
            return html_response(start_response, cash_entries_page(user, context))
        except Exception:
            context = build_entries_context({}, flash="Não foi possível salvar o lançamento. Revise os campos.", flash_kind="error")
            return html_response(start_response, cash_entries_page(user, context), status="400 Bad Request")

    if path == "/lancamentos/excluir" and method == "POST":
        user, response = require_auth(environ, start_response)
        if response:
            return response
        form = parse_form(environ)
        try:
            entry_id = int(form["id"])
            delete_cash_entry(entry_id)
            create_audit_log("lancamento_excluido", "lancamento", user=user, entity_id=entry_id, details="Lançamento removido.", ip_address=client_ip(environ))
            context = build_entries_context({}, flash="Lançamento excluído.")
            return html_response(start_response, cash_entries_page(user, context))
        except Exception:
            context = build_entries_context({}, flash="Não foi possível excluir o lançamento.", flash_kind="error")
            return html_response(start_response, cash_entries_page(user, context), status="400 Bad Request")

    if path == "/fluxo-caixa" and method == "GET":
        user, response = require_auth(environ, start_response)
        if response:
            return response
        log_access(user, environ, "fluxo_caixa")
        filters = parse_query(environ)
        start_date = filters.get("start_date") or date.today().isoformat()
        opening_balance = float((filters.get("opening_balance") or str(get_opening_balance())).replace(",", "."))
        rows = cash_flow_summary(start_date, opening_balance, days=30)
        period = {"start_date": start_date, "opening_balance": f"{opening_balance:.2f}"}
        return html_response(start_response, cash_flow_page(user, rows, period))

    if path == "/dre" and method == "GET":
        user, response = require_auth(environ, start_response)
        if response:
            return response
        log_access(user, environ, "dre")
        filters = parse_query(environ)
        period = {"competence_month": filters.get("competence_month", "")}
        return html_response(
            start_response,
            dre_page(user, dre_summary(period["competence_month"] or None), period),
        )

    if path == "/conciliacao" and method == "GET":
        user, response = require_auth(environ, start_response)
        if response:
            return response
        log_access(user, environ, "conciliacao")
        filters = {
            "competence_month": parse_query(environ).get("competence_month", ""),
            "entry_type": parse_query(environ).get("entry_type", ""),
            "payment_method": parse_query(environ).get("payment_method", ""),
        }
        methods = sorted(
            {item["name"] for item in list_payment_methods()} | {item["name"] for item in list_receive_methods()},
            key=str.casefold,
        )
        summary = conciliation_summary(filters)
        return html_response(start_response, conciliation_page(user, summary, filters, methods))

    if path == "/admin/usuarios" and method == "GET":
        user, response = require_admin(environ, start_response)
        if response:
            return response
        log_access(user, environ, "admin_usuarios")
        return html_response(start_response, users_page(user, list_users()))

    if path == "/admin/usuarios/aprovar" and method == "POST":
        user, response = require_admin(environ, start_response)
        if response:
            return response
        form = parse_form(environ)
        try:
            target_id = int(form["id"])
            approve_user(target_id)
            create_audit_log("usuario_aprovado", "usuario", user=user, entity_id=target_id, details="Conta aprovada pelo administrador.", ip_address=client_ip(environ))
            refreshed_user = current_user(environ) or user
            return html_response(start_response, users_page(refreshed_user, list_users(), flash="Usuário aprovado com sucesso."))
        except Exception:
            refreshed_user = current_user(environ) or user
            return html_response(
                start_response,
                users_page(refreshed_user, list_users(), flash="Não foi possível aprovar o usuário.", flash_kind="error"),
                status="400 Bad Request",
            )

    if path == "/admin/usuarios/perfil" and method == "POST":
        user, response = require_admin(environ, start_response)
        if response:
            return response
        form = parse_form(environ)
        try:
            target_id = int(form["id"])
            new_role = form.get("role", "user")
            if target_id == user["id"]:
                return html_response(
                    start_response,
                    users_page(user, list_users(), flash="Use outra conta de administrador para alterar o seu próprio perfil.", flash_kind="error"),
                    status="400 Bad Request",
                )
            update_user_role(target_id, new_role)
            create_audit_log(
                "perfil_alterado",
                "usuario",
                user=user,
                entity_id=target_id,
                details=f"Perfil alterado para {new_role}.",
                ip_address=client_ip(environ),
            )
            refreshed_user = current_user(environ) or user
            return html_response(start_response, users_page(refreshed_user, list_users(), flash="Perfil atualizado com sucesso."))
        except Exception:
            refreshed_user = current_user(environ) or user
            return html_response(
                start_response,
                users_page(refreshed_user, list_users(), flash="Não foi possível alterar o perfil do usuário.", flash_kind="error"),
                status="400 Bad Request",
            )

    if path == "/admin/usuarios/excluir" and method == "POST":
        user, response = require_admin(environ, start_response)
        if response:
            return response
        form = parse_form(environ)
        try:
            target_id = int(form["id"])
            if target_id == user["id"]:
                return html_response(
                    start_response,
                    users_page(user, list_users(), flash="Não é possível remover o usuário logado.", flash_kind="error"),
                    status="400 Bad Request",
                )
            delete_user(target_id)
            create_audit_log("usuario_removido", "usuario", user=user, entity_id=target_id, details="Conta removida pelo administrador.", ip_address=client_ip(environ))
            refreshed_user = current_user(environ) or user
            return html_response(start_response, users_page(refreshed_user, list_users(), flash="Usuário removido com sucesso."))
        except Exception:
            refreshed_user = current_user(environ) or user
            return html_response(
                start_response,
                users_page(refreshed_user, list_users(), flash="Não foi possível remover o usuário.", flash_kind="error"),
                status="400 Bad Request",
            )

    if path == "/admin/auditoria" and method == "GET":
        user, response = require_admin(environ, start_response)
        if response:
            return response
        log_access(user, environ, "admin_auditoria")
        return html_response(start_response, audit_page(user, list_audit_logs()))

    if path == "/admin/referencias" and method == "GET":
        user, response = require_admin(environ, start_response)
        if response:
            return response
        log_access(user, environ, "admin_referencias")
        return html_response(start_response, references_page(user, build_references_context(parse_query(environ))))

    if path == "/admin/referencias" and method == "POST":
        user, response = require_admin(environ, start_response)
        if response:
            return response
        form = parse_form(environ)
        try:
            set_opening_balance(form.get("opening_balance", "0").replace(",", "."))
            create_audit_log("configuracao_fluxo_atualizada", "configuracao", user=user, details="Saldo inicial do fluxo de caixa atualizado.", ip_address=client_ip(environ))
            return html_response(start_response, references_page(user, build_references_context({}, flash="Configuração salva.")))
        except Exception:
            return html_response(start_response, references_page(user, build_references_context({}, flash="Não foi possível salvar a configuração.", flash_kind="error")), status="400 Bad Request")

    if path == "/admin/referencias/categorias/salvar" and method == "POST":
        user, response = require_admin(environ, start_response)
        if response:
            return response
        form = parse_form(environ)
        try:
            category_id = int(form["id"]) if form.get("id") else None
            if category_id:
                update_category(category_id, form.get("name", "").strip(), form.get("entry_type", "DESPESA"), form.get("dre_group", "").strip())
                flash = "Categoria atualizada com sucesso."
                action = "categoria_atualizada"
            else:
                create_category(form.get("name", "").strip(), form.get("entry_type", "DESPESA"), form.get("dre_group", "").strip())
                flash = "Categoria criada com sucesso."
                action = "categoria_criada"
            create_audit_log(action, "categoria", user=user, details=form.get("name", "").strip(), ip_address=client_ip(environ))
            return html_response(start_response, references_page(user, build_references_context({}, flash=flash)))
        except Exception:
            return html_response(start_response, references_page(user, build_references_context({}, flash="Não foi possível salvar a categoria.", flash_kind="error")), status="400 Bad Request")

    if path == "/admin/referencias/categorias/excluir" and method == "POST":
        user, response = require_admin(environ, start_response)
        if response:
            return response
        form = parse_form(environ)
        try:
            target_id = int(form["id"])
            delete_category(target_id)
            create_audit_log("categoria_excluida", "categoria", user=user, entity_id=target_id, details="Categoria removida.", ip_address=client_ip(environ))
            return html_response(start_response, references_page(user, build_references_context({}, flash="Categoria excluída.")))
        except Exception:
            return html_response(start_response, references_page(user, build_references_context({}, flash="Não foi possível excluir a categoria.", flash_kind="error")), status="400 Bad Request")

    if path == "/admin/referencias/formas/salvar" and method == "POST":
        user, response = require_admin(environ, start_response)
        if response:
            return response
        form = parse_form(environ)
        try:
            payment_method_id = int(form["id"]) if form.get("id") else None
            fee_percent = float(form.get("fee_percent", "0").replace(",", "."))
            if payment_method_id:
                update_payment_method(payment_method_id, form.get("name", "").strip(), fee_percent)
                flash = "Forma de pagamento atualizada com sucesso."
                action = "forma_pagamento_atualizada"
            else:
                create_payment_method(form.get("name", "").strip(), fee_percent)
                flash = "Forma de pagamento criada com sucesso."
                action = "forma_pagamento_criada"
            create_audit_log(action, "forma_pagamento", user=user, details=form.get("name", "").strip(), ip_address=client_ip(environ))
            return html_response(start_response, references_page(user, build_references_context({}, flash=flash)))
        except Exception:
            return html_response(start_response, references_page(user, build_references_context({}, flash="Não foi possível salvar a forma de pagamento.", flash_kind="error")), status="400 Bad Request")

    if path == "/admin/referencias/formas/excluir" and method == "POST":
        user, response = require_admin(environ, start_response)
        if response:
            return response
        form = parse_form(environ)
        try:
            target_id = int(form["id"])
            delete_payment_method(target_id)
            create_audit_log("forma_pagamento_excluida", "forma_pagamento", user=user, entity_id=target_id, details="Forma de pagamento removida.", ip_address=client_ip(environ))
            return html_response(start_response, references_page(user, build_references_context({}, flash="Forma de pagamento excluída.")))
        except Exception:
            return html_response(start_response, references_page(user, build_references_context({}, flash="Não foi possível excluir a forma de pagamento.", flash_kind="error")), status="400 Bad Request")

    if path == "/admin/referencias/recebimentos/salvar" and method == "POST":
        user, response = require_admin(environ, start_response)
        if response:
            return response
        form = parse_form(environ)
        try:
            receive_method_id = int(form["id"]) if form.get("id") else None
            fee_percent = float(form.get("fee_percent", "0").replace(",", "."))
            if receive_method_id:
                update_receive_method(receive_method_id, form.get("name", "").strip(), fee_percent)
                flash = "Forma de recebimento atualizada com sucesso."
                action = "forma_recebimento_atualizada"
            else:
                create_receive_method(form.get("name", "").strip(), fee_percent)
                flash = "Forma de recebimento criada com sucesso."
                action = "forma_recebimento_criada"
            create_audit_log(action, "forma_recebimento", user=user, details=form.get("name", "").strip(), ip_address=client_ip(environ))
            return html_response(start_response, references_page(user, build_references_context({}, flash=flash)))
        except Exception:
            return html_response(start_response, references_page(user, build_references_context({}, flash="Não foi possível salvar a forma de recebimento.", flash_kind="error")), status="400 Bad Request")

    if path == "/admin/referencias/recebimentos/excluir" and method == "POST":
        user, response = require_admin(environ, start_response)
        if response:
            return response
        form = parse_form(environ)
        try:
            target_id = int(form["id"])
            delete_receive_method(target_id)
            create_audit_log("forma_recebimento_excluida", "forma_recebimento", user=user, entity_id=target_id, details="Forma de recebimento removida.", ip_address=client_ip(environ))
            return html_response(start_response, references_page(user, build_references_context({}, flash="Forma de recebimento excluída.")))
        except Exception:
            return html_response(start_response, references_page(user, build_references_context({}, flash="Não foi possível excluir a forma de recebimento.", flash_kind="error")), status="400 Bad Request")

    start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
    return ["Página não encontrada".encode("utf-8")]


def run():
    initialize_database()
    with make_server("127.0.0.1", 8000, application) as server:
        print("Servidor ativo em http://127.0.0.1:8000")
        server.serve_forever()


if __name__ == "__main__":
    run()
