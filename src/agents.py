# src/agents.py
from typing import Dict, Any
from src.state import GraphState
from src.guardrails.schemas import FinalReport
from src.guardrails.moderation import check_toxicity
from src.guardrails.pii import redact_pii
from src.tools.search import SearchTool
from src.tools.groq_client import GroqClient
from src.observability import log_trace
import os
import datetime
import json
import re
from dotenv import load_dotenv
from src.pdf_generator import generate_pdf_report

load_dotenv()  # Load environment variables from .env file

# Initialize tools once
search_tool = SearchTool()
groq = GroqClient(api_key=os.environ.get("GROQ_API_KEY"))

DEFAULT_MODEL = os.environ.get("DEFAULT_GROQ_MODEL", "llama-3.3-70b-versatile")

# -------------------------------
# Researcher Agent
# -------------------------------
class ResearcherAgent:
    name = "Researcher"

    def run(self, state: GraphState) -> GraphState:
        q = state["query"]
        try:
            # Get more search results (increased from 5 to 10)
            results = search_tool.web_search(q, top_k=10)
            enhanced_results = []

            # Fetch full page content for each result
            for result in results:
                url = result["url"]
                full_text = search_tool.fetch_full_page(url)

                enhanced_result = result.copy()
                enhanced_result["full_text"] = full_text

                # Combine snippet and full text for richer context
                combined_content = result["snippet"]
                if full_text:
                    combined_content += " " + full_text

                enhanced_result["combined_content"] = combined_content
                enhanced_results.append(enhanced_result)

            state["docs"] = enhanced_results

            # Use combined content for context (richer than just snippets)
            state["context"].extend([r["combined_content"] for r in enhanced_results])

            state["tools_used"].append("web_search")
            state["tools_used"].append("full_page_fetch")
            log_trace("researcher.web_search", {"count": len(results), "with_full_text": len([r for r in enhanced_results if r["full_text"]])})
        except Exception as e:
            state["violations"].append(f"researcher_failed: {str(e)}")
            state["tool_error"] = True
            state["failure_count"] += 1
        return state


# -------------------------------
# Analyst Agent
# -------------------------------
class AnalystAgent:
    name = "Analyst"

    def run(self, state: GraphState) -> GraphState:
        facts = []
        for d in state.get("docs", []):
            # Use combined_content if available (includes full page text), otherwise fall back to snippet
            content = d.get("combined_content") or d.get("snippet", "")

            # Clean up the content - remove excessive whitespace and limit length
            content = " ".join(content.split())  # Normalize whitespace
            if len(content) > 500:  # Limit content length for processing
                content = content[:500] + "..."

            facts.append({
                "source": d.get("title") or d.get("url", ""),
                "url": d.get("url", ""),
                "excerpt": d.get("snippet", ""),
                "content": content
            })

        # Sort facts by relevance (prioritize those with full content)
        facts.sort(key=lambda x: len(x["content"]), reverse=True)

        state["outputs"]["facts"] = facts
        state["tools_used"].append("analyst_web_parser")
        log_trace("analyst.facts_extracted", {"n_facts": len(facts), "avg_content_length": sum(len(f["content"]) for f in facts) / len(facts) if facts else 0})
        return state


# -------------------------------
# Writer Agent
# -------------------------------
# class WriterAgent:
#     name = "Writer"

#     def __init__(self, groq_client: GroqClient = None):
#         self.groq = groq_client or groq
#         self.model_dev = os.environ.get("DEV_GROQ_MODEL", DEFAULT_MODEL)
#         self.model_prod = os.environ.get("PROD_GROQ_MODEL", DEFAULT_MODEL)

#     def run(self, state: GraphState) -> GraphState:
#         facts = state["outputs"].get("facts", [])[:3]  # limit to 3 facts for brevity

#         messages = [
#             {"role": "system", "content": (
#                 "You are a research-writer. Output ONLY valid JSON. "
#                 "No markdown, no text outside JSON. "
#                 "Schema: {title, summary, key_findings:[], facts:[], generated_at}"
#             )},
#             {"role": "user", "content": f"Facts: {facts}"}
#         ]

#         try:
#             text = self.groq.chat(
#                 messages=messages,
#                 model=self.model_dev,
#                 max_tokens=400,
#                 temperature=0.0,
#                 use_cache=True
#             )
#             text = redact_pii(text)

#             # --- FIX: extract JSON block from output ---
#             match = re.search(r"\{.*\}", text, re.S)
#             if not match:
#                 raise ValueError("No JSON object in LLM output")
#             json_str = match.group(0)

