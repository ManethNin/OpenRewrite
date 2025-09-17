#!/usr/bin/env python3
"""
csv_to_jsonl_prompt.py

Convert rows from a CSV (with columns like Name, Description, Recipe type,
Source code preview, Recipe Options) into Instruction-Response JSONL
suitable for instruction-finetuning.

Usage:
    python csv_to_jsonl_prompt.py \
        --input recipes.csv \
        --output finetune.jsonl \
        --strip-license \
        --max-response-tokens 2000
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Optional

# ---------- Utilities ----------

def normalize_whitespace(s: str) -> str:
    """Collapse multiple spaces/tabs and normalize newlines."""
    if s is None:
        return ""
    # Normalize CRLF to LF
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # Remove trailing/leading whitespace on each line but keep line breaks
    lines = [line.rstrip() for line in s.split("\n")]
    # Collapse multiple blank lines to a maximum of 2
    out_lines = []
    blank_count = 0
    for line in lines:
        if line.strip() == "":
            blank_count += 1
        else:
            blank_count = 0
        if blank_count <= 2:
            out_lines.append(line)
    return "\n".join(out_lines).strip()

_LICENSE_COMMENT_RE = re.compile(r"(?s)/\*.*?\*/\s*")  # matches /* ... */ blocks (multiline)

def strip_license_header(code: str) -> str:
    """Remove a leading C-style license block (/* ... */) if present."""
    if not code:
        return code
    return _LICENSE_COMMENT_RE.sub("", code, count=1).lstrip()

def safe_truncate_text(text: str, max_chars: int) -> str:
    """Truncate conservatively on character boundary and append a marker."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n<<TRUNCATED>>"

def estimate_tokens_by_whitespace(text: str) -> int:
    """Very rough token estimate by whitespace splitting (useful if no tokenizer)."""
    if not text:
        return 0
    return max(1, len(text.split()))

# ---------- Prompt construction (expert templates) ----------

INSTRUCTION_TEMPLATE = (
    "You were given a task to implement an automated OpenRewrite recipe.\n\n"
    "Task name: {name}\n"
    "Language / Type: {recipe_type}\n"
    "Description: {description}\n\n"
    "Produce the complete implementation/code for this recipe."
)

# Optionally the instruction can include additional guidance or constraints:
INSTRUCTION_TEMPLATE_WITH_OPTIONS_IN_PROMPT = (
    INSTRUCTION_TEMPLATE +
    "\n\nDo not include any personal commentary. The expected output should be the code and the recipe options exactly as they appear in the response field."
)

RESPONSE_TEMPLATE_CODEFENCE = (
    "```{lang}\n{code}\n```\n\nRecipe Options:\n{options}"
)

# ---------- Main conversion ----------

def build_example(
    name: str,
    description: str,
    recipe_type: str,
    source_code: str,
    recipe_options: str,
    *,
    strip_license: bool = True,
    max_response_chars: Optional[int] = None,
    include_options_in_instruction: bool = False
) -> dict:
    """Construct a single instruction-response record."""
    name = normalize_whitespace(name or "")
    description = normalize_whitespace(description or "")
    recipe_type = (recipe_type or "unknown").strip()
    source_code = source_code or ""
    recipe_options = recipe_options or ""

    if strip_license:
        source_code = strip_license_header(source_code)

    source_code = normalize_whitespace(source_code)

    # If source code is extremely short, we still produce consistent code fence
    code_lang = "java" if "java" in recipe_type.lower() else ""

    # Build instruction
    if include_options_in_instruction:
        instruction = INSTRUCTION_TEMPLATE_WITH_OPTIONS_IN_PROMPT.format(
            name=name, recipe_type=recipe_type, description=description
        )
    else:
        instruction = INSTRUCTION_TEMPLATE.format(
            name=name, recipe_type=recipe_type, description=description
        )

    # Build response with code fences to preserve formatting
    response = RESPONSE_TEMPLATE_CODEFENCE.format(
        lang=code_lang,
        code=source_code.strip() if source_code.strip() else "<NO SOURCE PROVIDED>",
        options=normalize_whitespace(recipe_options)
    )

    # Optionally truncate very large responses
    if max_response_chars is not None:
        response = safe_truncate_text(response, max_response_chars)

    example = {
        "instruction": instruction,
        # include an 'input' field for Alpaca-style compatibility (left empty)
        "input": "",
        "response": response
    }
    return example

