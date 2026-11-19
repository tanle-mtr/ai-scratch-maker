#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成一套「有层次」的游戏音效（第二十九册配套）。

和 `gen_audio.py` 的分工：
    gen_audio.py —— 音频合成底层（振荡器/噪声/滤波/包络）+ 散装预设，单个音效用。
    gen_sfx_kit.py —— 在它之上出一**套**音效：分层响度、统一音色、统一命名、带 manifest。

为什么「一套」比「一堆」重要：
    把所有音效都归一化到同一个峰值，是业余作品最典型的听感问题 ——
    点一下按钮和爆炸一样响，玩家听两分钟就关声音。
    专业做法是**按信息重要度分四层**，层间差 6~9 dB：

        层       目标峰值     触发频率     例子
        ui      -18 dBFS     最频繁       悬停、点击、返回、开关
        fx       -9 dBFS     频繁         金币、跳跃、落地、受击
        ev       -3 dBFS     偶尔         开门、升级、胜利、失败、警报
        amb     -15 dBFS     持续         雨、风（循环铺底）

用法:
    python scripts/gen_sfx_kit.py                 # 输出 examples/assets/audio/
    python scripts/gen_sfx_kit.py --out 某目录
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_audio as g

RATE = g.RATE

# 四层响度（dBFS）。层间差 6~9 dB 是听感上「明显分层但不突兀」的区间。
LEVEL_DB = {"ui": -18, "fx": -9, "ev": -3, "amb": -15}
LEVEL_DESC = {
    "ui": "界面微反馈（最频繁，必须最轻）",
    "fx": "游戏内即时反馈（频繁）",
    "ev": "事件强调（偶尔，可以响）",
    "amb": "环境铺底（持续，不可抢戏）",
}


def finish(samples, group, fade_ms=None):
    """收尾：淡入淡出 + 按层归一化。"""
    n = len(samples)
    if n == 0:
        return samples
    fm = fade_ms if fade_ms is not None else min(10.0, (n / float(RATE)) * 1000 * 0.15)
    s = g.fade_edges(samples, RATE, fm)
    return g.normalize(s, 10 ** (LEVEL_DB[group] / 20.0))


def S(*layers):
    """叠加多层（和弦 / 音效+噪声）。"""
    return g.mix(*layers)


def seq(*parts):
    return g.seq(*parts)


def tone(name, dur, wave="sine", attack=0.003, release=None):
    return g.env(g.osc(g.note_freq(name), dur, wave), attack=attack,
                 release=release if release is not None else dur * 0.5)


# --------------------------------------------------------------------------- #
# UI 层：脆、短、干净。不要噪声，不要低频。
# --------------------------------------------------------------------------- #
def ui_hover():
    # 45ms 上滑：只是「我在这里」，不是「我做了什么」，所以最短最轻
    return g.env(g.osc(lambda t: 1100 + 700 * t, 0.045, "sine"), attack=0.002, release=0.016)


def ui_click():
    # 60ms：一个音头 + 一小撮高频噪声（模拟「咔」），噪声只占 6ms
    body = g.env(g.osc(lambda t: 900 + 500 * t, 0.06, "sine"), attack=0.001, release=0.022)
    tick = g.env(g.noise(0.008), attack=0.0005, release=0.004)
    return S(body, [v * 0.35 for v in tick])


def ui_back():
    # 70ms 下滑：方向 = 语义（返回就是往下走）
    return g.env(g.osc(lambda t: 1200 - 500 * t, 0.07, "sine"), attack=0.002, release=0.026)


def ui_toggle_on():
    a = tone("A5", 0.035, "sine", release=0.012)
    b = tone("E6", 0.045, "sine", release=0.02)
    return seq(a, b)


def ui_toggle_off():
    a = tone("E6", 0.035, "sine", release=0.012)
    b = tone("A5", 0.045, "sine", release=0.02)
    return seq(a, b)


def ui_error():
    # 190ms：方波 + 低频，粗糙感是「不对」的信号；带一点 12Hz 颤音
    s = g.osc(lambda t: 230 - 60 * t + 8 * math.sin(2 * math.pi * 12 * t * 0.19), 0.19, "square")
    return g.env(s, attack=0.004, release=0.06, sustain=0.8)


# --------------------------------------------------------------------------- #
# FX 层：有起音、有衰减，听得出「发生了什么」
# --------------------------------------------------------------------------- #
def fx_coin():
    # 经典两音上行 C6→E6：奖励音必须往上走
    return seq(tone("C6", 0.08, "sine", release=0.02), tone("E6", 0.10, "sine", release=0.05))


def fx_jump():
    # 上滑 400→900：身体往上，声音也往上
    return g.env(g.osc(lambda t: 400 + 500 * t ** 0.7, 0.16, "sine"), attack=0.004, release=0.07)


