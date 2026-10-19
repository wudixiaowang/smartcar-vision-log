# -*- coding: utf-8 -*-
"""CPU 上的第一个真训练：让模型看一眼框里的东西，说出它是哪一类。

吃的是你自己标的那批数据（dataset\\images + dataset\\labels），
把每个框裁出来当一张小图，学 3 类：block 方块 / bottle 瓶子 / doll 公仔。

本机没有 CUDA，全程 CPU，一分钟内跑完 —— 这一步的价值是跑通
「读标注 → 裁剪 → 训练 → 看准确率」这条链，不是训出一个能上车的模型。
样本只有几十个，记住这句话：数据太少，模型只会背答案。

双击同目录的 开始训练.cmd 就行。
"""

import os
import glob
import random
import torch
import torch.nn as nn
import numpy as np
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
DS = os.path.join(os.path.dirname(HERE), "dataset")
IMG_DIR = os.path.join(DS, "images")
LBL_DIR = os.path.join(DS, "labels")
模型路径 = os.path.join(HERE, "小分类器.pt")

类别名 = ["block", "doll", "bottle"]        # 本次训练用的顺序（cone 一个框都没有）
# dataset\labels 里的类别号是 0=block 1=cone 2=doll 3=bottle，
# 这里换成 0=block 1=doll 2=bottle，中间不留空位
类别号对照 = {0: 0, 2: 1, 3: 2}
尺寸 = 64
随机种子 = 20261019

random.seed(随机种子)
torch.manual_seed(随机种子)


def 读框(txt, w, h):
    """YOLO txt → 像素框列表 [(类别号, x1, y1, x2, y2)]"""
    out = []
    if not os.path.exists(txt):
        return out
    with open(txt, encoding="utf-8") as f:
        for line in f:
            p = line.split()
            if len(p) < 5:
                continue
            c = int(float(p[0]))
            cx, cy, bw, bh = (float(x) for x in p[1:5])
            x1 = max(0, int((cx - bw / 2) * w)); y1 = max(0, int((cy - bh / 2) * h))
            x2 = min(w, int((cx + bw / 2) * w)); y2 = min(h, int((cy + bh / 2) * h))
            if x2 - x1 > 8 and y2 - y1 > 8:
                out.append((c, x1, y1, x2, y2))
    return out


def 收集样本():
    """每张照片先转正（手机竖拍带 EXIF 旋转），再按框裁出来，缩到 64×64。"""
    样本 = []
    for img_path in sorted(glob.glob(os.path.join(IMG_DIR, "*.jpg"))):
        名 = os.path.splitext(os.path.basename(img_path))[0]
        im = ImageOps.exif_transpose(Image.open(img_path)).convert("RGB")
        w, h = im.size
        for c, x1, y1, x2, y2 in 读框(os.path.join(LBL_DIR, 名 + ".txt"), w, h):
            if c not in 类别号对照:
                continue
            图 = im.crop((x1, y1, x2, y2)).resize((尺寸, 尺寸))
            样本.append((图, 类别号对照[c]))
    return 样本


def 成张量(图, 翻转=False, 亮度=1.0):
    if 翻转:
        图 = ImageOps.mirror(图)
    if 亮度 != 1.0:
        图 = 图.point(lambda v: min(255, int(v * 亮度)))
    数据 = torch.from_numpy(np.asarray(图, dtype=np.float32).copy()) / 127.5 - 1.0
    return 数据.permute(2, 0, 1).contiguous()          # (高, 宽, 3) → (3, 高, 宽)


class 小网络(nn.Module):
    """三层的小卷积网：看形状和颜色。参数不到 5 千个，纯 CPU 也飞快。"""

    def __init__(self, 类数):
        super().__init__()
        self.特征 = nn.Sequential(
            nn.Conv2d(3, 8, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),     # 64 → 32
            nn.Conv2d(8, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),    # 32 → 16
            nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),   # 16 → 8
            nn.AdaptiveAvgPool2d(1),
        )
        self.判类 = nn.Linear(32, 类数)

    def forward(self, x):
        return self.判类(self.特征(x).flatten(1))


def main():
    print("")
    print("============ CPU 训练小实验 ============")
    print("读标注、裁框、训一个三层小网络（不用显卡，一分钟内）")
    print("")

    样本 = 收集样本()
    if len(样本) < 9:
        print("样本太少（%d 个框），先把 dataset 标起来再跑。" % len(样本))
        return

    统计 = {}
    for _, c in 样本:
        统计[c] = 统计.get(c, 0) + 1
    print("样本总数（框）: %d" % len(样本))
    for c, n in sorted(统计.items()):
        print("    %-7s %2d 个框" % (类别名[c], n))

    # 每一类留最后 2 个当「没训练过的考卷」
    按类 = {}
    for 图, c in 样本:
        按类.setdefault(c, []).append((图, c))
    训练集, 测试集 = [], []
    for c, 列表 in 按类.items():
        random.shuffle(列表)
        测试集 += 列表[:max(1, len(列表) // 5)]
        训练集 += 列表[max(1, len(列表) // 5):]
    print("")
    print("拿去学的 %d 个框，留着考它的 %d 个框（这些它一次都没见过）" % (len(训练集), len(测试集)))

    网络 = 小网络(len(类别名))
    优化器 = torch.optim.Adam(网络.parameters(), lr=0.01)
    损失函数 = nn.CrossEntropyLoss()
    参数数 = sum(p.numel() for p in 网络.parameters())
    print("网络参数: %d 个" % 参数数)
    print("")

    X = torch.stack([成张量(g) for g, _ in 训练集])
    y = torch.tensor([c for _, c in 训练集])

    for 轮 in range(1, 121):
        网络.train()
        # 每一轮把顺序打乱一遍（同一个框换个位置进批次），这是最基本的做法
        批次 = torch.randperm(len(X))
        Xb = X[批次]
        yb = y[批次]
        优化器.zero_grad()
        输出 = 网络(Xb)
        损失 = 损失函数(输出, yb)
        损失.backward()
        优化器.step()

        if 轮 % 20 == 0 or 轮 == 1:
            网络.eval()
            with torch.no_grad():
                训练正确 = (网络(X).argmax(1) == y).float().mean().item() * 100
            print("  第 %3d 轮   损失 %.4f   训练集准确率 %5.1f%%" % (轮, 损失.item(), 训练正确))

    # 考卷：留出的那些框，一次没学过
    网络.eval()
    对 = 0
    明细 = []
    with torch.no_grad():
        for 图, c in 测试集:
            预测 = int(网络(成张量(图).unsqueeze(0)).argmax(1).item())
            对 += (预测 == c)
            明细.append("%s %s%s" % ("√" if 预测 == c else "×", 类别名[c],
                                     "" if 预测 == c else " → 认成 " + 类别名[预测]))
    print("")
    print("留出的考卷 %d 个框，认对 %d 个（%.0f%%）" % (len(测试集), 对, 对 / len(测试集) * 100))
    for 行 in 明细:
        print("    " + 行)

    torch.save({"参数": 网络.state_dict(), "类别名": 类别名}, 模型路径)
    print("")
    print("模型存到: " + 模型路径)
    print("")
    print("读这张结果之前记住两句：")
    print("    ① 只有 %d 个框，它的成绩不代表真有本事 —— 换一只别的瓶子它很可能就认错；" % len(样本))
    print("    ② 这一步真正的收获是流程：标注 → 裁剪 → 训练 → 用没见过的图考它。")
    print("")


if __name__ == "__main__":
    main()
