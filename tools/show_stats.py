import json
from pathlib import Path


# Duong dan den file save.json o thu muc goc
ROOT_DIR = Path(__file__).resolve().parent.parent
SAVE_FILE = ROOT_DIR / "save.json"


def load_save():
    """Doc du lieu thanh tich tu save.json."""
    if not SAVE_FILE.exists():
        print("Chua tim thay file save.json!")
        return None

    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError) as error:
        print(f"Loi khi doc file save: {error}")
        return None


def show_statistics():
    data = load_save()

    if data is None:
        return

    levels = data.get("levels", {})

    total_levels = len(levels)
    total_coins = sum(level.get("coins", 0) for level in levels.values())
    total_gems = sum(len(level.get("gems", [])) for level in levels.values())
    total_score = sum(level.get("score", 0) for level in levels.values())

    rank_order = {"C": 1, "B": 2, "A": 3, "S": 4}
    best_rank = max(
        (level.get("rank", "C") for level in levels.values()),
        key=lambda rank: rank_order.get(rank, 0),
        default="N/A"
    )

    print("\n" + "=" * 42)
    print("          WAYFARER - PLAYER STATISTICS")
    print("=" * 42)

    print(f"So man da co thanh tich : {total_levels}")
    print(f"So man da mo khoa       : {data.get('unlocked', 1)}")
    print(f"Tong xu trong thanh tich: {total_coins}")
    print(f"Tong gem trong thanh tich: {total_gems}")
    print(f"Tong diem cac man       : {total_score}")
    print(f"Rank tot nhat           : {best_rank}")

    print("\n" + "-" * 42)
    print("          CHI TIET TUNG MAN")
    print("-" * 42)

    if not levels:
        print("Chua co thanh tich nao.")
    else:
        for name, record in levels.items():
            print(f"\nMan: {name}")
            print(f"  Thoi gian tot nhat: {record.get('time', 0):.2f} giay")
            print(f"  Xu: {record.get('coins', 0)}")
            print(f"  Gem: {len(record.get('gems', []))}")
            print(f"  Diem: {record.get('score', 0)}")
            print(f"  Rank: {record.get('rank', 'C')}")

    print("\n" + "=" * 42)


if __name__ == "__main__":
    show_statistics()