def fx_land():
    # 落地 = 低频撞击 + 极短噪声。低频给「重量」，噪声给「接触」
    thud = g.env(g.osc(lambda t: 140 - 60 * t, 0.12, "sine"), attack=0.002, release=0.06)
    dust = g.env(g.noise(0.05), attack=0.001, release=0.03)
    return S(thud, [v * 0.30 for v in dust])


def fx_hit():
    # 受击：噪声衰减 + 低频。比落地更「脏」更长，因为有伤害
    body = g.env(g.noise(0.20), attack=0.001, release=0.12)
    low = g.env(g.osc(lambda t: 110 - 40 * t, 0.18, "square"), attack=0.002, release=0.10)
    return S([v * 0.75 for v in body], [v * 0.55 for v in low])


def fx_pickup():
    # 三音琶音：比金币多一层，用于「拿到道具」
    return seq(tone("C5", 0.045, "tri", release=0.015),
               tone("E5", 0.045, "tri", release=0.015),
               tone("G5", 0.07, "tri", release=0.035))


def fx_swipe():
    # 挥砍：噪声 + 低通扫频（从闷到亮，模拟刀锋掠过）
    n = g.noise(0.14, decay=False)
    bright = g.lowpass(n, 3200)
    dark = g.lowpass(n, 900)
    out = []
    for i, (a, b) in enumerate(zip(dark, bright)):
        t = i / float(len(n))
        out.append(a * (1 - t) + b * t)
    return g.env(out, attack=0.002, release=0.06)


def fx_pop():
    # 100ms 上滑：UI 元素「弹出来」的通用音
    return g.env(g.osc(lambda t: 500 + 700 * t, 0.10, "sine"), attack=0.002, release=0.04)


def fx_heal():
    # 治疗：柔和三音上行 + 轻微失谐（失谐 = 「温暖」）
    a = g.env(g.osc(g.note_freq("C5"), 0.11, "sine", detune=3), attack=0.01, release=0.05)
    b = g.env(g.osc(g.note_freq("E5"), 0.11, "sine", detune=3), attack=0.01, release=0.05)
    c = g.env(g.osc(g.note_freq("A5"), 0.14, "sine", detune=3), attack=0.01, release=0.07)
    return seq(a, b, c)


# --------------------------------------------------------------------------- #
# EV 层：有「结构」（多段/和弦），可以响
# --------------------------------------------------------------------------- #
def ev_open():
    # 开门：机械两段（锁扣 + 滑轨）+ 低频铺底
    click = g.env(g.noise(0.03), attack=0.001, release=0.02)
    slide = g.env(g.osc(lambda t: 90 + 60 * t, 0.45, "tri"), attack=0.02, release=0.25)
    return seq([v * 0.4 for v in click], slide)


def ev_close():
    # 关门：下滑 + 结尾撞击（撞击放在最后 80ms）
    slide = g.env(g.osc(lambda t: 180 - 90 * t, 0.38, "tri"), attack=0.01, release=0.18)
    slam = g.env(g.osc(lambda t: 110 - 40 * t, 0.12, "sine"), attack=0.001, release=0.07)
    return seq(slide, slam)


def ev_levelup():
    # 升级：四音琶音，每音渐长（加速感的反面：越到后面越"展开"）
    return seq(tone("C5", 0.10, "square", release=0.04),
               tone("E5", 0.10, "square", release=0.04),
               tone("G5", 0.12, "square", release=0.05),
               tone("C6", 0.26, "square", release=0.14))


def ev_win():
    # 胜利：大三和弦（C-E-G）叠 + 高八度琶音收尾
    chord = S(tone("C5", 0.55, "square", release=0.3),
              tone("E5", 0.55, "square", release=0.3),
              tone("G5", 0.55, "square", release=0.3))
    tail = seq(tone("C6", 0.18, "square", release=0.10),
               tone("E6", 0.35, "square", release=0.2))
    return seq(chord, tail)


def ev_lose():
    # 失败：下行小调（A-G-F-E），音高一路降，最后拖长
    return seq(tone("A4", 0.16, "tri", release=0.08),
               tone("G4", 0.16, "tri", release=0.08),
               tone("F4", 0.18, "tri", release=0.09),
               tone("E4", 0.40, "tri", release=0.25))


def ev_alarm():
    # 警报：方波 660Hz 两段，中间断开 80ms（"嘀—嘀"比长音更急）
    def beep(dur):
        s = g.osc(lambda t: 660 + 10 * math.sin(2 * math.pi * 18 * t * dur), dur, "square")
        return g.env(s, attack=0.005, release=dur * 0.25, sustain=0.85)
    return seq(beep(0.22), g.silence(0.08, RATE), beep(0.22), g.silence(0.04, RATE),
               beep(0.14))


