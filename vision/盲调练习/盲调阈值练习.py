# ============================================================
# 盲调阈值练习  ——  考核前练"手感"的那支脚本
#
# 干什么：
#   随机抽一张照片，用系统看图工具弹给你看（这次不显示文件名，别靠名字猜），
#   你只凭眼睛报一个阈值，脚本立刻回答两件事：
#       ① 这条线切下去，"白/亮"的像素占百分之多少
#       ② 出一张 4 格对比图：原图灰度 | 阈值-30 | 你报的 | 阈值+30
#   练的是赛场上那句话："看一眼就知道线该画在哪"。
#   注意：阈值没有唯一正确答案 —— 取决于你想让画面里的什么留下。
#
# 怎么用（双击 开始盲调练习.cmd 也行）：
#   照片放进   盲调练习\照片\   （今晚拍的色块/锥桶就丢这里，越陌生越有用）
#   对比图落在 盲调练习\输出\
#   每次报的数字记进 盲调练习\练习记录.txt（哪张练过、报了多少、结果多少）
#
#   python 盲调阈值练习.py -n    → 不弹看图窗口（只想看数字时用）
# ============================================================

import os
import sys
import random
import datetime
from PIL import Image, ImageOps, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
照片目录 = os.path.join(HERE, "照片")
输出目录 = os.path.join(HERE, "输出")
记录文件 = os.path.join(HERE, "练习记录.txt")
不弹窗 = "-n" in sys.argv
字体路径 = r"C:\Windows\Fonts\msyh.ttc"

格宽 = 320
标签高 = 34


