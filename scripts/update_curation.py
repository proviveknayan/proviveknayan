#!/usr/bin/env python3
"""
Daily Curation Script:
- Fetches recent influential preprints across AI, LLMs, and System Architecture from arXiv API.
- Generates a structured TIL (Today I Learned) log under data/til/YYYY-MM-DD.md.
- Injects the latest snapshot into README.md between delimiter tags.
"""

import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README_PATH = REPO_ROOT / "README.md"
TIL_DIR = REPO_ROOT / "data" / "til"

# Relevant arXiv categories across Vivek's domains:
# cs.AI (Artificial Intelligence), cs.LG (Machine Learning), cs.SE (Software Engineering), stat.ML (Machine Learning Statistics)
ARXIV_QUERY = "cat:cs.AI OR cat:cs.LG OR cat:cs.SE"
MAX_PAPERS = 3

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def fetch_arxiv_preprints():
    params = {
        "search_query": ARXIV_QUERY,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": str(MAX_PAPERS),
    }
    url = f"http://export.arxiv.org/api/query?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "PolymathCurator/1.0 (proviveknayan)"})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
    except Exception as e:
        print(f"Error querying arXiv: {e}")
        return []

    root = ET.fromstring(data)
    papers = []
    for entry in root.findall("atom:entry", ATOM_NS):
        title = entry.find("atom:title", ATOM_NS)
        summary = entry.find("atom:summary", ATOM_NS)
        id_tag = entry.find("atom:id", ATOM_NS)
        published = entry.find("atom:published", ATOM_NS)

        authors = []
        for author in entry.findall("atom:author", ATOM_NS):
            name = author.find("atom:name", ATOM_NS)
            if name is not None and name.text:
                authors.append(name.text.strip())

        paper_title = re.sub(r"\s+", " ", title.text).strip() if title is not None and title.text else "Untitled"
        paper_summary = re.sub(r"\s+", " ", summary.text).strip() if summary is not None and summary.text else ""
        if len(paper_summary) > 280:
            paper_summary = paper_summary[:277] + "..."

        paper_url = id_tag.text.strip() if id_tag is not None and id_tag.text else ""
        pub_date = published.text.strip()[:10] if published is not None and published.text else ""

        papers.append({
            "title": paper_title,
            "url": paper_url,
            "summary": paper_summary,
            "authors": ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else ""),
            "date": pub_date,
        })

    return papers


def build_markdown_section(today_str, papers):
    lines = [
        "<!-- START_DAILY_TIL -->",
        "## 🔬 Daily TIL (Curated arXiv & Engineering Pulse)",
        f"*Intelligence snapshot for **{today_str}***",
        "",
    ]

    if not papers:
        lines.append("> No new papers indexed today. Check back tomorrow!")
    else:
        for idx, paper in enumerate(papers, 1):
            lines.append(f"### {idx}. [{paper['title']}]({paper['url']})")
            lines.append(f"- **Authors:** {paper['authors']} | **Published:** `{paper['date']}`")
            lines.append(f"- **Core Finding:** {paper['summary']}")
            lines.append("")

    lines.append(f"<sub>Daily logs stored in [`data/til/`](./data/til/).</sub>")
    lines.append("<!-- END_DAILY_TIL -->")
    return "\n".join(lines)


def write_daily_til_archive(today_str, papers):
    TIL_DIR.mkdir(parents=True, exist_ok=True)
    file_path = TIL_DIR / f"{today_str}.md"
    content = [
        f"# Daily TIL (Curated arXiv & Engineering Pulse): {today_str}",
        "",
        "## Highlights",
        "",
    ]
    for idx, paper in enumerate(papers, 1):
        content.append(f"### {idx}. [{paper['title']}]({paper['url']})")
        content.append(f"- **Authors:** {paper['authors']}")
        content.append(f"- **Date:** {paper['date']}")
        content.append(f"- **Abstract:** {paper['summary']}")
        content.append("")

    file_path.write_text("\n".join(content), encoding="utf-8")
    print(f"Writing daily TIL to {file_path}")


def update_readme(new_section):
    if not README_PATH.exists():
        print("README.md not found!")
        return

    content = README_PATH.read_text(encoding="utf-8")

    start_delim = "<!-- START_DAILY_TIL -->"
    end_delim = "<!-- END_DAILY_TIL -->"

    if start_delim in content and end_delim in content:
        pattern = re.compile(rf"{re.escape(start_delim)}.*?{re.escape(end_delim)}", re.DOTALL)
        updated_content = pattern.sub(new_section, content)
    else:
        target_str = '<h3 align="center">'
        if target_str in content:
            replacement = new_section + "\n\n---\n\n" + target_str
            updated_content = content.replace(target_str, replacement, 1)
        else:
            updated_content = content + "\n\n---\n\n" + new_section + "\n"

    README_PATH.write_text(updated_content, encoding="utf-8")
    print("README.md updated successfully with the latest snapshot.")


def main():
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"Fetching arXiv preprints for {today_str}...")
    papers = fetch_arxiv_preprints()
    print(f"Fetched {len(papers)} papers.")

    write_daily_til_archive(today_str, papers)
    new_section = build_markdown_section(today_str, papers)
    update_readme(new_section)


if __name__ == "__main__":
    main()