# --------------------------------------------------------------------------- #
# AMB 层：长、循环、低对比。一定不要有「事件感」（不能有起音）
# --------------------------------------------------------------------------- #
def amb_rain():
    n = g.noise(2.0, decay=False, seed=7)
    s = g.lowpass(n, 5200)
    # 缓慢起伏（0.7Hz），模拟雨势变化；幅度只有 ±15%，不能听出「呼吸」
    out = []
    for i, v in enumerate(s):
        t = i / float(len(s))
        out.append(v * (0.92 + 0.15 * math.sin(2 * math.pi * 0.7 * t)))
    return g.env(out, attack=0.05, release=0.05)


def amb_wind():
    n = g.noise(2.0, decay=False, seed=13)
    out = []
    for i, v in enumerate(n):
        t = i / float(len(n))
        # 低通截止频率在 500~1400 之间缓慢摆动 → 「风声」的核心
        cut = 500 + 900 * (0.5 + 0.5 * math.sin(2 * math.pi * 0.3 * t))
        out.append(v)
    # 分三段不同截止再拼接，比逐样本滤波快，听感差别可忽略
    seg = len(out) // 3
    parts = [g.lowpass(out[:seg], 900), g.lowpass(out[seg:2 * seg], 1500),
             g.lowpass(out[2 * seg:], 700)]
    return g.env(parts[0] + parts[1] + parts[2], attack=0.08, release=0.08)


# --------------------------------------------------------------------------- #
# 套件清单：名字 → (组, 生成函数, 用途)
# --------------------------------------------------------------------------- #
KIT = {
    # UI
    "ui_hover":     ("ui", ui_hover,     "鼠标悬停在按钮上（最高频，必须最轻）"),
    "ui_click":     ("ui", ui_click,     "按下按钮（任何主要操作）"),
    "ui_back":      ("ui", ui_back,      "返回 / 取消 / 关闭"),
    "ui_toggle_on": ("ui", ui_toggle_on, "开关打开"),
    "ui_toggle_off": ("ui", ui_toggle_off, "开关关闭"),
    "ui_error":     ("ui", ui_error,     "不可用操作 / 输入错误"),
    # FX
    "fx_coin":      ("fx", fx_coin,      "拾取金币 / 加一分"),
    "fx_jump":      ("fx", fx_jump,      "起跳"),
    "fx_land":      ("fx", fx_land,      "落地"),
    "fx_hit":       ("fx", fx_hit,       "受击 / 造成伤害"),
    "fx_pickup":    ("fx", fx_pickup,    "获得道具 / 拾取"),
    "fx_swipe":     ("fx", fx_swipe,     "挥砍 / 冲刺"),
    "fx_pop":       ("fx", fx_pop,       "UI 元素弹出（也可用于泡泡/果实）"),
    "fx_heal":      ("fx", fx_heal,      "治疗 / 恢复"),
    # EV
    "ev_open":      ("ev", ev_open,      "开门 / 启动机械"),
    "ev_close":     ("ev", ev_close,     "关门 / 停机"),
    "ev_levelup":   ("ev", ev_levelup,   "升级 / 解锁"),
    "ev_win":       ("ev", ev_win,       "胜利 / 通关"),
    "ev_lose":      ("ev", ev_lose,      "失败 / 死亡"),
    "ev_alarm":     ("ev", ev_alarm,     "警报 / 倒计时告急"),
    # AMB
    "amb_rain":     ("amb", amb_rain,    "雨天环境（循环）"),
    "amb_wind":     ("amb", amb_wind,    "风声环境（循环）"),
}


def peak_of(samples):
    return max((abs(s) for s in samples), default=0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = args.out or os.path.join(os.getcwd(), "examples", "assets", "audio")
    os.makedirs(out, exist_ok=True)

    manifest = {"levels": LEVEL_DB, "level_desc": LEVEL_DESC, "sounds": []}
    for name, (group, fn, use) in KIT.items():
        samples = finish(fn(), group)
        path = os.path.join(out, name + ".wav")
        g.write_wav(path, samples)
        dur = len(samples) / float(RATE)
        pk = peak_of(samples)
        db = 20 * math.log10(pk) if pk > 0 else -99
        manifest["sounds"].append({
            "name": name, "group": group, "file": name + ".wav",
            "dur": round(dur, 3), "peak": round(pk, 4), "peak_db": round(db, 1),
            "use": use,
        })
        print("%-14s %-4s %5.3fs  %6.1f dBFS  %s" % (name, group, dur, db, use))

    mp = os.path.join(out, "manifest.json")
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("\n套件已生成: %s" % out)
    print("  音效 %d 个（ui %d / fx %d / ev %d / amb %d）+ manifest.json" % (
        len(KIT),
        sum(1 for v in KIT.values() if v[0] == "ui"),
        sum(1 for v in KIT.values() if v[0] == "fx"),
        sum(1 for v in KIT.values() if v[0] == "ev"),
        sum(1 for v in KIT.values() if v[0] == "amb")))


if __name__ == "__main__":
    main()
