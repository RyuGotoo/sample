from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
import xml.etree.ElementTree as ET
from collections import defaultdict
from functools import lru_cache
from pathlib import Path


def _extract_text(node):
    """Return normalized text content for the given XML node."""
    if node is None:
        return ""
    text = "".join(node.itertext())
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = textwrap.dedent(text)
    text = text.strip()
    if re.fullmatch(r"<[^<>]+>", text):
        text = text[1:-1].strip()
    return text


def _collect_lines(text):
    if not text:
        return []
    return [line.rstrip() for line in text.splitlines()]


def function_to_markdown(root: ET.Element) -> str:
    lines: list[str] = []

    name = _extract_text(root.find("name"))
    if name:
        lines.append(f"# {name}")
        lines.append("")

    purpose = _extract_text(root.find("purpose"))
    if purpose:
        lines.append("## 目的")
        lines.append("")
        lines.extend(_collect_lines(purpose))
        lines.append("")

    summary = _extract_text(root.find("summary"))
    if summary:
        lines.append("## 概要")
        lines.append("")
        lines.extend(_collect_lines(summary))
        lines.append("")

    arguments = root.find("arguments")
    args = arguments.findall("arg") if arguments is not None else []
    if args:
        lines.append("## 引数")
        lines.append("")
        for index, arg in enumerate(args, 1):
            lines.append(f"### 引数 {index}")
            name_text = _extract_text(arg.find("name"))
            type_text = _extract_text(arg.find("type"))
            description_text = _extract_text(arg.find("description"))
            if name_text:
                lines.append(f"- 名前: {name_text}")
            if type_text:
                lines.append(f"- 型: {type_text}")
            if description_text:
                lines.append(f"- 説明: {description_text}")
            lines.append("")

    return_value = root.find("return-value")
    if return_value is not None:
        return_type = _extract_text(return_value.find("type"))
        return_description = _extract_text(return_value.find("description"))
        if return_type or return_description:
            lines.append("## 戻り値")
            lines.append("")
            if return_type:
                lines.append(f"- 型: {return_type}")
            if return_description:
                lines.append(f"- 説明: {return_description}")
            lines.append("")

    remark_lines = _collect_lines(_extract_text(root.find("remarks")))
    remarks = []
    for remark in remark_lines:
        cleaned = remark.strip()
        if not cleaned:
            continue
        if cleaned.startswith("- "):
            remarks.append(cleaned)
        elif cleaned.startswith("-"):
            remarks.append(f"- {cleaned[1:].strip()}")
        else:
            remarks.append(f"- {cleaned}")

    if remarks:
        lines.append("## 備考")
        lines.append("")
        for remark in remarks:
            lines.append(remark)
        lines.append("")

    process_flow = root.find("process-flow")
    steps = process_flow.findall("step") if process_flow is not None else []
    processed_steps = [s for s in (_extract_text(step) for step in steps) if s]
    if processed_steps:
        lines.append("## 処理の流れ")
        lines.append("")
        for idx, step in enumerate(processed_steps, 1):
            lines.append(f"{idx}. {step}")
        lines.append("")

    db_queries = root.find("database-queries")
    queries = db_queries.findall("query") if db_queries is not None else []
    if queries:
        lines.append("## データベースクエリ")
        lines.append("")
        for index, query in enumerate(queries, 1):
            lines.append(f"### クエリ {index}")
            lines.append("")
            desc = _extract_text(query.find("description")) or "不明"
            pseudo_sql = _extract_text(query.find("pseudo-sql")) or "不明"
            lines.append("説明:")
            lines.append(desc)
            lines.append("")
            lines.append("擬似SQL:")
            lines.append(pseudo_sql)
            lines.append("")

    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def parse_function(xml_path: Path) -> ET.Element:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    if root.tag != "function":
        raise ValueError("ルート要素は <function> である必要があります。")
    return root


def convert(
    xml_path: Path,
    analysis: AnalysisIndex | None = None,
    doc_lookup: dict[str, Path] | None = None,
) -> str:
    root = parse_function(xml_path)
    markdown = function_to_markdown(root)
    return _append_dependencies(markdown, xml_path, analysis, doc_lookup)


class AnalysisIndex:
    def __init__(
        self, functions: dict[str, dict[str, object]], callers: dict[str, list[str]]
    ):
        self._functions = functions
        self._callers = callers

    @classmethod
    def from_file(cls, path: Path) -> "AnalysisIndex":
        with path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        functions: dict[str, dict[str, object]] = {}
        callers: dict[str, list[str]] = defaultdict(list)
        for entry in data:
            if entry.get("type") != "func":
                continue
            func_id = entry.get("id")
            if not func_id:
                continue
            functions[func_id] = entry
        for entry in functions.values():
            for callee in entry.get("calls", []) or []:
                if callee in functions:
                    callers[callee].append(entry["id"])
        return cls(functions, callers)

    def get(self, func_id: str) -> dict[str, object] | None:
        return self._functions.get(func_id)

    def callers_of(self, func_id: str) -> list[dict[str, object]]:
        return [
            self._functions[cid]
            for cid in self._callers.get(func_id, [])
            if cid in self._functions
        ]

    def callees_of(self, func_id: str) -> list[dict[str, object]]:
        func = self.get(func_id)
        if not func:
            return []
        callees: list[dict[str, object]] = []
        for callee in func.get("calls", []) or []:
            info = self._functions.get(callee)
            if info:
                callees.append(info)
        return callees


