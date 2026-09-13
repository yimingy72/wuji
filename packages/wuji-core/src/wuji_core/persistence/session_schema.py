"""P08 Session publication, recovery, input and approval migration."""

from pathlib import Path
import re

from wuji_core.persistence.retained_result_schema import HEAD as PARENT_HEAD


HEAD = "vnext_0014_p08_session_approval"
_DRAFT = (
    Path(__file__).resolve().parents[1]
    / "execution"
    / "session_schema_draft.sql"
)
_DOLLAR_QUOTE = re.compile(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$")


def _split_sql(source: str):
    """Split the reviewed SQL resource without breaking function/DO bodies."""

    statements, current = [], []
    index = 0
    quote = None
    dollar_quote = None
    line_comment = False
    block_comment = False
    while index < len(source):
        if line_comment:
            current.append(source[index])
            if source[index] == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if source.startswith("*/", index):
                current.append("*/")
                block_comment = False
                index += 2
            else:
                current.append(source[index])
                index += 1
            continue
        if dollar_quote is not None:
            if source.startswith(dollar_quote, index):
                current.append(dollar_quote)
                index += len(dollar_quote)
                dollar_quote = None
            else:
                current.append(source[index])
                index += 1
            continue
        if quote is not None:
            current.append(source[index])
            if source[index] == quote:
                if index + 1 < len(source) and source[index + 1] == quote:
                    current.append(source[index + 1])
                    index += 2
                    continue
                quote = None
            index += 1
            continue
        if source.startswith("--", index):
            current.append("--")
            line_comment = True
            index += 2
            continue
        if source.startswith("/*", index):
            current.append("/*")
            block_comment = True
            index += 2
            continue
        if source[index] in {"'", '"'}:
            quote = source[index]
            current.append(source[index])
            index += 1
            continue
        if source[index] == "$":
            match = _DOLLAR_QUOTE.match(source, index)
            if match is not None:
                dollar_quote = match.group(0)
                current.append(dollar_quote)
                index = match.end()
                continue
        if source[index] == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            index += 1
            continue
        current.append(source[index])
        index += 1
    if quote is not None or dollar_quote is not None or block_comment:
        raise ValueError("unterminated P08 migration SQL")
    statement = "".join(current).strip()
    if statement:
        statements.append(statement)
    return tuple(statements)


def statements():
    return _split_sql(_DRAFT.read_text(encoding="utf-8"))


def upgrade(connection, application_role):
    if PARENT_HEAD != "vnext_0013_receiver_results":
        raise ValueError("P08 migration parent changed")
    connection.execute(
        "SELECT set_config('wuji.p08_application_role',%s,true)",
        (application_role,),
    ).fetchone()
    for statement in statements():
        connection.execute(statement)
    connection.execute(
        "INSERT INTO vnext.schema_migration(head) VALUES(%s)",
        (HEAD,),
    )
