#!/usr/bin/env python3
"""朋友圈摄影大赛模拟器 pengyouquan-contest.

7 天国庆假期，每天从 3 张候选照片里选 1 张发朋友圈，再选发布时间。
不同好友群体点赞偏好不同（爸妈爱烟火气、文青爱逼格、颜狗爱颜值），
选对时段对应群体点赞 x1.5。7 天后按总赞数授称号。纯标准库。
"""

import argparse
import random
import sys

COPYRIGHT = "Copyright (c) 2026 ljiang9"

# 好友群体：名称 -> (人数, {维度: 权重(整数,和为100)})
GROUPS = {
    "爸妈团": (30, {"颜值": 20, "逼格": 10, "烟火气": 70}),
    "文青圈": (25, {"颜值": 20, "逼格": 70, "烟火气": 10}),
    "颜狗团": (35, {"颜值": 70, "逼格": 20, "烟火气": 10}),
    "干饭人": (40, {"颜值": 30, "逼格": 20, "烟火气": 50}),
    "夜猫子": (20, {"颜值": 40, "逼格": 40, "烟火气": 20}),
}

# 发布时间 -> (文案, 被加成的群体)
SLOTS = {
    1: ("早上 8 点", "爸妈团"),
    2: ("中午 12 点", "干饭人"),
    3: ("晚上 9 点", "夜猫子"),
}

PHOTO_NAMES = [
    "日出云海", "夜市烧烤摊", "自拍九宫格", "古镇青石板",
    "火锅正在冒泡", "演唱会灯海", "沙漠星空", "外婆包的饺子",
    "城市天际线", "街角咖啡馆", "海边日落", "雪山倒影",
]

DAYS = 7

# 理论单日上限：全 100 分照片 + 最优时段 + 上热门 x2
_DAY_BASE_MAX = sum(size * 100 for size, _ in GROUPS.values())
_DAY_BASE_MAX += (40 * 100) // 2  # 干饭人被时段加成多出的 0.5 倍
DAY_MAX = _DAY_BASE_MAX * 2
MAX_TOTAL = DAY_MAX * DAYS


class IllegalMove(ValueError):
    """非法选择：照片编号或发布时间不合法。"""


def make_photo(rng, name):
    """生成一张随机三维照片，各维度 20~100。"""
    return {
        "name": name,
        "颜值": rng.randint(20, 100),
        "逼格": rng.randint(20, 100),
        "烟火气": rng.randint(20, 100),
    }


def daily_candidates(rng):
    """每天 3 张候选照片。"""
    names = rng.sample(PHOTO_NAMES, 3)
    return [make_photo(rng, n) for n in names]


def validate(photo, slot):
    if not isinstance(photo, dict) or any(
        k not in photo for k in ("name", "颜值", "逼格", "烟火气")
    ):
        raise IllegalMove("照片数据不合法")
    if slot not in SLOTS:
        raise IllegalMove("发布时间只能是 1/2/3")
    for dim in ("颜值", "逼格", "烟火气"):
        v = photo[dim]
        if not isinstance(v, int) or not 0 <= v <= 100:
            raise IllegalMove("照片维度必须是 0~100 的整数")


def base_likes(photo, slot):
    """不计事件的基础点赞数（整数精确计算）。"""
    validate(photo, slot)
    _, boosted = SLOTS[slot]
    total = 0
    for gname, (size, weights) in GROUPS.items():
        contrib = (
            size
            * (
                weights["颜值"] * photo["颜值"]
                + weights["逼格"] * photo["逼格"]
                + weights["烟火气"] * photo["烟火气"]
            )
            // 100
        )
        if gname == boosted:
            contrib = contrib * 3 // 2
        total += contrib
    return total


def roll_event(rng):
    """掷每日随机事件，返回 (事件键, 备注文案)。"""
    r = rng.random()
    if r < 0.10:
        return ("hot", "🔥 被赞爆了！上了热门，赞数 x2")
    if r < 0.18:
        return ("overps", "💥 P 过头被认出来了，社死！本条赞数清零")
    if r < 0.30:
        return ("boss", "😱 忘屏蔽老板，emo 了，赞数 x0.5")
    return ("none", "（风平浪静）")


