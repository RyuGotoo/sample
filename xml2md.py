import argparse
import sys
import os
from pathlib import Path
from xml.etree import ElementTree as ET
import re
from typing import Optional, Set


def _norm_text(elem):
    if elem is None:
        return ""
    # Join all text within the element, collapsing whitespace
    text = "".join(elem.itertext())
    # Keep intentional single newlines but strip indentation
    lines = [line.strip() for line in text.splitlines()]
    # Collapse multiple blank lines
    out = []
    prev_blank = False
    for ln in lines:
        if ln:
            out.append(ln)
            prev_blank = False
        else:
            if not prev_blank:
                out.append("")
                prev_blank = True
    return "\n".join(out).strip()


def _bullets_from_textblock(text):
    bullets = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("- "):
            bullets.append(s[2:].strip())
        else:
            bullets.append(s)
    return bullets


def _parse_xml_tolerant(xml_path: Path) -> ET.ElementTree:
    """Parse XML, tolerating stray '&' by auto-escaping when needed."""
    try:
        return ET.parse(xml_path)
    except ET.ParseError:
        # Attempt to auto-escape bare ampersands
        raw = xml_path.read_text(encoding="utf-8")
        fixed = re.sub(r"&(?![a-zA-Z#0-9]+;)", "&amp;", raw)
        return ET.ElementTree(ET.fromstring(fixed))


def xml_to_markdown(
    xml_path: Path,
    analysis_graph=None,
    func_id: Optional[str] = None,
    docs_root: Optional[Path] = None,
) -> str:
    tree = _parse_xml_tolerant(xml_path)
    root = tree.getroot()
    if root.tag != "function":
        raise ValueError("Root element must be <function>")

    name = _norm_text(root.find("name")) or "(名称未設定)"
    purpose = _norm_text(root.find("purpose"))
    summary = _norm_text(root.find("summary"))

    # Arguments
    args_md = []
    args_el = root.find("arguments")
    if args_el is not None:
        for arg in args_el.findall("arg"):
            aname = _norm_text(arg.find("name"))
            atype = _norm_text(arg.find("type"))
            adesc = _norm_text(arg.find("description"))
            label = f"- {aname} ({atype}): {adesc}" if aname or atype or adesc else None
            if label:
                args_md.append(label)

    # Return value
    ret_el = root.find("return-value")
    rtype = rdesc = ""
    if ret_el is not None:
        rtype = _norm_text(ret_el.find("type"))
        rdesc = _norm_text(ret_el.find("description"))

    # Remarks
    remarks_el = root.find("remarks")
    remarks_md = []
    if remarks_el is not None:
        rtext = _norm_text(remarks_el)
        if rtext:
            remarks_md = _bullets_from_textblock(rtext)

    # Process flow
    flow_el = root.find("process-flow")
    steps_md = []
    if flow_el is not None:
        for step in flow_el.findall("step"):
            descr = _norm_text(step.find("description"))
            rationale = _norm_text(step.find("rationale"))
            fname = _norm_text(step.find("function_name"))
            line = None
            if descr and rationale:
                line = f"{descr} — {rationale}"
            elif descr:
                line = descr
            elif rationale:
                line = rationale
            if line is None:
                line = ""
            if fname:
                # Append function hint if present
                line = (line + f" (関数: {fname})").strip()
            if line:
                steps_md.append(line)

    # Database queries
    dbq_el = root.find("database-queries")
    queries = []
    if dbq_el is not None:
        for q in dbq_el.findall("query"):
            qdesc = _norm_text(q.find("description"))
            sql = _norm_text(q.find("pseudo-sql"))
            if qdesc or sql:
                queries.append((qdesc, sql))

    # Build Markdown in Japanese headings
    lines = []
    lines.append(f"# {name}")

    if purpose:
        lines.append("")
        lines.append("**目的**")
        lines.append("")
        lines.append(purpose)

    if summary:
        lines.append("")
        lines.append("**概要**")
        lines.append("")
        # Keep original paragraphs without forced wrapping (better for CJK)
        for para in summary.split("\n\n"):
            lines.append(para)
            lines.append("")
        if lines and lines[-1] == "":
            lines.pop()

    if args_md:
        lines.append("")
        lines.append("**引数**")
        for item in args_md:
            lines.append(item)

    if rtype or rdesc:
        lines.append("")
        lines.append("**戻り値**")
        if rtype and rdesc:
            lines.append(f"- 型: {rtype}")
            lines.append(f"- 説明: {rdesc}")
        elif rtype:
            lines.append(f"- 型: {rtype}")
        elif rdesc:
            lines.append(f"- 説明: {rdesc}")

    if remarks_md:
        lines.append("")
        lines.append("**注意事項**")
        for r in remarks_md:
            lines.append(f"- {r}")

    if steps_md:
        lines.append("")
        lines.append("**処理の流れ**")
        for i, s in enumerate(steps_md, 1):
            lines.append(f"{i}. {s}")

    if queries:
        lines.append("")
        lines.append("**データベースクエリ**")
        for qdesc, sql in queries:
            if qdesc:
                lines.append(f"- 説明: {qdesc}")
            if sql:
                lines.append("  SQL:")
                lines.append("  ```")
                lines.append("  " + sql.replace("\n", "\n  "))
                lines.append("  ```")

    # Append call relationships (recursive trees) if analysis graph is available
    if analysis_graph:
        # Link builder preferring doc.md under docs_root
        def _entry_link_by_id(fid: str) -> str:
            entry = analysis_graph.id_to_entry.get(fid, {})
            n = entry.get("name", "") or fid
            fp = entry.get("file_path", "")
            ln = entry.get("line_start")
            ln_txt = f":{ln}" if isinstance(ln, int) else ""
            if docs_root and n and fp:
                parts = Path(fp).with_suffix("").parts
                if parts and parts[0].endswith("-master"):
                    parts = parts[1:]
                target = Path(docs_root, *parts, n, "doc.md")
                try:
                    rel = os.path.relpath(target, start=xml_path.parent)
                except Exception:
                    rel = str(target)
                return f"[{n}]({rel})"
            if fp:
                return f"[{n}]({fp}) — {fp}{ln_txt}"
            return n

        def _children(fid: str, direction: str) -> list[str]:
            if direction == "callees":
                return sorted(analysis_graph.calls_map.get(fid, ()))
            else:
                return sorted(analysis_graph.callers_map.get(fid, ()))

        def _render_tree(
            start_ids: Set[str],
            direction: str,
            max_depth: int = 8,
            max_children: int = 30,
        ) -> list[str]:
            out: list[str] = []

            def dfs(fid: str, depth: int, stack: list[str]):
                indent = "  " * depth
                label = _entry_link_by_id(fid)
                if fid in stack:
                    out.append(f"{indent}- {label} … (循環)")
                    return
                if depth >= max_depth:
                    out.append(f"{indent}- {label} … (省略)")
                    return
                out.append(f"{indent}- {label}")
                ch = _children(fid, direction)
                if not ch:
                    return
                stack.append(fid)
                for idx, cid in enumerate(ch):
                    if idx >= max_children:
                        out.append(f"{indent}  … (他 {len(ch) - max_children} 件省略)")
                        break
                    dfs(cid, depth + 1, stack)
                stack.pop()

            for sid in sorted(start_ids):
                for cid in _children(sid, direction):
                    dfs(cid, 0, [])
            return out

        # Determine starting ids
        start_ids: Set[str] = set()
        if func_id:
            start_ids.add(func_id)
        elif name:
            start_ids = set(analysis_graph.name_to_ids.get(name, set()))

        if start_ids:
            callee_tree = _render_tree(start_ids, direction="callees")
            if callee_tree:
                lines.append("")
                lines.append("**Callee**")
                lines.extend(callee_tree)
            caller_tree = _render_tree(start_ids, direction="callers")
            if caller_tree:
                lines.append("")
                lines.append("**Caller**")
                lines.extend(caller_tree)

    return "\n".join(lines).rstrip() + "\n"


