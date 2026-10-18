"""Local analyst interface. Run: python -m streamlit run app.py"""
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import streamlit as st

from ir_assistant.generation import provider_config
from ir_assistant.models import Answer
from ir_assistant.settings import DATA
from ir_assistant.banks import bank_name, bank_registry


@st.cache_resource(show_spinner=False)
def application(strategy: str, rerank: bool, generate: bool, index_stamp: int, backend_stamp: tuple):
    from ir_assistant.workflow import Application
    return Application(strategy=strategy, rerank=rerank, generate=generate)


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def answer_display(answer: Answer):
    """Separate internal source footers and turn citation IDs into source links."""
    lookup = {hit.chunk.chunk_id: hit.chunk for hit in answer.hits}
    paragraphs = [p for p in answer.text.split("\n\n")
                  if not any(p.startswith(f"[{cid}] ") and chunk.url in p for cid, chunk in lookup.items())]
    body = "\n\n".join(paragraphs)
    cited = list(dict.fromkeys(cid for cid in re.findall(r"\[([^\]]+)\]", body) if cid in lookup))
    sources = [lookup[cid] for cid in cited] if cited else [h.chunk for h in answer.hits]
    numbers = {chunk.chunk_id: i for i, chunk in enumerate(sources, 1)}

    def citation(match):
        cid = match.group(1)
        if cid not in numbers:
            return match.group(0)
        url = lookup[cid].url
        return f"[{numbers[cid]}](<{url}>)" if urlsplit(url).scheme in {"http", "https"} else f"[{numbers[cid]}]"

    body = re.sub(r"\[([^\]]+)\]", citation, body)
    # Streamlit treats dollar signs as math delimiters; preserve currency text.
    return re.sub(r"(?<!\\)\$(?=\d)", r"\\$", body), sources


def source_summary(chunk, title: str) -> str:
    if "\nRow " in chunk.text:
        row = chunk.text.rsplit("\nRow ", 1)[1]
        label = row.split("|", 1)[0].split("=", 1)[-1].strip()
        label = re.sub(r"\s*\([a-z]\)\s*$", "", label, flags=re.I)
        label = " ".join(label.split())
        if label:
            return f"{title} — {label[:100]}"
    return f"{title} — supporting earnings disclosure."


def render_answer(record: dict, manifest: list):
    answer = Answer.model_validate(record["answer"])
    body, sources = answer_display(answer)
    st.subheader("Answer" if answer.status != "evidence_only" else "Source search")
    st.caption(record["question"])
    if record.get("base_bank"):
        st.caption("Comparison base: " + bank_name(record["base_bank"]))
        compared = record.get("trace", {}).get("scope", {}).get("banks", [])
        if len(compared) > 1:
            st.caption("Peers: " + ", ".join(bank_name(bank) for bank in compared if bank != record["base_bank"]))
    if answer.status == "evidence_only":
        st.info("Only supporting sources are available for this result. If the answer service is configured, ask again to receive an answer.")
    elif answer.status == "clarification":
        st.warning(body)
    elif answer.status == "insufficient_evidence":
        st.warning(body)
    elif answer.mode == "validated_calculation" and record["trace"].get("calculations"):
        rows = []
        for calculation in record["trace"]["calculations"]:
            row = {"Bank": bank_name(calculation["bank"])}
            components = calculation.get("components", {})
            if components:
                row.update({"Revenue growth": f"{components['revenue_growth']}%",
                            "Expense growth": f"{components['expense_growth']}%",
                            "Operating leverage": f"{calculation['value']} pp"})
            else:
                metric = calculation["inputs"][0]["metric"].replace("_", " ")
                row.update({"Measure": f"Consumer {metric} growth", "Growth": f"{calculation['value']}%"})
            rows.append(row)
        st.dataframe(rows, hide_index=True, use_container_width=True)
        if any(c.get("components") for c in record["trace"]["calculations"]):
            st.caption("Operating leverage = year-over-year revenue growth minus expense growth, in percentage points (pp).")
        for paragraph in body.split("\n\n"):
            if paragraph.startswith("Under this formula"):
                st.markdown(paragraph)
        st.caption("Segment names alone do not establish comparable business scope; preserve each bank's reporting basis when comparing results.")
        if any(c["bank"] == "COF" for c in record["trace"]["calculations"]):
            st.caption("Capital One growth covers Consumer Banking, with Credit Card reported separately; acquisition effects are not removed.")
    else:
        st.markdown(body)
    titles = {item["document_id"]: item["title"] for item in manifest}
    if sources:
        st.markdown("**Supporting sources**")
        for index, chunk in enumerate(sources, 1):
            title = titles.get(chunk.document_id, bank_name(chunk.bank))
            summary = source_summary(chunk, title)
            link = f"[View source](<{chunk.url}>)" if urlsplit(chunk.url).scheme in {"http", "https"} else ""
            st.markdown(f"{index}. {summary} {link}")
    if answer.status != "evidence_only":
        base_context = f"Comparison base: {bank_name(record['base_bank'])}\n\n" if record.get("base_bank") else ""
        export = f"# {record['question']}\n\n{base_context}{body}\n"
        st.download_button("Download answer", data=export, file_name="ir-answer.md", mime="text/markdown")