#             parsed = json.loads(json_str)
#             if "generated_at" not in parsed:
#                 parsed["generated_at"] = datetime.datetime.utcnow().isoformat()

#             state["outputs"]["report_raw"] = parsed
#             state["tools_used"].append("groq_writer")
#             log_trace("writer.groq_call", {"model": self.model_dev})

#         except Exception as e:
#             state["violations"].append("writer_json_parse_failure")
#             state["failure_count"] += 1
#             state["tool_error"] = True
#             log_trace("writer.error", {"error": str(e)})
#         return state

class WriterAgent:
    name = "Writer"

    def __init__(self, groq_client=None):
        from src.tools.groq_client import GroqClient
        self.groq = groq_client or GroqClient()
        self.model_dev = os.environ.get("DEV_GROQ_MODEL", "llama-3.3-70b-versatile")

    def run(self, state: GraphState) -> GraphState:
        facts = state["outputs"].get("facts", [])[:5]  # increased to 5 facts for better content

        messages = [
            {"role": "system", "content": (
                "You are an expert market research writer. Create comprehensive, well-structured reports. "
                "Return ONLY valid JSON with complete, detailed content. No truncation or incomplete sentences. "
                "Schema: {title: string, summary: detailed paragraph (150-200 words), key_findings: [3-5 detailed bullet points], facts: array of objects with {source, url, excerpt, content}, generated_at: ISO datetime}"
            )},
            {"role": "user", "content": (
                f"Create a comprehensive market research report based on these facts about: '{state['query']}'\n\n"
                f"AVAILABLE FACTS:\n" + "\n".join([
                    f"{i+1}. Source: {fact.get('source', 'Unknown')}\n   URL: {fact.get('url', '')}\n   Excerpt: {fact.get('excerpt', '')}\n   Content: {fact.get('content', '')}"
                    for i, fact in enumerate(facts)
                ]) + "\n\n"
                f"REQUIREMENTS:\n"
                f"- Title: Catchy and relevant to the query\n"
                f"- Summary: 150-200 word comprehensive overview synthesizing the key insights\n"
                f"- Key Findings: 3-5 detailed, insightful bullet points highlighting the most important discoveries\n"
                f"- Facts: Select the 3-5 most relevant facts from the available facts above. Each fact must be a complete object with:\n"
                f"  * source: The original source name/title\n"
                f"  * url: The original URL\n"
                f"  * excerpt: A brief excerpt (2-3 sentences)\n"
                f"  * content: The full content from the source\n"
                f"- generated_at: Current timestamp in ISO format (e.g., '2024-01-15T10:30:00.000Z')\n"
                f"- Ensure all text is complete, professional, and directly relevant to the query\n"
                f"- IMPORTANT: Facts must be proper JSON objects, not just strings"
            )}
        ]

        try:
            text = self.groq.chat(
                messages=messages,
                model=self.model_dev,
                max_tokens=1200,  # Increased for more complete responses
                temperature=0.1,  # Slightly higher for better creativity while maintaining accuracy
                use_cache=True
            )

            # --- Extract JSON block ---
            match = re.search(r"\{.*\}", text, re.S)
            if not match:
                raise ValueError(f"No JSON object found in LLM output: {text[:200]}")
            json_str = match.group(0)

            parsed = json.loads(json_str)

            # Apply PII redaction to text fields only, not datetime
            if "summary" in parsed:
                parsed["summary"] = redact_pii(parsed["summary"])
            if "key_findings" in parsed:
                parsed["key_findings"] = [redact_pii(finding) for finding in parsed["key_findings"]]
            if "facts" in parsed:
                for fact in parsed["facts"]:
                    if "content" in fact:
                        fact["content"] = redact_pii(fact["content"])
                    if "excerpt" in fact:
                        fact["excerpt"] = redact_pii(fact["excerpt"])

            if "generated_at" not in parsed:
                parsed["generated_at"] = datetime.datetime.utcnow().isoformat()

            state["outputs"]["report_raw"] = parsed
            state["tools_used"].append("groq_writer")
            log_trace("writer.success", {"keys": list(parsed.keys())})

        except json.JSONDecodeError as e:
            state["violations"].append("writer_json_parse_failure")
            state["failure_count"] += 1
            state["tool_error"] = True
            log_trace("writer.error", {"error": str(e), "json_error": True})
        except Exception as e:
            state["violations"].append("writer_json_parse_failure")
            state["failure_count"] += 1
            state["tool_error"] = True
            log_trace("writer.error", {"error": str(e)})

        return state