def _convert_one(input_xml: Path, output_path: Optional[Path], analysis_graph=None):
    # Try to infer function id from sibling files like 'func_<id>'
    inferred_id = None
    try:
        for p in input_xml.parent.iterdir():
            if p.is_file() and p.name.startswith("func_"):
                inferred_id = p.name
                break
    except Exception:
        inferred_id = None

    # Infer docs_root using analysis info so that cross-links point to doc.md
    docs_root = None
    if analysis_graph and inferred_id:
        entry = analysis_graph.id_to_entry.get(inferred_id)
        if entry and entry.get("file_path") and entry.get("name"):
            parts = Path(entry["file_path"]).with_suffix("").parts
            if parts and parts[0].endswith("-master"):
                parts = parts[1:]
            subpath = Path(*parts) / entry["name"]
            doc_dir = input_xml.parent
            # Find ancestor 'root' such that root/subpath == doc_dir
            for anc in [doc_dir, *doc_dir.parents]:
                try:
                    if (anc / subpath).resolve() == doc_dir.resolve():
                        docs_root = anc
                        break
                except Exception:
                    continue

    md = xml_to_markdown(
        input_xml,
        analysis_graph=analysis_graph,
        func_id=inferred_id,
        docs_root=docs_root,
    )
    if output_path is None:
        output_path = input_xml.with_suffix(".md")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(md, encoding="utf-8")
    elif str(output_path) == "-":
        sys.stdout.write(md)
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(md, encoding="utf-8")