# ---------- CSV reading & writing ----------

def convert_csv_to_jsonl(
    input_path: Path,
    output_path: Path,
    *,
    field_map: dict,
    strip_license: bool,
    max_response_chars: Optional[int],
    include_options_in_instruction: bool,
    deduplicate: bool
):
    seen = set()
    written = 0
    with input_path.open(newline="", encoding="utf-8") as csvfile, \
         output_path.open("w", encoding="utf-8") as out_f:
        reader = csv.DictReader(csvfile)
        for row_idx, row in enumerate(reader, start=1):
            # Map fields with fallback
            name = row.get(field_map.get("name", "Name"), "").strip()
            description = row.get(field_map.get("description", "Description"), "")
            recipe_type = row.get(field_map.get("recipe_type", "Recipe type"), "")
            source_code = row.get(field_map.get("source_code", "Source code preview"), "")
            recipe_options = row.get(field_map.get("recipe_options", "Recipe Options"), "")

            if not (name or description or source_code):
                # skip empty rows
                continue

            record = build_example(
                name=name,
                description=description,
                recipe_type=recipe_type,
                source_code=source_code,
                recipe_options=recipe_options,
                strip_license=strip_license,
                max_response_chars=max_response_chars,
                include_options_in_instruction=include_options_in_instruction
            )

            # Deduplicate by instruction + response hash
            key = (record["instruction"].strip(), record["response"].strip())
            if deduplicate:
                keyh = json.dumps(key, ensure_ascii=False)
                if keyh in seen:
                    continue
                seen.add(keyh)

            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1

    print(f"Wrote {written} records to {output_path}", file=sys.stderr)

# ---------- CLI ----------

def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert recipe CSV to instruction-response JSONL")
    parser.add_argument("--input", "-i", type=Path, required=True, help="Input CSV file")
    parser.add_argument("--output", "-o", type=Path, required=True, help="Output JSONL file")
    parser.add_argument("--strip-license", action="store_true", default=False,
                        help="Remove leading /* ... */ license header from source code")
    parser.add_argument("--max-response-chars", type=int, default=None,
                        help="If set, truncate response to this many characters (useful to avoid giant examples)")
    parser.add_argument("--include-options-in-instruction", action="store_true", default=False,
                        help="Place recipe options text inside the instruction (not recommended for most training)")
    parser.add_argument("--deduplicate", action="store_true", default=True,
                        help="Deduplicate identical instruction+response pairs (default: True)")
    parser.add_argument("--name-field", default="Name", help="CSV column name for 'Name'")
    parser.add_argument("--description-field", default="Description", help="CSV column name for 'Description'")
    parser.add_argument("--recipe-type-field", default="Recipe type", help="CSV column name for 'Recipe type'")
    parser.add_argument("--source-code-field", default="Source code preview", help="CSV column name for the code")
    parser.add_argument("--options-field", default="Recipe Options", help="CSV column name for options")
    args = parser.parse_args(argv)

    field_map = {
        "name": args.name_field,
        "description": args.description_field,
        "recipe_type": args.recipe_type_field,
        "source_code": args.source_code_field,
        "recipe_options": args.options_field
    }

    convert_csv_to_jsonl(
        input_path=args.input,
        output_path=args.output,
        field_map=field_map,
        strip_license=args.strip_license,
        max_response_chars=args.max_response_chars,
        include_options_in_instruction=args.include_options_in_instruction,
        deduplicate=args.deduplicate
    )

if __name__ == "__main__":
    main()
