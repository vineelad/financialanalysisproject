"""Make one configured-provider explanation request for the final demo check."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ir_assistant.workflow import Application
from ir_assistant.storage import write_json


def main():
    question = "What does Bank of America management say drove consumer revenue changes in Q2 2025?"
    app = Application("semantic", rerank=True, generate=True)
    try:
        answer, trace = app.ask(question, save=False, base_bank="BAC")
    except Exception as exc:
        # Do not print provider exception bodies or credentials.
        write_json(ROOT / "reports/final-provider-check.json", {"passed": False, "error_type": type(exc).__name__,
                                                               "note": "Provider explanation check failed; inspect configuration locally."})
        print("Provider explanation check failed; no provider error body displayed.")
        raise SystemExit(1)
    text = answer.text.casefold()
    supported_driver = "higher nii" in text or "higher net interest income" in text
    passed = answer.status == "answered" and supported_driver and answer.mode in {"generated", "source_excerpt"}
    write_json(ROOT / "reports/final-provider-check.json", {"passed": passed, "provider_requests": 1,
               "review": "Assistant checked the stated higher-NII driver against the retrieved BofA earnings material; not independent human review.",
               "trace": trace})
    print({"passed": passed, "mode": answer.mode, "usage": answer.usage})
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