# -------------------------------
# Narrative Writer Agent (for Article Mode)
# -------------------------------
class NarrativeWriterAgent:
    name = "NarrativeWriter"

    def __init__(self, groq_client=None):
        from src.tools.groq_client import GroqClient
        self.groq = groq_client or GroqClient()
        self.model_dev = os.environ.get("DEV_GROQ_MODEL", "llama-3.3-70b-versatile")

    def run(self, state: GraphState) -> GraphState:
        report = state["outputs"].get("report")
        if not report:
            state["violations"].append("no_structured_report")
            return state

        facts = report.get("facts", [])
        summary = report.get("summary", "")
        findings = report.get("key_findings", [])
        title = report.get("title", "")

        messages = [
            {"role": "system", "content": (
                "You are a professional business writer specializing in market research articles. "
                "Write complete, well-structured articles with no repetition or truncation. "
                "Ensure each section is fully developed and flows naturally into the next."
            )},
            {"role": "user", "content": (
                f"Write a comprehensive article about: '{state['query']}'\n\n"
                f"ARTICLE TITLE: {title}\n\n"
                f"CONTENT REQUIREMENTS:\n"
                f"• Introduction (150 words): Hook the reader and provide context\n"
                f"• Main Analysis (300 words): Analyze the key findings in detail\n"
                f"• Evidence & Examples (200 words): Support claims with specific facts\n"
                f"• Implications (150 words): Discuss business and economic implications\n"
                f"• Conclusion (100 words): Summarize key takeaways\n\n"
                f"SOURCE MATERIAL:\n"
                f"Summary: {summary}\n\n"
                f"Key Findings:\n" + "\n".join(f"• {finding}" for finding in findings) + "\n\n"
                f"Facts:\n" + "\n".join([
                    f"{i+1}. {fact.get('source', 'Source')}: {fact.get('content', '')}"
                    for i, fact in enumerate(facts[:3])  # Limit to top 3 facts
                ]) + "\n\n"
                f"INSTRUCTIONS:\n"
                f"• Write in a professional, objective tone\n"
                f"• Ensure smooth transitions between sections\n"
                f"• Avoid repetition of the same information\n"
                f"• Complete all sentences and paragraphs\n"
                f"• Use markdown formatting for readability\n"
                f"• Total length: approximately 800-1000 words"
            )}
        ]

        try:
            text = self.groq.chat(
                messages=messages,
                model=self.model_dev,
                max_tokens=2000,  # Increased for complete articles
                temperature=0.2,  # Lower temperature for more consistent output
                use_cache=True
            )

            # Clean up the response - remove any incomplete sections
            if text:
                # Remove any trailing incomplete sentences
                text = text.strip()
                if not text.endswith('.'):
                    # Find the last complete sentence
                    last_period = text.rfind('.')
                    if last_period > len(text) * 0.8:  # If period is in last 20% of text
                        text = text[:last_period + 1]

            # Apply PII redaction to the article
            text = redact_pii(text)

            state["outputs"]["article"] = text
            state["tools_used"].append("narrative_writer")
            log_trace("narrative_writer.success", {"word_count": len(text.split())})

        except Exception as e:
            state["violations"].append("narrative_writer_failed")
            state["failure_count"] += 1
            state["tool_error"] = True
            log_trace("narrative_writer.error", {"error": str(e)})

        return state


# -------------------------------
# Reviewer Agent
# -------------------------------
class ReviewerAgent:
    name = "Reviewer"

    def run(self, state: GraphState) -> GraphState:
        raw = state["outputs"].get("report_raw")
        if not raw:
            state["violations"].append("no_report")
            return state

        try:
            validated = FinalReport.parse_obj(raw)
            state["outputs"]["report"] = validated.dict()
            state["schema_ok"] = True
            state["tools_used"].append("pydantic_validation")
            log_trace("reviewer.schema_ok", {"title": validated.title})

            # Generate PDF report and save filename in state outputs
            pdf_filename = generate_pdf_report(validated.dict(), filename=f"report_{state['query'][:20].replace(' ', '_')}.pdf")
            state["outputs"]["pdf_report"] = pdf_filename
            state["tools_used"].append("pdf_generator")
            log_trace("reviewer.pdf_generated", {"filename": pdf_filename})

        except Exception as e:
            state["schema_ok"] = False
            state["violations"].append(f"schema_error: {str(e)}")
            log_trace("reviewer.schema_error", {"error": str(e)})

        summary = raw.get("summary", "")
        flagged, reason = check_toxicity(summary)
        if flagged:
            state["policy_violation"] = True
            state["violations"].append("policy_violation:" + reason)
            log_trace("reviewer.moderation_flag", {"reason": reason})
        return state
# -------------------------------