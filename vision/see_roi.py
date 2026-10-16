# -*- coding: utf-8 -*-
"""第二支视觉脚本：ROI —— 只切出"车真正要看的那一块"。

跑法：双击 run_see_roi.cmd（输出会停在屏幕上）
上一支 see_image.py 看清了一件事：一张图 = 480 行 × 640 列的数字墙。
这一支学车队每天真在干的事：整张图不看，只掐出画面中间那一小块（ROI）。
"""

import os
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "样例照片", "1_顺光.png")

# 中文路径的老坑：cv2 读不了中文路径，先读成字节再解成图。
img = cv2.imdecode(np.fromfile(IMG, dtype=np.uint8), cv2.IMREAD_COLOR)

print("=" * 56)
print("ROI：从数字墙上只切一块下来")
print("=" * 56)
print("读的是：", IMG)
print()

print("1) 整张图 img.shape =", img.shape, "  <- (高, 宽, 通道)")
h, w = img.shape[0], img.shape[1]
print("   也就是", h, "行 ×", w, "列 =", h * w, "个像素")
print()

print("2) 先复习一维切片：从【一行里】掐出 8 格")
print("   img[0, 0:8, 0] =", img[0, 0:8, 0])
print()

print("3) 今天升级成二维切片：从【整面墙】里掐出【一块】")
print("   写法：img[从哪行 : 到哪行 , 从哪列 : 到哪列]")
roi = img[240:480, 200:560]
print("   roi = img[240:480, 160:480]")
print("   roi.shape =", roi.shape, "  <- 高", roi.shape[0], "× 宽", roi.shape[1], "，通道数没变")
print("   跟 s[0:3] 一个规矩：含开始、不含结束 —— 240:480 是第 240 行到第 479 行。")
print()

print("4) 切出来的 roi 自己也是一张图、也是一面数字墙：")
print("   roi[0, 0]       =", roi[0, 0], "  (蓝, 绿, 红)")
print("   roi[120, 160]   =", roi[120, 160], "  <- 这块的正中间")
print()

print("5) 为什么要切？车上摄像头拍一整幅，但车道只在画面中间那一条带子里。")
print("   整张图要算", h * w, "格；只算 roi 只要算", roi.shape[0] * roi.shape[1], "格")
print("   少算", h * w - roi.shape[0] * roi.shape[1], "格 —— 帧率就是这么省出来的。")
print()

# 同一个阈值，整图 vs 只算 ROI，白占比差多少？
th = 150
gray_all = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
pct_all = round(float((gray_all > th).mean()) * 100, 2)
pct_roi = round(float((gray_roi > th).mean()) * 100, 2)
print("6) 同一个阈值", th, "，白像素占比：")
print("   整张图  > ", th, " 的占", pct_all, "%")
print("   只算 roi > ", th, " 的占", pct_roi, "%")
print("   同一个数，换个范围结果就变了 —— 这就是赛场必须现场标定的原因。")
print()

out_roi = os.path.join(HERE, "out_roi色块.png")
cv2.imencode(".png", roi)[1].tofile(out_roi)
th_roi = (gray_roi > th).astype(np.uint8) * 255
out_bin = os.path.join(HERE, "out_roi二值图.png")
cv2.imencode(".png", th_roi)[1].tofile(out_bin)
print("7) 存好了两张，打开看一眼：")
print("   ", out_roi, "  <- 只切下来的那一块")
print("   ", out_bin, "     <- 这一块按亮度 150 切开的样子")
print()
print("一句话：整张图不看，只切要看的那一块 —— 这就是 ROI，车队代码里天天出现。")
print()

# ========== 现在轮到你了（只做一件事）==========
# 往上看一点，找到这一行（文件里第 36 行）：
#     roi = img[240:480, 160:480]
# 把里面【列】的那两个数 160 和 480 改成 200 和 520（就动这两个数，别的都别碰）。
# 先猜一件事：屏幕 6) 里 roi 的白占比会变大还是变小？
# 再 Ctrl+S 保存、双击 run_see_roi.cmd，把屏幕上【6) 那两行】的数字贴给我。