class AnalysisGraph:
    def __init__(self, id_to_entry, name_to_ids, calls_map, callers_map):
        self.id_to_entry = id_to_entry
        self.name_to_ids = name_to_ids
        self.calls_map = calls_map
        self.callers_map = callers_map

    def get_callers_callees_by_name(self, func_name: str):
        ids = self.name_to_ids.get(func_name, set())
        callees_ids = set()
        callers_ids = set()
        for fid in ids:
            callees_ids.update(self.calls_map.get(fid, ()))
            callers_ids.update(self.callers_map.get(fid, ()))
        # Remove self-refs
        callees_ids.difference_update(ids)
        callers_ids.difference_update(ids)
        callees = [self.id_to_entry.get(cid, {}) for cid in sorted(callees_ids)]
        callers = [self.id_to_entry.get(cid, {}) for cid in sorted(callers_ids)]
        return callers, callees

    def get_callers_callees_by_id(self, fid: str):
        callees_ids = set(self.calls_map.get(fid, ()))
        callers_ids = set(self.callers_map.get(fid, ()))
        # Remove self-refs
        if fid in callees_ids:
            callees_ids.remove(fid)
        if fid in callers_ids:
            callers_ids.remove(fid)
        callees = [self.id_to_entry.get(cid, {}) for cid in sorted(callees_ids)]
        callers = [self.id_to_entry.get(cid, {}) for cid in sorted(callers_ids)]
        return callers, callees


_ANALYSIS_CACHE = {}


def load_analysis_graph(path: Path) -> Optional[AnalysisGraph]:
    if not path.exists():
        return None
    key = str(path.resolve())
    if key in _ANALYSIS_CACHE:
        return _ANALYSIS_CACHE[key]
    import json

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # First pass: collect functions
    id_to_entry = {}
    name_to_ids = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "func":
            continue
        fid = item.get("id")
        if not fid or not str(fid).startswith("func_"):
            continue
        id_to_entry[fid] = {
            "id": fid,
            "name": item.get("name"),
            "file_path": item.get("file_path"),
            "line_start": item.get("line_start"),
        }
        n = item.get("name")
        if n:
            name_to_ids.setdefault(n, set()).add(fid)

    # Second pass: build call maps
    calls_map = {}
    callers_map = {}
    for item in data:
        if not isinstance(item, dict) or item.get("type") != "func":
            continue
        src_id = item.get("id")
        if src_id not in id_to_entry:
            continue
        raw_calls = item.get("calls") or []
        tgt_ids = [c for c in raw_calls if c in id_to_entry]
        if tgt_ids:
            calls_map[src_id] = set(tgt_ids)
            for t in tgt_ids:
                callers_map.setdefault(t, set()).add(src_id)

    graph = AnalysisGraph(id_to_entry, name_to_ids, calls_map, callers_map)
    _ANALYSIS_CACHE[key] = graph
    return graph


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert XML function docs to Markdown (file or directory)"
    )
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        help="XML file or directory to process. If directory, searches recursively for 'doc.xml'",
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=None,
        help="Input XML file (ignored if 'path' is provided)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output Markdown file (file mode only). Default: same name as XML; use '-' for stdout",
    )
    parser.add_argument(
        "-a",
        "--analysis",
        type=Path,
        default=None,
        help="Path to analysis_result.json for caller/callee links (default: auto-detect)",
    )
    args = parser.parse_args(argv)

    # Resolve analysis graph once
    analysis_path = args.analysis
    if analysis_path is None:
        # Auto-detect common locations, robust to cwd being different from repo root
        candidates = []
        # 1) relative to current working directory
        candidates += [
            Path("output_ffmpeg_01/analysis_result.json"),
            Path("analysis_result.json"),
        ]
        # 2) relative to script root (repo root = parent of this script's dir)
        try:
            script_root = Path(__file__).resolve().parent.parent
            candidates += [
                script_root / "output_ffmpeg_01/analysis_result.json",
                script_root / "analysis_result.json",
            ]
        except Exception:
            pass
        # 3) walk up from cwd
        try:
            for base in [Path.cwd(), *Path.cwd().parents]:
                candidates += [
                    base / "output_ffmpeg_01/analysis_result.json",
                    base / "analysis_result.json",
                ]
        except Exception:
            pass
        # pick first existing
        for c in candidates:
            if c.exists():
                analysis_path = c
                break
    analysis_graph = load_analysis_graph(analysis_path) if analysis_path else None

    # Directory mode if 'path' is a directory
    if args.path and args.path.is_dir():
        if args.output not in (None,):
            parser.error("-o/--output cannot be used with directory input")
        count = 0
        for xml_file in args.path.rglob("doc.xml"):
            try:
                _convert_one(xml_file, None, analysis_graph=analysis_graph)
                count += 1
            except Exception as e:
                print(f"[WARN] Failed to convert {xml_file}: {e}", file=sys.stderr)
        if count == 0:
            print("[INFO] No 'doc.xml' files found.", file=sys.stderr)
        return

    # Single-file mode
    input_path = args.path or args.input or Path("sample.xml")
    if not input_path.exists():
        parser.error(f"Input XML not found: {input_path}")
    _convert_one(input_path, args.output, analysis_graph=analysis_graph)


if __name__ == "__main__":
    main()