def 找照片():
    if not os.path.isdir(照片目录):
        return []
    return sorted(f for f in os.listdir(照片目录)
                  if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")))


def 读已练过():
    练过 = set()
    if os.path.exists(记录文件):
        with open(记录文件, encoding="utf-8") as f:
            for 行 in f:
                段 = [x.strip() for x in 行.split("|")]
                if len(段) >= 2 and 段[1]:
                    练过.add(段[1])
    return 练过


def 记一笔(名字, 阈值, 占比, 平均, 中位):
    新文件 = not os.path.exists(记录文件)
    with open(记录文件, "a", encoding="utf-8") as f:
        if 新文件:
            f.write("# 时间 | 照片 | 我报的阈值 | 白/亮占比 | 这张图平均亮度 | 中位亮度\n")
        时间 = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        f.write(时间 + " | " + 名字 + " | " + str(阈值) + " | "
                + str(round(占比, 1)) + "% | " + str(平均) + " | " + str(中位) + "\n")


def 白占比(灰度图, 阈值):
    """亮度 >= 阈值的格子算"白"，返回它们占全图的百分比。"""
    阈值 = max(0, min(255, int(阈值)))
    直方图 = 灰度图.histogram()
    总数 = 灰度图.width * 灰度图.height
    return sum(直方图[阈值:]) / 总数 * 100


def 平均和中位(灰度图):
    直方图 = 灰度图.histogram()
    总数 = 灰度图.width * 灰度图.height
    平均 = sum(亮度 * 个数 for 亮度, 个数 in enumerate(直方图)) / 总数
    累计 = 0
    for 亮度, 个数 in enumerate(直方图):
        累计 += 个数
        if 累计 >= 总数 / 2:
            return round(平均), 亮度
    return round(平均), 0


def 做对比图(灰度图, 阈值):
    小图 = 灰度图.copy()
    小图.thumbnail((格宽, 格宽 * 2))          # 只为看得清，不改判断逻辑
    标签们 = ["原图灰度", "阈值 " + str(阈值 - 30), "你报的 " + str(阈值), "阈值 " + str(阈值 + 30)]
    阈值们 = [None, 阈值 - 30, 阈值, 阈值 + 30]

    拼图 = Image.new("L", (小图.width * 4, 小图.height + 标签高), 0)
    画 = ImageDraw.Draw(拼图)
    try:
        字体 = ImageFont.truetype(字体路径, 20)
    except Exception:
        字体 = ImageFont.load_default()

    for 序号, (标签, 这条线) in enumerate(zip(标签们, 阈值们)):
        x = 小图.width * 序号
        if 这条线 is None:
            拼图.paste(小图, (x, 标签高))
        else:
            线 = max(0, min(255, int(这条线)))
            二值 = 小图.point(lambda 像素, k=线: 255 if 像素 >= k else 0)
            拼图.paste(二值, (x, 标签高))
        画.text((x + 8, 8), 标签, fill=255, font=字体)
    return 拼图


def 评级(占比):
    if 占比 >= 95:
        return "切得太低了：整张图几乎全白，画面里的东西都被淹没了"
    if 占比 >= 70:
        return "偏松：留了很多白 —— 看对比图，白里是不是把要认的东西也吞了"
    if 占比 <= 5:
        return "太高了：几乎什么都不留（一片黑），等于没切出东西"
    if 占比 <= 30:
        return "偏紧：只留下很少一部分 —— 想要的东西是不是也被切掉了"
    return "中等：画面里有黑有白，像能切开的样子 —— 具体对不对看对比图"


def main():
    照片们 = 找照片()
    print("")
    print("========== 盲调阈值练习 ==========")
    print("照片目录：" + 照片目录)
    if not 照片们:
        print("这个文件夹里还没有照片 —— 先把照片放进 " + 照片目录)
        return
    练过 = 读已练过()
    未练 = [f for f in 照片们 if f not in 练过]
    池子 = 未练 if 未练 else 照片们
    print("照片 " + str(len(照片们)) + " 张，其中没练过的 " + str(len(未练)) + " 张"
          + ("（都练过了，随机重来一遍）" if not 未练 else ""))
    print("规则：图弹出来你自己看 → 回来输一个 0~255 的阈值 → 我立刻算给你看")
    print("按键：p = 再看一眼这张图    q = 退出")
    print("==================================")

    第几张 = 0
    上一张 = None
    while True:
        第几张 += 1
        if len(池子) > 1 and 上一张 is not None:
            可选 = [f for f in 池子 if f != 上一张]
        else:
            可选 = 池子
        名字 = random.choice(可选)
        上一张 = 名字
        路径 = os.path.join(照片目录, 名字)

        灰度图 = ImageOps.exif_transpose(Image.open(路径)).convert("L")
        平均, 中位 = 平均和中位(灰度图)

        print("")
        print("---- 第 " + str(第几张) + " 张 ----")
        if 不弹窗:
            print("（-n 模式：没弹窗，图就是 " + 名字 + "）")
        else:
            print("图弹出来了（这次不告诉你文件名）—— 看清楚它，然后回到这个窗口。")
            try:
                os.startfile(路径)
            except Exception as 错:
                print("图没能自己弹出来（" + str(错) + "），自己去这个文件夹点开看：" + 照片目录)

        while True:
            回答 = input("你报的阈值是多少？（0~255，p 再看一次，q 退出）：").strip()
            if 回答.lower() == "q":
                print("")
                print("今天就到这儿。记录都在：" + 记录文件)
                return
            if 回答.lower() == "p":
                if not 不弹窗:
                    try:
                        os.startfile(路径)
                    except Exception:
                        pass
                continue
            if 回答.isdigit() and 0 <= int(回答) <= 255:
                我报的 = int(回答)
                break
            print("  要输 0~255 之间的一个整数，比如 120")

        占比 = 白占比(灰度图, 我报的)
        print("")
        print("  你报 " + str(我报的) + " → 亮度 >= " + str(我报的) + " 的格子占整张的 "
              + str(round(占比, 1)) + "%")
        print("  这张图：平均亮度 " + str(平均) + "，中位亮度 " + str(中位) + "（255 是全白）")
        print("  " + 评级(占比))

        print("")
        print("  同一张图换个阈值，白就多一片 / 少一片：")
        线们 = list(range(20, 241, 20))
        print("      阈值  " + "".join("%5d" % 线 for 线 in 线们))
        print("    白占比% " + "".join("%5.1f" % 白占比(灰度图, 线) for 线 in 线们))
        print("    （你报的 " + str(我报的) + " 落在上面哪两档之间，白占比就该在它们之间）")

        对比图 = 做对比图(灰度图, 我报的)
        os.makedirs(输出目录, exist_ok=True)
        存到 = os.path.join(输出目录, "盲调_" + os.path.splitext(名字)[0]
                            + "_报" + str(我报的) + ".png")
        对比图.save(存到)
        print("")
        print("  对比图（原图 | 阈值-" + str(30) + " | 你报的 | 阈值+" + str(30) + "）已存：")
        print("  " + 存到)
        if not 不弹窗:
            try:
                os.startfile(存到)
            except Exception:
                pass

        记一笔(名字, 我报的, 占比, 平均, 中位)

        print("")
        print("  看完对比图问自己一句：我想要的那个东西，在这条线上是白还是黑？")
        再 = input("  继续下一张？（回车继续 / q 退出）：").strip()
        if 再.lower() == "q":
            print("")
            print("今天就到这儿。记录都在：" + 记录文件)
            return


try:
    main()
except KeyboardInterrupt:
    print("")
    print("（按了 Ctrl+C，先停在这儿）")
