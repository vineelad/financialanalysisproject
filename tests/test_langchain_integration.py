import json
import unittest
from uuid import uuid4

import httpx
from langchain_core.embeddings import Embeddings

from ir_assistant.documents import from_document, to_document
from ir_assistant.models import Chunk


def fixture_chunk():
    return Chunk(chunk_id="source-row", document_id="fixture", bank="BAC", strategy="fixed",
                 text="Consumer revenue evidence", location="Table 1 row 2", url="https://example.com/results",
                 periods=["2025Q2", "2024Q2"], evidence_ids=["fixture:t1:r2"], token_count=4)


class LangChainIntegrationTests(unittest.TestCase):
    def test_document_roundtrip_preserves_financial_provenance(self):
        chunk = fixture_chunk()
        document = to_document(chunk, score=0.5)
        self.assertEqual(document.id, chunk.chunk_id)
        self.assertEqual(from_document(document), chunk)

    def test_chroma_adapter_preserves_ids_and_metadata_without_model_download(self):
        import chromadb
        from chromadb.config import Settings
        from langchain_chroma import Chroma

        class FixtureEmbeddings(Embeddings):
            def embed_documents(self, texts):
                return [[1.0, 0.0, 0.0] for _ in texts]

            def embed_query(self, text):
                return [1.0, 0.0, 0.0]

        store = Chroma(client=chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False)),
                       collection_name="test-" + uuid4().hex, embedding_function=FixtureEmbeddings())
        chunk = fixture_chunk()
        store.add_documents([to_document(chunk)], ids=[chunk.chunk_id])
        result = store.as_retriever(search_kwargs={"k": 1, "filter": {"bank": "BAC"}}).invoke("consumer revenue")
        self.assertEqual(result[0].id, chunk.chunk_id)
        self.assertEqual(from_document(result[0]), chunk)

    def model(self, content, requests):
        from langchain_openai import ChatOpenAI

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={"id": "fixture-response", "object": "chat.completion",
                "created": 0, "model": "fixture-model", "choices": [{"index": 0, "finish_reason": "stop",
                "message": {"role": "assistant", "content": content}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}})

        return ChatOpenAI(model="fixture-model", api_key="test-placeholder", base_url="https://provider.invalid/v1",
                          http_client=httpx.Client(transport=httpx.MockTransport(respond)), max_retries=0)

    def test_prompt_model_parser_chain_with_mocked_provider(self):
        from ir_assistant.generation import generate_answer
        content = json.dumps({"status": "answered", "claims": [{"text": "Supported observation.",
                              "citations": ["source-row"]}], "limitations": []})
        requests = []
        result, usage = generate_answer("consumer revenue?", [{"chunk_id": "source-row", "text": "evidence"}], [],
                                       model=self.model(content, requests))
        self.assertEqual(result.claims[0].citations, ["source-row"])
        self.assertEqual(usage["total_tokens"], 15)
        self.assertEqual(str(requests[0].url), "https://provider.invalid/v1/chat/completions")
        payload = json.loads(requests[0].content)
        self.assertIn("source-row", payload["messages"][1]["content"])
        self.assertIn("claims", payload["messages"][0]["content"])

    def test_bad_json_is_rejected_without_echoing_provider_content(self):
        from ir_assistant.generation import generate_answer
        requests = []
        with self.assertRaises(RuntimeError) as error:
            generate_answer("question", [], [], model=self.model("invalid confidential provider content", requests))
        self.assertNotIn("confidential", str(error.exception))

    def test_workflow_still_rejects_citations_outside_retrieved_evidence(self):
        from unittest.mock import patch
        from ir_assistant.models import GeneratedAnswer, Hit
        from ir_assistant.workflow import Application
        application = object.__new__(Application)
        application.generate = True
        generated = GeneratedAnswer.model_validate({"status": "answered", "claims": [
            {"text": "Unsupported", "citations": ["unknown-id"]}]})
        with patch("ir_assistant.workflow.generate_answer", return_value=(generated, {})):
            with self.assertRaisesRegex(ValueError, "not retrieved"):
                application.answer({"question": "question", "hits": [Hit(chunk=fixture_chunk(), score=1)]})


if __name__ == "__main__":
    unittest.main()
