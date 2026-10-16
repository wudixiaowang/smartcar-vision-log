# -*- coding: utf-8 -*-
"""第一眼看清"一张图就是一排排数字"：用 numpy + opencv 把一张图读进来。

跑法：双击 run_see_image.cmd（输出会停在屏幕上）
     或在 VS Code 里按 Ctrl+F5
用的是车队视觉的样例照片：code/vision/样例照片/1_顺光.png
"""
import os
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "样例照片", "1_顺光.png")

# 小坑先说清：cv2.imread() 遇到中文路径会读不到（返回 None），
# 中文路径要绕一下 —— 先把文件读成字节，再让 cv2 解成图。
img = cv2.imdecode(np.fromfile(IMG, dtype=np.uint8), cv2.IMREAD_COLOR)

print("=" * 52)
print("把一张图读成一排排数字")
print("=" * 52)
print("读的是：", IMG)
print()

print("1) img.shape =", img.shape, "  <- (高, 宽, 通道)")
print("   也就是 480 行 × 640 列，每格 3 个数字（蓝、绿、红）")
print()

print("2) 最左上角那一格 img[0, 0] =", img[0, 0])
print("   一格就是一个像素，里面装着 3 个数字")
print()

print("3) 正中间那一格 img[240, 320] =", img[240, 320])
print()

print("4) 最上面一行最左边 8 格的蓝值 img[0, 0:8, 0] =")
print("   ", img[0, 0:8, 0])
print("   这就是你会写的切片 —— 从这一行里掐出 8 格来看")
print()

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
print("5) 变灰后 gray.shape =", gray.shape, "  <- 每格只剩 1 个数字")
print("   正中间那一格 gray[240, 320] =", gray[240, 320])
print()

# 阈值：亮度大于 150 的当白色，其余当黑色。
# 你在 Python 课里写的 for + if + append，opencv 这一步一次把所有格子都做完。
bright = gray > 150
print("6) 亮度大于 150 的格子有", int(bright.sum()), "个")
print("   占全图", round(float(bright.mean()) * 100, 2), "%  <- 这个数就是调阈值时盯着的数")
print()

th_img = bright.astype(np.uint8) * 255          # 255 = 白，0 = 黑
out = os.path.join(HERE, "out_二值图.png")
cv2.imencode(".png", th_img)[1].tofile(out)     # 中文路径存图也用这一招
print("7) 二值图存好了：", out)
print("   打开它看一眼：亮的地方存住了，暗的地方没了")
print()
print("一句话：一张图 = 一大面数字；处理图像 = 对这些数字做加减比较。")
