#!/usr/bin/env python3
"""Check the buildless website and its GitHub Pages root-site references."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit


BASE_URL = "https://alex-duyminhtran.github.io/"
BASE_PATH = "/"
OWNER_EMAIL = "alex.duyminhtran@gmail.com"
PAGES = ("index.html", "privacy.html", "support.html")
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


@dataclass
class Element:
    tag: str
    attrs: dict[str, str]
    line: int
    ancestors: tuple[str, ...]


class Document(HTMLParser):
    def __init__(self, name: str) -> None:
        super().__init__(convert_charrefs=True)
        self.name = name
        self.elements: list[Element] = []
        self.ids: set[str] = set()
        self.stack: list[tuple[str, int]] = []
        self.problems: list[str] = []
        self.text: list[str] = []
        self.doctype = False

    def handle_decl(self, decl: str) -> None:
        self.doctype = decl.lower() == "doctype html"

    def add_element(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        line = self.getpos()[0]
        names = [name for name, _ in attrs]
        if len(names) != len(set(names)):
            self.problems.append(f"{self.name}:{line}: duplicate attribute on <{tag}>")
        values = {key: value if value is not None else "" for key, value in attrs}
        self.elements.append(Element(tag, values, line, tuple(item[0] for item in self.stack)))
        if identifier := values.get("id"):
            if identifier in self.ids:
                self.problems.append(f"{self.name}:{line}: duplicate id '{identifier}'")
            self.ids.add(identifier)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.add_element(tag, attrs)
        if tag not in VOID_TAGS:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.add_element(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        line = self.getpos()[0]
        if tag in VOID_TAGS:
            self.problems.append(f"{self.name}:{line}: void <{tag}> must not have an end tag")
        elif not self.stack or self.stack[-1][0] != tag:
            current = self.stack[-1][0] if self.stack else "nothing"
            self.problems.append(f"{self.name}:{line}: closing </{tag}> while <{current}> is open")
        else:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        self.text.append(data)

    def finish(self) -> None:
        self.close()
        for tag, line in self.stack:
            self.problems.append(f"{self.name}:{line}: unclosed <{tag}>")


class SiteValidator:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.documents: dict[str, Document] = {}
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.references = 0
        self.provenance_files = 0
        self.source_files = 0

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def parse_pages(self) -> None:
        for name in PAGES:
            path = self.root / name
            if not path.is_file():
                self.errors.append(f"{name}: required page is missing")
                continue
            document = Document(name)
            try:
                document.feed(path.read_text(encoding="utf-8"))
                document.finish()
            except (OSError, UnicodeError, ValueError) as error:
                self.errors.append(f"{name}: cannot parse UTF-8 HTML: {error}")
                continue
            self.documents[name] = document
            self.errors.extend(document.problems)

    def resolve_local(self, reference: str, owner: str, location: str,
                      *, allow_absolute: bool = False, check_fragment: bool = True) -> str | None:
        """Resolve with the deployed root-site URL."""
        if not reference.strip() or reference.strip() == "#":
            self.errors.append(f"{location}: replace the empty or '#' placeholder URL")
            return None
        parsed = urlsplit(reference)
        if parsed.scheme in ("mailto", "tel"):
            return None
        if parsed.scheme and parsed.scheme not in ("http", "https"):
            self.errors.append(f"{location}: unsupported URL scheme '{parsed.scheme}'")
            return None
        absolute = urlsplit(urljoin(urljoin(BASE_URL, owner), reference))
        if absolute.netloc != urlsplit(BASE_URL).netloc:
            return None
        if (parsed.scheme or reference.startswith("/")) and not allow_absolute:
            self.errors.append(f"{location}: use a relative website URL: {reference}")
        if not absolute.path.startswith(BASE_PATH):
            self.errors.append(f"{location}: URL escapes the website root: {reference}")
            return None
        relative = unquote(absolute.path[len(BASE_PATH):])
        destination = (self.root / relative).resolve()
        if not destination.is_relative_to(self.root):
            self.errors.append(f"{location}: reference escapes the website folder: {reference}")
            return None
        if destination.is_dir() or absolute.path.endswith("/"):
            destination /= "index.html"
        self.references += 1
        if not destination.is_file():
            self.errors.append(f"{location}: missing local file for '{reference}'")
            return None
        resolved_name = destination.relative_to(self.root).as_posix()
        if check_fragment and absolute.fragment and resolved_name.endswith(".html"):
            target = self.documents.get(resolved_name)
            if target is not None and unquote(absolute.fragment) not in target.ids:
                self.errors.append(f"{location}: missing #{absolute.fragment} in {resolved_name}")
        return resolved_name

    def check_documents(self) -> None:
        for name, document in self.documents.items():
            tags = document.elements
            self.require(document.doctype, f"{name}: declare <!doctype html>")
            for tag in ("html", "head", "body", "title", "main", "h1"):
                self.require(sum(node.tag == tag for node in tags) == 1,
                             f"{name}: expected exactly one <{tag}>")
            html = next((node for node in tags if node.tag == "html"), None)
            self.require(bool(html and re.fullmatch(r"en(?:-[A-Za-z]+)?", html.attrs.get("lang", ""))),
                         f"{name}: set the English document language")
            metadata = {
                node.attrs.get("name", node.attrs.get("property", "")): node.attrs.get("content", "")
                for node in tags if node.tag == "meta"
            }
            for key in ("description", "viewport", "og:title", "og:description", "og:image"):
                self.require(bool(metadata.get(key, "").strip()), f"{name}: missing {key} metadata")
            expected_url = urljoin(BASE_URL, "" if name == "index.html" else name)
            canonical_urls = [node.attrs.get("href") for node in tags
                              if node.tag == "link" and node.attrs.get("rel") == "canonical"]
            self.require(canonical_urls == [expected_url],
                         f"{name}: canonical URL must be {expected_url}")
            self.require(metadata.get("og:url") == expected_url,
                         f"{name}: og:url must be {expected_url}")
            self.require(metadata.get("og:image") == urljoin(BASE_URL, "assets/social-preview.png"),
                         f"{name}: use the root-site social-preview URL")
            self.require("width=device-width" in metadata.get("viewport", "").replace(" ", ""),
                         f"{name}: viewport must include width=device-width")
            self.resolve_local(metadata.get("og:image", ""), name, f"{name}:og:image", allow_absolute=True)

            skip_links = [node for node in tags if node.tag == "a"
                          and "skip" in node.attrs.get("class", "")
                          and node.attrs.get("href", "").startswith("#")]
            main_ids = {node.attrs.get("id") for node in tags if node.tag == "main"}
            self.require(any(node.attrs.get("href", "")[1:] in main_ids for node in skip_links),
                         f"{name}: provide a skip link to the main content ID")

            destinations: dict[str, set[str]] = {"header": set(), "footer": set()}
            email_links = 0
            images = [node for node in tags if node.tag == "img"]
            for node in tags:
                location = f"{name}:{node.line}"
                self.require(node.tag not in {"form", "iframe", "embed", "object"},
                             f"{location}: <{node.tag}> adds an unplanned service or form")
                for attribute in ("href", "src"):
                    if attribute not in node.attrs:
                        continue
                    reference = node.attrs[attribute]
                    parsed = urlsplit(reference)
                    if node.tag == "a" and parsed.scheme == "mailto":
                        address = unquote(parsed.path).lower()
                        self.require(address == OWNER_EMAIL, f"{location}: use the agreed support email")
                        email_links += 1
                    if parsed.netloc in {"apps.apple.com", "itunes.apple.com"}:
                        self.errors.append(f"{location}: no App Store listing exists yet; keep Coming soon")
                    external = bool(parsed.netloc and parsed.netloc != urlsplit(BASE_URL).netloc)
                    self.require(not (external and (attribute == "src" or node.tag in {"script", "link"})),
                                 f"{location}: external executable, image, font, or stylesheet: {reference}")
                    destination = self.resolve_local(
                        reference, name, location,
                        allow_absolute=node.tag == "link" and node.attrs.get("rel") == "canonical",
                    )
                    if destination and node.tag == "a":
                        for container in destinations:
                            if container in node.ancestors:
                                destinations[container].add(destination)
                if "srcset" in node.attrs:
                    for item in node.attrs["srcset"].split(","):
                        reference = item.strip().split()[0] if item.strip() else ""
                        self.require(not urlsplit(reference).netloc,
                                     f"{location}: responsive images must be local")
                        self.resolve_local(reference, name, location)
                if node.tag == "img":
                    self.require("alt" in node.attrs, f"{location}: image needs alt text or alt='' when decorative")
                    self.require(all(re.fullmatch(r"[1-9][0-9]*", node.attrs.get(size, ""))
                                     for size in ("width", "height")),
                                 f"{location}: set explicit positive image width and height")
                    if "footer" in node.ancestors:
                        self.require(node.attrs.get("loading") == "lazy", f"{location}: lazy-load the footer artwork")
                    elif images.index(node) >= 3 and node.attrs.get("loading") != "lazy":
                        self.warnings.append(f"{location}: consider loading='lazy' for this below-fold image")
            for container, links in destinations.items():
                missing = set(PAGES) - links
                self.require(not missing, f"{name}: {container} needs links to {', '.join(sorted(missing))}")
            if name in ("privacy.html", "support.html"):
                self.require(email_links > 0, f"{name}: add the working public mailto link")
            if name == "index.html":
                text = " ".join(" ".join(document.text).split()).lower()
                self.require("coming soon on iphone and ipad" in text,
                             "index.html: show 'Coming soon on iPhone and iPad' while the app is not live")

    def check_styles_and_scripts(self) -> None:
        for path in self.root.rglob("*"):
            if not path.is_file() or path.suffix not in {".css", ".js"}:
                continue
            relative = path.relative_to(self.root)
            if any(part.startswith(".") or part in {"verification", "Verification", "node_modules"} for part in relative.parts):
                continue
            content = path.read_text(encoding="utf-8")
            owner = relative.as_posix()
            if path.suffix == ".css":
                for match in re.finditer(r"url\(\s*(['\"]?)(.*?)\1\s*\)", content):
                    reference = match.group(2)
                    self.require(not urlsplit(reference).netloc, f"{owner}: external CSS URL is not allowed")
                    self.resolve_local(reference, owner, owner, check_fragment=False)
                self.require(not re.search(r"@import\s+(?:url\()?\s*['\"]?(?:https?:)?//", content, re.I),
                             f"{owner}: external CSS imports or fonts are not allowed")
            else:
                self.require(not re.search(r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(|sendBeacon\s*\(", content),
                             f"{owner}: network requests are outside this static website's scope")

    def check_provenance(self) -> None:
        path = self.root / "assets/provenance.json"
        if not path.is_file():
            self.errors.append("assets/provenance.json: missing approved asset provenance")
            return
        try:
            provenance = json.loads(path.read_text(encoding="utf-8"))
            sources = provenance["sources"]
            renditions = provenance["renditions"]
            self.require(bool(sources and renditions), "assets/provenance.json: empty source or rendition list")
            for key, entry in sources.items():
                self.require(entry.get("unchanged_after_generation") is True,
                             f"assets/provenance.json: source {key} was not verified unchanged")
                source = Path(entry["path"])
                if source.is_file():
                    self.require(hashlib.sha256(source.read_bytes()).hexdigest() == entry["sha256"],
                                 f"assets/provenance.json: source {key} hash no longer matches")
                    self.source_files += 1
            for filename, entry in renditions.items():
                rendition = (self.root / "assets" / filename).resolve()
                self.require(rendition.is_relative_to(self.root / "assets"),
                             f"assets/provenance.json: rendition path escapes assets: {filename}")
                if not rendition.is_relative_to(self.root / "assets") or not rendition.is_file():
                    self.errors.append(f"assets/provenance.json: missing rendition {filename}")
                    continue
                data = rendition.read_bytes()
                self.require(hashlib.sha256(data).hexdigest() == entry["sha256"],
                             f"assets/{filename}: SHA-256 does not match approved provenance")
                self.require(len(data) == entry["bytes"], f"assets/{filename}: byte size does not match provenance")
                self.require(entry.get("source_key") in sources, f"assets/{filename}: unknown provenance source")
                self.require(all(isinstance(entry.get(size), int) and entry[size] > 0 for size in ("width", "height")),
                             f"assets/{filename}: missing positive dimensions in provenance")
                if entry.get("operation", "").startswith("Byte-for-byte"):
                    source = sources.get(entry.get("source_key"), {})
                    self.require(entry["sha256"] == source.get("sha256"),
                                 f"assets/{filename}: unmodified copy does not match its source")
                self.provenance_files += 1
        except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
            self.errors.append(f"assets/provenance.json: malformed or unreadable provenance: {error}")

    def run(self) -> dict:
        self.parse_pages()
        self.check_documents()
        self.check_styles_and_scripts()
        self.check_provenance()
        self.require((self.root / ".nojekyll").is_file(), ".nojekyll: missing static GitHub Pages marker")
        return {
            "passed": not self.errors,
            "base_url": BASE_URL,
            "pages_checked": list(self.documents),
            "local_references_checked": self.references,
            "approved_renditions_checked": self.provenance_files,
            "available_original_sources_checked": self.source_files,
            "errors": self.errors,
            "warnings": self.warnings,
            "limitations": [
                "Static checks do not establish public deployment, legal completeness, or assistive-technology behavior.",
                "Original source hashes are rechecked when their recorded local paths are available; rendition hashes always are.",
            ],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--report", type=Path, help="Optional JSON report, relative to the site root unless absolute")
    args = parser.parse_args()
    root = args.root.resolve()
    result = SiteValidator(root).run()
    if args.report:
        report = args.report if args.report.is_absolute() else root / args.report
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for error in result["errors"]:
        print(f"ERROR: {error}")
    for warning in result["warnings"]:
        print(f"WARNING: {warning}")
    status = "PASS" if result["passed"] else "FAIL"
    print(f"{status}: {len(result['pages_checked'])} pages, "
          f"{result['local_references_checked']} website references, "
          f"{result['approved_renditions_checked']} approved assets, "
          f"{len(result['errors'])} errors, {len(result['warnings'])} warnings.")
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
