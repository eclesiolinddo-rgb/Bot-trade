"""Formatting helpers for messages sent by the bot"""


def format_ranking(items):
    if not items:
        return "Sem ranking disponível."
    lines = ["🏆 Ranking — Top traders:\n"]
    for i, it in enumerate(items, start=1):
        name = it.get("displayName") or it.get("uid")
        score = it.get("score", 0)
        lines.append(f"{i}. {name} — {score}")
    return "\n".join(lines)


def format_signal(signal):
    # signal: {symbol, direction, size, sl, tp, meta}
    return f"Sinal: {signal.get('symbol')} {signal.get('direction')}\nTamanho: {signal.get('size')}\nSL: {signal.get('sl')} TP: {signal.get('tp')}"
