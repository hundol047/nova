# Round R partial publication status

The user explicitly approved publication of the five synthetic trace archives, final reports and v23 ZIP on 2026-10-09. Those approved artifacts are included on this review branch. The broader detailed evaluation JSON and complete release binding remain blocked by automatic approval review pending explicit approval for that full file list.

This is a review branch, not the complete target-branch release. Its existing CURRENT_RELEASE/v22 pointer does not certify this branch's modified runtime. Do not treat it as a release package until the complete current verification record is published and connected.

Verified local runtime: `18b994984d0e22c1ee15a3e9ffcc125d5056b46b`. Byte-identical published runtime: `cf31e011244a9f5340ea36c05a723dc1d11177aa`. Full local source tree equality was verified; code has not changed after frozen validation. Local tests: 2119 passed, 0 failed, 1 skipped. New-case clinical safety remains FAIL; actual LLM and official API remain unverified.

Reports: `ROUND_R_REPAIR_REPORT_KO.md` and `ROUND_R_FOLLOWUP_KO.md`. Some detailed evidence references in those reports are still local pending approval. Original target `claude/determined-brahmagupta-wrfveb` and main are unchanged by this partial publication.