def play_day(rng, photo, slot):
    """结算一天，返回 (当天赞数, 事件文案)。"""
    base = base_likes(photo, slot)
    event, text = roll_event(rng)
    if event == "hot":
        likes = base * 2
    elif event == "overps":
        likes = 0
    elif event == "boss":
        likes = base // 2
    else:
        likes = base
    return likes, text


def settle(total):
    """按 7 天总赞数授称号，返回 (称号, 评语)。"""
    if total >= MAX_TOTAL * 50 // 100:
        return ("朋友圈之王", "7 天屠榜！建议出书《点赞学》，第一章就叫《集赞数就是 GDP》。")
    if total >= MAX_TOTAL * 30 // 100:
        return ("点赞收割机", "稳定输出，朋友圈的 GDP 担当，广告商已经在路上了。")
    if total >= MAX_TOTAL * 12 // 100:
        return ("透明人", "发了，但好像没发。下次试试分组可见，至少有人好奇。")
    return ("分组可见受害者", "建议检查一下是不是被屏蔽了（不是，是真的没人看）。")


def auto_choose(rng, candidates):
    """AI：按期望基础点赞选最优 (照片下标, 时段)。"""
    best = None
    for i, photo in enumerate(candidates):
        for slot in SLOTS:
            score = base_likes(photo, slot)
            if best is None or score > best[0]:
                best = (score, i, slot)
    return best[1], best[2]


def run_game(rng, chooser, verbose=False):
    """跑完 7 天。chooser(day, candidates) -> (photo_idx, slot)。"""
    total = 0
    log = []
    for day in range(1, DAYS + 1):
        candidates = daily_candidates(rng)
        idx, slot = chooser(day, candidates)
        if not 0 <= idx < len(candidates):
            raise IllegalMove("照片编号越界")
        photo = candidates[idx]
        likes, event_text = play_day(rng, photo, slot)
        total += likes
        slot_name, _ = SLOTS[slot]
        line = (
            f"第 {day} 天：发《{photo['name']}》"
            f"（颜值{photo['颜值']}/逼格{photo['逼格']}/烟火气{photo['烟火气']}）"
            f"于{slot_name}，{event_text}，获赞 {likes}"
        )
        log.append(line)
        if verbose:
            print(line)
    title, comment = settle(total)
    if verbose:
        print(f"\n7 天总赞数：{total}，称号：{title}\n{comment}")
    return total, title, comment, log


def auto_chooser(rng):
    def choose(day, candidates):
        return auto_choose(rng, candidates)

    return choose


def interactive_chooser(day, candidates):
    print(f"\n—— 第 {day} 天：今日 3 张候选 ——")
    for i, p in enumerate(candidates, 1):
        print(f"  {i}. 《{p['name']}》 颜值{p['颜值']} / 逼格{p['逼格']} / 烟火气{p['烟火气']}")
    try:
        idx = int(input("发第几张？(1-3) ").strip()) - 1
        slot = int(input("什么时候发？(1=早上8点 2=中午12点 3=晚上9点) ").strip())
    except (ValueError, EOFError):
        raise IllegalMove("输入不合法，请输入数字")
    return idx, slot


def main(argv=None):
    parser = argparse.ArgumentParser(description="朋友圈摄影大赛模拟器：7 天假期，集赞数就是 GDP")
    parser.add_argument("--auto", action="store_true", help="AI 自动游玩演示")
    parser.add_argument("--games", type=int, default=1, help="自动演示局数")
    parser.add_argument("--seed", type=int, default=None, help="随机种子")
    parser.add_argument("--verbose", action="store_true", help="打印每日战报")
    args = parser.parse_args(argv)

    if args.games < 1:
        parser.error("--games 必须 >= 1")

    if args.auto:
        rng = random.Random(args.seed)
        titles = {}
        for g in range(args.games):
            total, title, comment, _ = run_game(rng, auto_chooser(rng), verbose=args.verbose)
            titles[title] = titles.get(title, 0) + 1
            if args.verbose and args.games > 1:
                print(f"--- 第 {g + 1} 局结束：{total} 赞，{title} ---")
        if args.games > 1:
            print(f"\n共 {args.games} 局，称号分布：")
            for t, c in titles.items():
                print(f"  {t}：{c} 局")
        return 0

    if not sys.stdin.isatty():
        print("交互模式需要终端输入；非终端请用 --auto 自动演示。", file=sys.stderr)
        return 2
    rng = random.Random(args.seed)
    total, title, comment, _ = run_game(rng, interactive_chooser, verbose=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
