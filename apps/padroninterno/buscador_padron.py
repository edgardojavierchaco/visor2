import re

from unidecode import unidecode


TEXT = 'TEXT'
IDENTIFIER_DIGITS = 'IDENTIFIER_DIGITS'
IDENTIFIER_ALNUM = 'IDENTIFIER_ALNUM'

_ACCENTED_CHARS = '\u00c1\u00c9\u00cd\u00d3\u00da\u00dc\u00d1\u00e1\u00e9\u00ed\u00f3\u00fa\u00fc\u00f1'
_UNACCENTED_CHARS = 'AEIOUUNaeiouun'
_ACCENT_TRANSLATION = str.maketrans(_ACCENTED_CHARS, _UNACCENTED_CHARS)
_SQL_COMPAT_INPUT_RE = re.compile(r'[^A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ]+')
_TEXT_SEPARATOR_RE = re.compile(r'[^a-z0-9]+')
_DIGITS_RE = re.compile(r'[^0-9]+')
_ALNUM_RE = re.compile(r'[^a-z0-9]+')
_IDENTIFIER_QUERY_RE = re.compile(r'^\s*[0-9][0-9\s.\-/]*$')
_IDENTIFIER_GLOBAL_MIN_DIGITS = 7


def _plain_text(value):
    return '' if value is None else ' '.join(str(value).split())


# Helpers legados compartidos por los filtros avanzados y sus casos especiales.
def fold_filter_text(value):
    return _plain_text(value).translate(_ACCENT_TRANSLATION).lower()


def folded_sql(expr):
    return f"LOWER(TRANSLATE(BTRIM(COALESCE(({expr})::text, '')), '{_ACCENTED_CHARS}', '{_UNACCENTED_CHARS}'))"


def filter_tokens(value):
    tokens = [token for token in re.split(r'[^a-z0-9]+', fold_filter_text(value)) if token]
    return list(dict.fromkeys(tokens))


def build_legacy_text_search_clause(expr, value):
    tokens = filter_tokens(value)
    if not tokens:
        return '', []

    sql_expr = folded_sql(expr)
    return ' AND '.join([f"{sql_expr} LIKE %s" for _ in tokens]), [f'%{token}%' for token in tokens]


# Normalizacion comun del buscador rapido.
def normalize_text(value):
    sql_compatible = _SQL_COMPAT_INPUT_RE.sub(' ', _plain_text(value))
    normalized = unidecode(sql_compatible).casefold()
    return ' '.join(_TEXT_SEPARATOR_RE.sub(' ', normalized).split())


def text_tokens(value):
    return list(dict.fromkeys(token for token in normalize_text(value).split(' ') if token))


def normalize_digits(value):
    return _DIGITS_RE.sub('', _plain_text(value))


def normalize_alnum(value):
    sql_compatible = _SQL_COMPAT_INPUT_RE.sub('', _plain_text(value))
    return _ALNUM_RE.sub('', unidecode(sql_compatible).casefold())


def normalized_sql(expr, field_type):
    raw_expr = f"COALESCE(({expr})::text, '')"

    if field_type == IDENTIFIER_DIGITS:
        return f"REGEXP_REPLACE({raw_expr}, '[^0-9]+', '', 'g')"

    folded_expr = f"TRANSLATE(LOWER({raw_expr}), 'áéíóúüñ', 'aeiouun')"
    if field_type == IDENTIFIER_ALNUM:
        return f"REGEXP_REPLACE({folded_expr}, '[^a-z0-9]+', '', 'g')"

    return (
        "REGEXP_REPLACE("
        f"BTRIM(REGEXP_REPLACE({folded_expr}, '[^a-z0-9]+', ' ', 'g')), "
        "'[[:space:]]+', ' ', 'g')"
    )


def build_field_search_clause(expr, value, field_type):
    sql_expr = normalized_sql(expr, field_type)

    if field_type == IDENTIFIER_DIGITS:
        normalized_value = normalize_digits(value)
        return (f"{sql_expr} LIKE %s", [f'%{normalized_value}%']) if normalized_value else ('', [])

    if field_type == IDENTIFIER_ALNUM:
        normalized_value = normalize_alnum(value)
        return (f"{sql_expr} LIKE %s", [f'%{normalized_value}%']) if normalized_value else ('', [])

    tokens = text_tokens(value)
    if not tokens:
        return '', []
    return ' AND '.join([f"{sql_expr} LIKE %s" for _ in tokens]), [f'%{token}%' for token in tokens]


def build_contains_search_clause(expr, value, field_type, quick_search_value=''):
    if quick_search_value and normalize_text(value) == normalize_text(quick_search_value):
        return build_field_search_clause(expr, value, field_type)
    return build_legacy_text_search_clause(expr, value)


def build_global_search_clause(field_sql, field_types, value):
    normalized_value = normalize_digits(value)
    if (
        _IDENTIFIER_QUERY_RE.fullmatch(str(value or ''))
        and len(normalized_value) >= _IDENTIFIER_GLOBAL_MIN_DIGITS
    ):
        clauses = [
            f"{normalized_sql(field_sql[field], field_type)} LIKE %s"
            for field, field_type in field_types.items()
            if field_type in {IDENTIFIER_DIGITS, IDENTIFIER_ALNUM} and field in field_sql
        ]
        if not clauses:
            return '', []
        return f"({' OR '.join(clauses)})", [f'%{normalized_value}%'] * len(clauses)

    token_groups = []
    params = []
    for token in text_tokens(value):
        token_clauses = []
        token_params = []
        for field, field_type in field_types.items():
            expr = field_sql.get(field)
            if not expr:
                continue
            if field_type == IDENTIFIER_DIGITS and not token.isdigit():
                continue

            normalized_token = (
                normalize_digits(token)
                if field_type == IDENTIFIER_DIGITS
                else normalize_alnum(token)
                if field_type == IDENTIFIER_ALNUM
                else token
            )
            if not normalized_token:
                continue
            token_clauses.append(f"{normalized_sql(expr, field_type)} LIKE %s")
            token_params.append(f'%{normalized_token}%')

        if token_clauses:
            token_groups.append(f"({' OR '.join(token_clauses)})")
            params.extend(token_params)

    if not token_groups:
        return '', []
    return f"({' AND '.join(token_groups)})", params
