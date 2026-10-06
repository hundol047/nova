"""Publish test outcomes without parameter text, paths, hostnames, or output logs."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def sanitize(path):
    path = Path(path)
    raw = path.read_bytes()
    original = ET.fromstring(raw)
    if original.get("public_summary") == "sha256-identities-v1":
        return
    root = ET.Element("testsuites", public_summary="sha256-identities-v1")
    suite = ET.SubElement(root, "testsuite", name="verified_tests")
    totals = dict(tests=0, passed=0, failures=0, errors=0, skipped=0)
    for case in original.iter("testcase"):
        identity = json.dumps([case.get("classname"), case.get("name")], ensure_ascii=False)
        digest = hashlib.sha256(identity.encode()).hexdigest()
        out = ET.SubElement(suite, "testcase", classname="sha256", name=digest,
                            time=case.get("time", "0"))
        totals["tests"] += 1
        outcome = "passed"
        for tag, count in (("failure", "failures"), ("error", "errors"), ("skipped", "skipped")):
            if case.find(tag) is not None:
                ET.SubElement(out, tag, message="See retained original report; details withheld from public summary")
                outcome = count
                break
        totals[outcome] += 1
    suite.attrib.update({k: str(v) for k, v in totals.items() if k != "passed"})
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    path.with_suffix(".receipt.json").write_text(json.dumps({
        "format": "public-test-outcomes-v1", "original_sha256": hashlib.sha256(raw).hexdigest(),
        "summary_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "counts": totals,
        "identity": "SHA256 of JSON [classname, name] with ensure_ascii=False",
        "redacted": ["test names and parameters", "suite metadata", "paths", "output", "failure and skip details"],
        "note": "Original reports retained locally. Outcomes and durations preserved; this is not a new test run."
    }, indent=2) + "\n")


if __name__ == "__main__":
    import sys
    for name in sys.argv[1:]:
        sanitize(name)