def build_doc_lookup(root: Path) -> dict[str, Path]:
    lookup: dict[str, Path] = {}
    for func_marker in root.rglob("func_*"):
        if func_marker.is_file():
            lookup[func_marker.name] = func_marker.parent / "doc.md"
    return lookup


@lru_cache(maxsize=None)
def _load_purpose_from_doc(doc_md_path: str) -> str:
    doc_path = Path(doc_md_path)
    doc_xml = doc_path.with_name("doc.xml")
    if not doc_xml.exists():
        return ""
    try:
        tree = ET.parse(doc_xml)
    except ET.ParseError:
        return ""
    root = tree.getroot()
    if root.tag != "function":
        return ""
    return _extract_text(root.find("purpose"))


def _format_dependency_list(
    current_dir: Path,
    entries: list[dict[str, object]],
    doc_lookup: dict[str, Path] | None,
) -> list[str]:
    if not entries:
        return ["- なし"]
    lines: list[str] = []
    for entry in sorted(
        entries,
        key=lambda item: (
            str(item.get("name")) if item.get("name") else item.get("id")
        ),
    ):
        func_id = str(entry.get("id"))
        name = str(entry.get("name") or func_id)
        link = "#"
        purpose = ""
        if doc_lookup:
            target = doc_lookup.get(func_id)
            if target:
                relative = os.path.relpath(target, current_dir)
                link = Path(relative).as_posix()
                purpose = _load_purpose_from_doc(str(target))
        purpose = purpose or "（生成対象でないため情報なし）"
        lines.append(f"- [{name} ({func_id})]({link}): {purpose}")
    return lines


def _append_dependencies(
    markdown: str,
    xml_path: Path,
    analysis: AnalysisIndex | None,
    doc_lookup: dict[str, Path] | None,
) -> str:
    if not analysis:
        return markdown

    func_id = None
    for candidate in xml_path.parent.glob("func_*"):
        if candidate.is_file():
            func_id = candidate.name
            break
    if not func_id:
        return markdown

    if doc_lookup is not None and func_id not in doc_lookup:
        doc_lookup[func_id] = xml_path.with_name("doc.md")

    callers = analysis.callers_of(func_id)
    callees = analysis.callees_of(func_id)

    if not callers and not callees:
        return markdown

    current_dir = xml_path.parent
    sections: list[str] = []
    sections.append("## Caller")
    sections.append("")
    sections.extend(_format_dependency_list(current_dir, callers, doc_lookup))
    sections.append("")
    sections.append("## Callee")
    sections.append("")
    sections.extend(_format_dependency_list(current_dir, callees, doc_lookup))

    return markdown + "\n\n" + "\n".join(sections)


def process_directory(
    directory: Path,
    analysis: AnalysisIndex | None,
) -> list[Path]:
    generated_paths: list[Path] = []
    doc_lookup = build_doc_lookup(directory) if analysis else {}
    for xml_path in directory.rglob("doc.xml"):
        markdown = convert(xml_path, analysis=analysis, doc_lookup=doc_lookup)
        output_path = xml_path.with_name("doc.md")
        output_path.write_text(markdown, encoding="utf-8")
        generated_paths.append(output_path)
    return generated_paths


def main():
    parser = argparse.ArgumentParser(
        description="XMLファイルまたはディレクトリ内のdoc.xmlをMarkdownに変換します。"
    )
    parser.add_argument(
        "path",
        type=Path,
        help="入力XMLファイル、またはdoc.xmlを含むディレクトリのパス",
    )
    parser.add_argument(
        "analysis",
        type=Path,
        nargs="?",
        help="関数間依存関係を含む analysis_result.json のパス",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="入力が単一XMLファイルの場合の出力Markdownファイルのパス。省略時は標準出力に出力します。",
    )
    args = parser.parse_args()

    target = args.path
    analysis_index: AnalysisIndex | None = None

    if args.analysis:
        if not args.analysis.exists():
            parser.error(f"analysis_result.json が見つかりません: {args.analysis}")
        analysis_index = AnalysisIndex.from_file(args.analysis)

    if target.is_dir():
        if args.output:
            parser.error("ディレクトリを指定した場合、--output は使用できません。")
        generated_paths = process_directory(target, analysis_index)
        if not generated_paths:
            print("doc.xml が見つかりませんでした。", file=sys.stderr)
        else:
            for output_path in generated_paths:
                print(f"生成しました: {output_path}")
        return

    if not target.exists():
        parser.error(f"指定されたパスが存在しません: {target}")

    doc_lookup = build_doc_lookup(target.parent) if analysis_index else None
    markdown = convert(target, analysis=analysis_index, doc_lookup=doc_lookup)

    if args.output:
        args.output.write_text(markdown, encoding="utf-8")
    else:
        print(markdown)


if __name__ == "__main__":
    main()
