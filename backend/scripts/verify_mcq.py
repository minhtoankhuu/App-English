"""Kiểm chứng nhanh chất lượng đề trắc nghiệm mà KHÔNG cần Docker/Postgres.

Dùng đúng prompt + schema thật của app (prompts.py, openai_provider._RESPONSE_SCHEMA),
chỉ thay phần RAG bằng danh sách chunk mẫu viết tay bên dưới — nên đo được đúng thứ
vừa thay đổi (prompt v12 + trường why_wrong) mà không cần dựng DB.

Chạy:
    OPENAI_API_KEY=sk-... ./.venv/Scripts/python.exe scripts/verify_mcq.py
Tùy chọn:  --count 8  --model gpt-4o-mini  --no-why-wrong (mô phỏng bản CŨ để so sánh)
"""

import argparse
import json
import os
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
# Console Windows mac dinh cp1252 -> ep UTF-8 de in duoc tieng Viet/IPA.
sys.stdout.reconfigure(encoding="utf-8")

from app.services.mcq_check import check_multiple_choice
from app.services.openai_provider import _RESPONSE_SCHEMA
from app.services.prompts import PROMPT_VERSION, build_system_prompt, build_user_prompt

# Chunk mẫu mô phỏng vốn từ Unit "Communication in the Future" (GS8 Unit 10).
SAMPLE_CHUNKS = [
    ("c1", "telepathy (n) /təˈlepəθi/ : thần giao cách cảm"),
    ("c2", "voice message (n) : tin nhắn thoại"),
    ("c3", "social network (n) : mạng xã hội"),
    ("c4", "interact with sb : tương tác với ai"),
    ("c5", "keep in contact with sb : giữ liên lạc với ai"),
    ("c6", "face to face (adv) : mặt đối mặt, trực tiếp"),
    ("c7", "in person : trực tiếp (gặp mặt)"),
    ("c8", "instant messaging (n) : nhắn tin tức thời"),
    ("c9", "Present Perfect : have/has + V3 — diễn tả việc đã xảy ra, còn liên hệ hiện tại"),
    ("c10", "be keen on + V-ing/N : rất thích làm gì"),
    ("c11", "be interested in + V-ing/N : quan tâm/hứng thú với"),
    ("c12", "will + V1 : diễn tả hành động trong tương lai"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=8)
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--no-why-wrong", action="store_true", help="Bỏ why_wrong khỏi schema (bản CŨ) để so sánh")
    args = ap.parse_args()

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("Thiếu OPENAI_API_KEY trong biến môi trường.")
        raise SystemExit(1)

    import openai

    schema = json.loads(json.dumps(_RESPONSE_SCHEMA))
    if args.no_why_wrong:
        item = schema["properties"]["questions"]["items"]["properties"]["options"]["items"]
        item["properties"].pop("why_wrong", None)
        item["required"] = [r for r in item["required"] if r != "why_wrong"]

    system_prompt = build_system_prompt("multiple_choice", args.count, "A2")
    user_prompt = build_user_prompt("Communication in the Future", SAMPLE_CHUNKS, None, None)

    resp = openai.OpenAI(api_key=key).chat.completions.create(
        model=args.model,
        temperature=0.7,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "question_generation", "schema": schema, "strict": True},
        },
    )
    data = json.loads(resp.choices[0].message.content)

    mode = "KHÔNG why_wrong (bản cũ)" if args.no_why_wrong else f"CÓ why_wrong (prompt {PROMPT_VERSION})"
    print(f"=== {mode} | model={args.model} ===\n")
    flagged = 0
    for i, q in enumerate(data["questions"], 1):
        warnings = check_multiple_choice(q["prompt_text"], q.get("options"))
        flagged += bool(warnings)
        print(f"{i}. {'OK' if not warnings else 'CO CANH BAO'}")
        for line in q["prompt_text"].split("\n"):
            print("     " + line)
        for opt in q.get("options") or []:
            mark = "*" if opt.get("is_correct") else " "
            reason = opt.get("why_wrong")
            print(f"     {mark} {opt['label']}. {opt['text']:<20} why_wrong: {reason}")
        for w in warnings:
            print("     ! " + w)
        print()
    print(f"=== {flagged}/{len(data['questions'])} cau bi canh bao boi mcq_check ===")
    print("Doc tay tung cau: co phuong an nhieu nao THAY VAO CHO TRONG van dung khong?")


if __name__ == "__main__":
    main()
