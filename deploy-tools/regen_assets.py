"""把 _new_assets/ 里的 AI 原图批量整理成示例作品需要的素材。

尺寸严格对齐原有素材，避免造型框变化影响角色的旋转中心与碰撞逻辑。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEW = os.path.join(ROOT, '_new_assets')
OUT = os.path.join(ROOT, '_processed_assets')
SCRIPT = os.path.join(ROOT, 'ai-scratch-maker', 'scripts', 'prep_asset.py')

# (原图文件名片段, 输出文件名, 模式参数, 是否抠背景, 是否生成镜像, 是否裁水印)
JOBS = [
    ('orange_tabby_ca', 'cat.png',   ['--mode', 'custom', '--width', '268', '--height', '300'], True, True, False),
    ('grey_mouse__sta', 'mouse.png', ['--mode', 'custom', '--width', '185', '--height', '240'], True, True, False),
    ('sofa__th',        '沙发.png',  ['--mode', 'custom', '--width', '180', '--height', '100'], True, False, False),
    ('wooden_c_2026-11-04T16-23-08', '柜子.png', ['--mode', 'custom', '--width', '180', '--height', '110'], True, False, False),
    ('wooden_c_2026-11-04T16-23-33', '书桌.png', ['--mode', 'custom', '--width', '200', '--height', '130'], True, False, False),
    ('round_fl',        '地毯.png',  ['--mode', 'custom', '--width', '200', '--height', '160'], True, False, False),
    # 背景不抠，裁填铺满；但要先裁掉右下角工具强制水印
    ('Wide_establishing', 'bigmap.png',   ['--mode', 'custom', '--width', '960', '--height', '720', '--fill'], False, False, True),
    ('Game_title_screen', 'title_bg.png', ['--mode', 'custom', '--width', '480', '--height', '360', '--fill'], False, False, True),
]


def find_src(frag):
    hits = [f for f in os.listdir(NEW) if frag in f and f.endswith('.png')]
    if len(hits) != 1:
        raise SystemExit('原图匹配数异常 (%s): %s' % (frag, hits))
    return os.path.join(NEW, hits[0])


def run(args):
    r = subprocess.run([sys.executable, SCRIPT] + args,
                       capture_output=True, text=True)
    ok = r.stdout.startswith('OK')
    print(('  OK   ' if ok else '  FAIL ') + ' '.join(args[-4:]))
    if not ok:
        print('        ' + (r.stdout + r.stderr).strip()[:300])
    return ok


def overlay_title(path):
    """给 AI 首页背景补上标题文字。

    旧版 title_bg.png 是 make_ui_assets.py 画的，标题烧在背景里；
    换成 AI 插画后文字会丢 —— title_screen 没有单独的标题角色。
    所以这里在浅色半透明底板上叠加主标题 + 副标题，按钮区域保持留空。
    """
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(path).convert('RGBA')
    w, h = im.size
    panel = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle((40, 18, w - 40, 140), radius=28, fill=(255, 252, 242, 205))
    im = Image.alpha_composite(im, panel)
    d = ImageDraw.Draw(im)
    fonts = ['C:/Windows/Fonts/msyhbd.ttc', 'C:/Windows/Fonts/simhei.ttf']
    fp = next((f for f in fonts if os.path.exists(f)), None)
    f1 = ImageFont.truetype(fp, 54) if fp else ImageFont.load_default()
    f2 = (ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 20)
          if os.path.exists('C:/Windows/Fonts/msyh.ttc') else ImageFont.load_default())

    def center(text, y, font, fill, stroke, sw):
        b = d.textbbox((0, 0), text, font=font)
        d.text(((w - (b[2] - b[0])) // 2, y), text, font=font,
               fill=fill, stroke_width=sw, stroke_fill=stroke)

    center('猫抓老鼠', 38, f1, (70, 48, 32), (255, 255, 255), 3)
    center('用方向键控制猫，别让老鼠跑掉', 104, f2, (95, 72, 52), (255, 255, 255), 2)
    im.convert('RGB').save(path, 'PNG', optimize=True)
    print('  OK   首页标题已叠加')


def main():
    os.makedirs(OUT, exist_ok=True)
    fails = 0
    for frag, name, mode, remove_bg, mirror, crop_wm in JOBS:
        src = find_src(frag)
        dst = os.path.join(OUT, name)
        args = ['--in', src, '--out', dst] + mode
        if remove_bg:
            args.append('--remove-bg')
        args += ['--trim', '--hq']
        if crop_wm:
            args.append('--crop-watermark')
        if not run(args):
            fails += 1
            continue
        if mirror:
            left = os.path.join(OUT, name.replace('.png', '_left.png'))
            # 镜像直接从整理好的成品翻，不再重复抠图/缩放
            args2 = ['--in', dst, '--out', left, '--mode', 'sprite', '--flip-h']
            if not run(args2):
                fails += 1
    title = os.path.join(OUT, 'title_bg.png')
    if os.path.exists(title):
        overlay_title(title)
    print('\n完成，失败 %d 项，输出目录：%s' % (fails, OUT))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
