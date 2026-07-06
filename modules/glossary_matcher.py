"""
glossary_matcher.py — "BuscarV" de una tabla BigQuery nueva contra el glosario de negocio
central (repo dataplex-sara, fuente de verdad).

Para cada columna busca un término existente por nombre de columna, sinónimo o nombre de término
(match exacto o difuso). Si no lo encuentra, la deja en '-' para que un humano la complete y así
retroalimentar el glosario (vía MR / validación).
"""
from __future__ import annotations

import difflib
import os
import re
from pathlib import Path

import yaml

DOMAIN_GLOSSARY = {
    "comm": "DIA – Comercial",
    "ops": "DIA – Operaciones",
    "sc": "DIA – Supply Chain",
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def governance_repo() -> Path:
    """Ruta al repo de gobierno (dataplex-sara). Env GOVERNANCE_REPO_PATH o hermano en Desktop."""
    p = os.getenv("GOVERNANCE_REPO_PATH")
    if p:
        return Path(p)
    return Path(__file__).resolve().parents[2] / "dataplex-sara"


def build_index(repo: str | Path | None = None) -> tuple[dict, list]:
    """Devuelve (index, terms). index: norm_key → info de término (primer match gana)."""
    repo = Path(repo) if repo else governance_repo()
    domains = repo / "glossary" / "domains"
    index: dict[str, dict] = {}
    terms: list[dict] = []
    if not domains.exists():
        return index, terms
    for f in sorted(domains.rglob("*.yaml")):
        if f.name.startswith("_"):
            continue
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for t in data.get("terms") or []:
            tid = t.get("id", "")
            info = {
                "term": t.get("name", tid),
                "term_id": tid,
                "definition": " ".join((t.get("definition") or "").split()),
                "domain": t.get("domain", data.get("glossary", "")),
                "category": t.get("category", data.get("category", "")),
                "glossary": DOMAIN_GLOSSARY.get(tid.split(".")[0], t.get("domain", "")),
            }
            terms.append(info)
            keys = {_norm(t.get("name", "")), _norm(tid.split(".")[-1])}
            keys.update(_norm(c) for c in (t.get("related_columns") or []))
            keys.update(_norm(s) for s in (t.get("synonyms") or []))
            for k in keys:
                if k and k not in index:
                    index[k] = info

    # Efecto red: añade los mapeos explícitos columna→término de otras tablas ya onboardadas.
    info_by_id = {t["term_id"]: t for t in terms}
    links_dir = repo / "glossary" / "column_links"
    if links_dir.exists():
        for f in sorted(links_dir.glob("*.yaml")):
            if f.name.startswith("_"):
                continue
            m = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            for col, tid in (m.get("exact") or {}).items():
                info = info_by_id.get(tid)
                if info and _norm(col) not in index:
                    index[_norm(col)] = info
    return index, terms


def read_bq_columns(project: str, dataset: str, table: str) -> list[dict]:
    from google.cloud import bigquery
    client = bigquery.Client(project=project)
    tbl = client.get_table(f"{project}.{dataset}.{table}")
    return [{"name": f.name, "type": f.field_type} for f in tbl.schema]


def match_columns(columns: list[dict], index: dict) -> list[dict]:
    """Para cada columna: match exacto → aproximado → sin match ('-')."""
    all_keys = list(index.keys())
    out = []
    for col in columns:
        name = col["name"]
        k = _norm(name)
        row = {
            "column": name, "type": col.get("type", ""),
            "term": "-", "term_id": "", "definition": "-",
            "glossary": "-", "category": "-", "domain": "-",
            "confidence": "sin match", "match_source": "",
        }
        info = None
        if k in index:
            info = index[k]
            row["confidence"] = "exacta"
            row["match_source"] = "columna/sinónimo"
        else:
            close = difflib.get_close_matches(k, all_keys, n=1, cutoff=0.86)
            if close:
                info = index[close[0]]
                row["confidence"] = "aproximada"
                row["match_source"] = f"~ {close[0]}"
        if info:
            row.update(term=info["term"], term_id=info["term_id"], definition=info["definition"],
                       glossary=info["glossary"], category=info["category"], domain=info["domain"])
        out.append(row)
    return out


def scan_table(project: str, dataset: str, table: str) -> dict:
    """Punto de entrada: lee esquema + hace el buscarV. Devuelve resumen + filas."""
    index, terms = build_index()
    columns = read_bq_columns(project, dataset, table)
    rows = match_columns(columns, index)
    n = len(rows)
    matched = sum(1 for r in rows if r["confidence"] != "sin match")
    return {
        "asset": f"{project}.{dataset}.{table}",
        "total": n, "matched": matched, "pending": n - matched,
        "coverage": round(100 * matched / n, 1) if n else 0,
        "glossary_terms": len(terms),
        "rows": rows,
    }


def existing_taxonomy(terms: list) -> dict:
    """{domain: [categorías]} de la taxonomía actual, para que la IA mapee a lo que ya existe."""
    tax: dict[str, set] = {}
    for t in terms:
        if t.get("domain"):
            tax.setdefault(t["domain"], set()).add(t.get("category", ""))
    return {d: sorted(c for c in cs if c) for d, cs in tax.items()}


def suggest_term(column: str, dtype: str, asset: str, user_name: str = "") -> dict:
    """Pide a Gemini (Vertex) un término de negocio COMPLETO para una columna nueva, mapeando a la
    taxonomía existente. Devuelve {name, definition, overview, domain, category, synonyms}.
    Requiere VERTEX_PROJECT / VERTEX_LOCATION (o usa el proyecto del activo)."""
    import json
    import os
    from google import genai

    index, terms = build_index()
    tax = existing_taxonomy(terms)
    project = os.getenv("VERTEX_PROJECT") or asset.split(".")[0]
    location = os.getenv("VERTEX_LOCATION", "us-central1")
    model = os.getenv("VERTEX_MODEL", "gemini-2.5-flash")

    prompt = f"""Eres un Data Steward de DIA definiendo un término de glosario de negocio.
Columna técnica: `{column}` (tipo {dtype}) de la tabla `{asset}`.
{"Nombre propuesto por el usuario: " + user_name if user_name else ""}

Taxonomía EXISTENTE (elige domain y category de esta lista; no inventes nuevos si encaja uno):
{json.dumps(tax, ensure_ascii=False, indent=2)}

Devuelve SOLO un JSON con:
{{
  "name": "Nombre de negocio del atributo (ES, estilo 'Nombre de X'/'Código de X'/'Indicador de X')",
  "definition": "Descripción SENCILLA del campo (1 frase, la que rellena el metadatado)",
  "overview": "Descripción DETALLADA (contexto, uso, matices)",
  "domain": "uno de los domains de la taxonomía",
  "category": "una category del domain elegido",
  "synonyms": ["sinónimos y el nombre técnico de la columna"]
}}
Responde SOLO el JSON válido, en español."""

    client = genai.Client(vertexai=True, project=project, location=location)
    resp = client.models.generate_content(model=model, contents=prompt)
    txt = (resp.text or "").replace("```json", "").replace("```", "").strip()
    data = json.loads(txt)
    # normaliza
    return {
        "name": data.get("name") or user_name or column,
        "definition": data.get("definition", ""),
        "overview": data.get("overview", ""),
        "domain": data.get("domain", ""),
        "category": data.get("category", ""),
        "synonyms": data.get("synonyms", []),
    }


def build_proposal(asset: str, rows: list[dict]) -> dict:
    """Genera los YAML de propuesta a partir de las filas revisadas por el usuario.

    Cada fila puede traer: term_id (término existente), o new_term/new_definition/new_category/
    new_domain (término nuevo), o nada (pendiente → se deja como TODO en un borrador).
    """
    table = asset.split(".")[-1]
    links, new_terms, pending = [], [], []
    for r in rows:
        col = r["column"]
        if r.get("term_id"):
            links.append((col, r["term_id"]))
        elif r.get("new_term"):
            tid = f"new.{table}.{_norm(r['new_term']) or _norm(col)}"
            syn = r.get("new_synonyms") or []
            if isinstance(syn, str):
                syn = [s.strip() for s in syn.split(",") if s.strip()]
            new_terms.append({
                "id": tid, "name": r["new_term"],
                "definition": r.get("new_definition") or "-",
                "overview": r.get("new_overview") or "",
                "domain": r.get("new_domain") or "-",
                "category": r.get("new_category") or "-",
                "synonyms": syn,
                "column": col,
            })
            links.append((col, tid))
        else:
            pending.append(col)

    links_yaml = (
        f"# Propuesta de column_links para {asset}  (generada por el frontal)\n"
        f"asset: {asset}\nlink_type: definition\nexact:\n"
        + "".join(f"  {c}: {tid}\n" for c, tid in links)
        + (f"# Pendientes (sin término, rellenar): {', '.join(pending)}\n" if pending else "")
    )

    terms_yaml = ""
    if new_terms:
        terms_yaml = "# Términos NUEVOS propuestos (status DRAFT — validar antes de publicar)\nterms:\n"
        for t in new_terms:
            terms_yaml += (
                f"  - id: {t['id']}\n    name: \"{t['name']}\"\n"
                f"    definition: \"{t['definition']}\"\n"
            )
            if t.get("overview"):
                terms_yaml += f"    overview: \"{t['overview']}\"\n"
            terms_yaml += (
                f"    domain: {t['domain']}\n    category: {t['category']}\n    status: DRAFT\n"
            )
            if t.get("synonyms"):
                terms_yaml += f"    synonyms: [{', '.join(t['synonyms'])}]\n"
            terms_yaml += f"    related_columns: [{t['column']}]\n"

    return {
        "links_count": len(links), "new_terms_count": len(new_terms), "pending_count": len(pending),
        "links_yaml": links_yaml, "terms_yaml": terms_yaml,
    }


def write_proposal(asset: str, proposal: dict) -> str:
    """Escribe la propuesta en dataplex-sara/proposals/<table>/ (borrador para MR)."""
    table = asset.split(".")[-1]
    dest = governance_repo() / "proposals" / table
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{table}.column_links.yaml").write_text(proposal["links_yaml"], encoding="utf-8")
    if proposal.get("terms_yaml"):
        (dest / f"{table}.new_terms.yaml").write_text(proposal["terms_yaml"], encoding="utf-8")
    return str(dest)
