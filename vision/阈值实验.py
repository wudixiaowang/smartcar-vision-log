# ============================================================
# 阈值实验  ——  视觉方向第 1 个“能看见东西”的练手脚本
#
# 干什么：
#   把一张照片转成灰度（只留明暗，0=纯黑，255=纯白），
#   再用 4 个不同的阈值把它切成黑/白两半，
#   你会看到：阈值高一点，机器眼里的世界就多一片“白”。
#   赛场调参数，调的就是这个旋钮。
#
# 怎么用（也可以直接双击 运行阈值实验.cmd）：
#   python 阈值实验.py                  处理同目录下的“样例照片”文件夹
#   python 阈值实验.py 某个文件夹        处理你自己手机拍的那三张照片
#   python 阈值实验.py 一张照片.jpg      只处理这一张
#
# 你会得到：
#   屏幕上每个图片 3 行字：尺寸 / 平均亮度 / 4 个阈值下“白”占多少
#   图片同级的“阈值实验输出”文件夹里，一张对比图：
#        原图灰度 | 阈值60 | 阈值100 | 阈值140 | 阈值180
# ============================================================

import os
import sys
from PIL import Image, ImageOps

阈值表 = [60, 100, 140, 180]   # 要试的 4 个阈值，随便改这一行就能重做实验
每格宽度 = 300                  # 手机照片动辄几千像素，缩到这个宽度再拼一起才看得清


def 处理一张(图片路径, 输出目录):
    # exif_transpose：手机竖着拍的照片文件里躺着横图 + 一个"请转 90°"的标记，这一句把它摆正
    图 = ImageOps.exif_transpose(Image.open(图片路径)).convert("L")   # L = 灰度模式：颜色全部丢掉，只留 0~255 的明暗
    直方图 = 图.histogram()                    # 256 个格子；直方图[100] 就是“亮度正好 100”的像素个数
    总像素 = 图.width * 图.height
    平均亮度 = sum(亮度 * 个数 for 亮度, 个数 in enumerate(直方图)) / 总像素

    print("")
    print("--- " + os.path.basename(图片路径) + "  " + str(图.width) + "x" + str(图.height)
          + "  平均亮度 " + str(round(平均亮度)) + "/255 ---")

    小图 = 图.copy()
    小图.thumbnail((每格宽度, 每格宽度 * 2))      # 等比缩小，只为拼图好看，不改判断逻辑
    小格 = 小图.width

    拼图 = Image.new("L", (小格 * (len(阈值表) + 1), 小图.height), 0)
    拼图.paste(小图, (0, 0))                      # 第 1 格：原图灰度

    for 序号, 阈值 in enumerate(阈值表):
        二值图 = 小图.point(lambda 像素, t=阈值: 255 if 像素 >= t else 0)
        白像素占比 = 二值图.histogram()[255] / (小格 * 小图.height) * 100
        print("    阈值 " + str(阈值).rjust(3) + " ： 被判成“白/亮”的像素占 "
              + str(round(白像素占比, 1)) + "%")
        拼图.paste(二值图, (小格 * (序号 + 1), 0))

    os.makedirs(输出目录, exist_ok=True)
    名字 = os.path.splitext(os.path.basename(图片路径))[0]
    存到 = os.path.join(输出目录, "对比_" + 名字 + ".png")
    拼图.save(存到)
    print("    对比图已存：" + 存到)


def main():
    if len(sys.argv) > 1:
        目标 = sys.argv[1]
    else:
        目标 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "样例照片")

    if not os.path.exists(目标):
        print("找不到这个路径：" + 目标)
        return

    print("对比图从左到右依次是：原图灰度 / " + " / ".join("阈值" + str(t) for t in 阈值表))

    if os.path.isdir(目标):
        输出目录 = os.path.join(目标, "阈值实验输出")
        图片们 = [f for f in sorted(os.listdir(目标))
                  if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))]
        if not 图片们:
            print("这个文件夹里没有图片：" + 目标)
            return
        for 名字 in 图片们:
            处理一张(os.path.join(目标, 名字), 输出目录)
    else:
        处理一张(目标, os.path.join(os.path.dirname(目标), "阈值实验输出"))

    print("")
    print("同一张图、同一件事，只换阈值，被判成“白”的比例差这么多 —— 这就是临场要调的那个旋钮。")


main()
