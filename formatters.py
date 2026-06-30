def format_ranking_message(items, title="Ranking"):
    if not items:
        return f"{title}\nNenhum dado disponível."
    lines = [f"*{title}*"]
    for i, doc in enumerate(items, start=1):
        name = doc.get("displayName") or doc.get("uid") or "—"
        score = doc.get("score", 0)
        lines.append(f"{i}. {name} — {score}")
    return "\n".join(lines)