def main():
    st.set_page_config(page_title="IR Research Desk", page_icon="📊", layout="wide")
    st.caption("INVESTOR RELATIONS / DOCUMENT INTELLIGENCE")
    st.title("IR Research Desk")
    st.write("Explore bank performance with evidence you can inspect.")
    manifest = load_json(DATA / "processed" / "source_manifest.json", [])
    banks = sorted({item["bank"] for item in manifest})
    periods = sorted({period for item in manifest for period in item["periods"]}, reverse=True)
    bank_names = {bank: item["name"] for bank, item in bank_registry().items()}
    st.caption(f"Available research: {', '.join(bank_names.get(b, b) for b in banks) or 'no documents loaded'} · "
               + ', '.join(f"Q{p[-1]} {p[:4]}" for p in periods))

    ready = all(provider_config())
    strategy, rerank, generate = "semantic", True, ready
    if not ready:
        st.warning("The answer service is not configured. Only supporting source links are available.")

    st.subheader("Ask a question")
    st.caption("Comparison questions include all available peers by default. Name a peer to narrow the comparison.")
    st.session_state.setdefault("question", "")
    index_path = DATA / "processed" / f"index-{strategy}.json"
    index_ready = index_path.exists() and (DATA / "processed" / f"chunks-{strategy}.jsonl").exists()
    if not index_ready:
        st.warning("The selected index is missing. Run prepare, then index --strategy both from the terminal.")
    with st.form("research_question"):
        base_bank = st.selectbox("Base bank", options=banks or list(bank_names), index=None,
                                 format_func=lambda bank: bank_names.get(bank, bank),
                                 placeholder="Select a base bank", key="base_bank",
                                 help="Peer percentage comparisons use this bank as the denominator. Single-bank lookups stay focused on the requested bank.")
        question = st.text_area("Your question", key="question", height=100,
                                placeholder="Ask about a financial measure and reporting period.")
        submitted = st.form_submit_button("Ask" if generate else "Search sources", disabled=not index_ready)
    if submitted:
        if base_bank is None:
            st.warning("Select a base bank before asking a question.")
        elif not question.strip():
            st.warning("Enter a question before searching.")
        else:
            try:
                with st.spinner("Retrieving and checking the documents…"):
                    backend_files = (Path(__file__).resolve().parent / "ir_assistant").glob("*.py")
                    backend_stamp = tuple((p.name, p.stat().st_mtime_ns) for p in sorted(backend_files))
                    engine = application(strategy, rerank, generate, index_path.stat().st_mtime_ns, backend_stamp)
                    answer, trace = engine.ask(question.strip(), base_bank=base_bank)
                st.session_state["latest_result"] = {
                    "question": question.strip(), "answer": answer.model_dump(), "trace": trace,
                    "base_bank": base_bank,
                    "configuration": f"{strategy}{' + reranking' if rerank else ''}",
                }
            except Exception:
                # Never expose provider error bodies, credentials or raw stacks.
                st.error("The request could not be completed. Check the local index, model downloads, and provider configuration, then retry.")
                st.session_state.pop("latest_result", None)
    if "latest_result" in st.session_state:
        st.divider()
        render_answer(st.session_state["latest_result"], manifest)
    else:
        st.info("Ask about a bank and reporting period. Your answer and source links will appear here.")

if __name__ == "__main__":
    main()
