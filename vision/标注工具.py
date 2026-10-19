# -*- coding: utf-8 -*-
"""fospeed 视觉 · 图片标注小工具（OpenCV 版，v4）

v4 改了什么：
    ① 中文输入法不再吃键盘。以前输入法停在中文状态时，一点进这个窗口，
       D / U / Q 一个都按不动（看着就像卡死）—— 现在窗口一建好就把输入法
       从窗口上摘掉（ImmDisableIME + ImmAssociateContext(hwnd, NULL)）。
    ② 字母键不区分大小写（CapsLock 开着也认），另外 ← → 也能翻上/下一张。
    ③ 手一抖拖出来的迷你框（小于图宽或图高的 6%）直接不保存，免得污染数据。

v3 改了什么（v2 的毛病）：
    ① 去掉了底部滑块 —— 它会被窗口高度顶到屏幕外面（实测窗口 1073 高，工作区只有 1040），
       现在切类别只用数字键，屏幕上大字写着现在是哪一个，不可能再"找不到"。
    ② 图片会按屏幕可用区自动缩放，整张图加状态条一定装得进屏幕。
    ③ 顺手兼容你以前的习惯：D = 下一张，A = 上一张。

怎么用（双击同目录的「打开标注工具.cmd」）：
    按 1 / 2 / 3 / 4 切类别：1=block 色块 · 2=cone 锥桶 · 3=doll 公仔 · 4=bottle 瓶子
    （屏幕上会显示现在选的是哪个；4 是 2026-10-19 加的，家里没胶带卷不出锥，就单独给瓶子一类）
    鼠标左键按住，贴着物体边缘拖一个方框，松手即成框（立刻自动保存）
    D 或 N = 下一张 · A 或 P = 上一张 · U = 撤销上一个框 · C = 清空本张 · Q = 退出 · ← → 也能翻页
    输入法停在中文也没事：这个窗口一建好就把输入法从自己身上摘掉了。按键要是没反应，
    先用鼠标点一下窗口（让它变成最前面那个）再按。

标注存在 dataset\\labels\\，每个 .txt 跟一张照片同名，YOLO 格式：
    类别号 中心x 中心y 宽 高     （四个数都是 0~1 的小数）
"""

import ctypes
import glob
import os
import traceback
from ctypes import wintypes

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(HERE, "dataset", "images")
LBL_DIR = os.path.join(HERE, "dataset", "labels")
CLASSES = ["block", "cone", "doll", "bottle"]                # 0=色块 1=锥桶 2=公仔 3=瓶子
CN_NAMES = ["色块", "锥桶", "公仔", "瓶子"]
FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"                    # 微软雅黑
BAR_H = 62                                                  # 顶部状态条高度
WINDOW_EXTRA_H = 135                                        # 标题栏+边框（没有滑块了），实测 126，留余量

_font = ImageFont.truetype(FONT_PATH, 20)
_font_big = ImageFont.truetype(FONT_PATH, 24)


class _RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


def disable_ime(win_name):
    """把中文输入法从这个窗口上摘掉。

    不摘的话：输入法停在中文状态时，点进窗口按 D/U/Q，键盘事件全被输入法吃掉，
    窗口一个键也收不到 —— 看起来就是「卡死了、按什么都没反应」。
    做两步：ImmDisableIME(-1) 关掉本进程所有线程的输入法；
    ImmAssociateContext(hwnd, NULL) 把窗口和输入法彻底断开。
    返回 True 表示至少认到了窗口（失败也不影响别的功能）。
    """
    u32 = ctypes.windll.user32
    imm = ctypes.WinDLL("imm32.dll")
    hwnd = u32.FindWindowW(None, win_name)
    if not hwnd:                       # 标题没找到就退一步：认本进程自己的窗口
        pid = os.getpid()
        found = []

        def _cb(h, lparam):
            p = wintypes.DWORD()
            u32.GetWindowThreadProcessId(h, ctypes.byref(p))
            if p.value == pid:
                found.append(h)
            return True

        CBF = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        u32.EnumWindows(CBF(_cb), 0)
        if found:
            hwnd = found[0]
    if not hwnd:
        return False
    try:
        imm.ImmDisableIME(ctypes.c_uint(0xFFFFFFFF))     # 0xFFFFFFFF = 本进程所有线程
    except Exception:
        pass
    imm.ImmAssociateContext(hwnd, 0)                      # 0 = 断开输入法
    return True


def work_area():
    """屏幕可用区（已扣掉任务栏）—— 窗口必须整个装得进去。"""
    try:
        r = _RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0):
            return r.right - r.left, r.bottom - r.top
    except Exception:
        pass
    try:
        u = ctypes.windll.user32
        return u.GetSystemMetrics(0), u.GetSystemMetrics(1) - 40
    except Exception:
        return 1920, 1040


WORK_W, WORK_H = work_area()
MAX_H = max(320, WORK_H - BAR_H - WINDOW_EXTRA_H - 20)      # 图片最多这么高
MAX_W = max(320, min(1150, WORK_W - 100))                   # 图片最多这么宽


def fit_scale(w, h):
    """算出整张图（含状态条）都落在屏幕里的显示比例。"""
    return min(MAX_W / w, MAX_H / h, 1.0)


def put_cn(img, text, xy, color=(0, 255, 255), big=False):
    """在图上写中文 —— cv2 自带的 putText 画不出中文，借 Pillow 写。"""
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    ImageDraw.Draw(pil).text(xy, text, font=_font_big if big else _font,
                             fill=(color[2], color[1], color[0]))
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def load_image(path):
    """用 Pillow 读图：既认中文路径，也按手机照片的 EXIF 把方向转正。"""
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    img = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
    h, w = img.shape[:2]
    scale = fit_scale(w, h)
    disp = cv2.resize(img, (max(1, int(round(w * scale))), max(1, int(round(h * scale)))),
                      interpolation=cv2.INTER_AREA)
    return img, disp, scale


def label_path(img_path):
    return os.path.join(LBL_DIR, os.path.splitext(os.path.basename(img_path))[0] + ".txt")


def boxes_to_lines(boxes, w, h):
    """像素框 [(cls,x1,y1,x2,y2)] -> YOLO 的 5 列文本行。"""
    lines = []
    for cls, x1, y1, x2, y2 in boxes:
        x1, x2 = sorted((float(np.clip(x1, 0, w)), float(np.clip(x2, 0, w))))
        y1, y2 = sorted((float(np.clip(y1, 0, h)), float(np.clip(y2, 0, h))))
        bw, bh = x2 - x1, y2 - y1
        if bw <= 1 or bh <= 1:
            continue
        lines.append("%d %.6f %.6f %.6f %.6f"
                     % (cls, (x1 + x2) / 2 / w, (y1 + y2) / 2 / h, bw / w, bh / h))
    return lines


def lines_to_boxes(lines, w, h):
    boxes = []
    for ln in lines:
        p = ln.split()
        if len(p) != 5:
            continue
        cls = int(p[0])
        cx, cy, bw, bh = (float(v) for v in p[1:])
        boxes.append((cls, int((cx - bw / 2) * w), int((cy - bh / 2) * h),
                      int((cx + bw / 2) * w), int((cy + bh / 2) * h)))
    return boxes


def save_labels(img_path, boxes, w, h):
    os.makedirs(LBL_DIR, exist_ok=True)
    with open(label_path(img_path), "w", encoding="utf-8") as f:
        for ln in boxes_to_lines(boxes, w, h):
            f.write(ln + "\n")
    with open(os.path.join(LBL_DIR, "classes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(CLASSES) + "\n")


def load_labels(img_path, w, h):
    p = label_path(img_path)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return lines_to_boxes(f.readlines(), w, h)
    return []


def render(disp, img_path, idx, total, cls_id, boxes, scale, hint=""):
    """拼出屏幕上那一帧：顶部状态条 + 图片 + 已框的方框。"""
    body = disp.copy()
    for cls, x1, y1, x2, y2 in boxes:
        p1 = (int(x1 * scale), int(y1 * scale))
        p2 = (int(x2 * scale), int(y2 * scale))
        cv2.rectangle(body, p1, p2, (0, 255, 0), 2)
        body = put_cn(body, CN_NAMES[cls], (p1[0], max(0, p1[1] - 26)), (0, 255, 0))
    bar = np.zeros((BAR_H, body.shape[1], 3), dtype=np.uint8)
    line1 = "现在选的是 【%d %s】   —— 按 1 色块 / 2 锥桶 / 3 公仔 / 4 瓶子%s" % (
        cls_id + 1, CN_NAMES[cls_id], hint)
    line2 = "第 %d/%d 张  %s     本张已框 %d 个     D 下一张 · A 上一张 · U 撤销 · C 清空 · Q 退出" % (
        idx + 1, total, os.path.basename(img_path), len(boxes))
    bar = put_cn(bar, line1, (10, 5), (0, 255, 255))
    bar = put_cn(bar, line2, (10, 33), (120, 255, 120))
    return np.vstack([bar, body])


def main():
    files = sorted(sum([glob.glob(os.path.join(IMG_DIR, e))
                        for e in ("*.jpg", "*.jpeg", "*.png", "*.bmp")], []))
    if not files:
        print("dataset\\images 里还没有照片，先把手机拍的照片拷进去再跑。")
        return
    win = "fospeed 标注工具"
    cv2.namedWindow(win, cv2.WINDOW_AUTOSIZE)
    print("输入法已从这个窗口摘掉：", disable_ime(win))

    st = {"idx": 0, "cls": 0, "boxes": [], "drag": False,
          "start": (0, 0), "cur": (0, 0), "hint": "", "err": ""}
    img = disp = None
    scale = 1.0

    def reload(idx):
        nonlocal img, disp, scale
        st["idx"] = idx % len(files)
        img, disp, scale = load_image(files[st["idx"]])
        h, w = img.shape[:2]
        st["boxes"] = load_labels(files[st["idx"]], w, h)
        st["hint"] = ""

    def on_mouse(event, x, y, flags, param):
        try:
            y = y - BAR_H                    # 减掉顶部状态条，剩下的才对应图片本身
            if event == cv2.EVENT_LBUTTONDOWN and y >= 0:
                st["drag"], st["start"] = True, (x, y)
            elif event == cv2.EVENT_MOUSEMOVE:
                st["cur"] = (x, y)
            elif event == cv2.EVENT_LBUTTONUP and st["drag"]:
                st["drag"] = False
                x1, y1 = st["start"]
                ox1, oy1 = int(x1 / scale), int(y1 / scale)
                ox2, oy2 = int(x / scale), int(y / scale)
                h, w = img.shape[:2]
                if abs(ox2 - ox1) > w * 0.06 and abs(oy2 - oy1) > h * 0.06:
                    st["boxes"].append((st["cls"], ox1, oy1, ox2, oy2))
                    save_labels(files[st["idx"]], st["boxes"], w, h)
                    st["hint"] = "  已保存"
                else:
                    st["hint"] = "  框太小了，没保存 —— 贴着物体再拖大一点"
        except Exception:
            st["err"] = traceback.format_exc().splitlines()[-1]

    cv2.setMouseCallback(win, on_mouse)
    reload(0)

    while True:
        try:
            view = render(disp, files[st["idx"]], st["idx"], len(files),
                          st["cls"], st["boxes"], scale, st["hint"])
            if st["drag"]:
                cv2.rectangle(view, (st["start"][0], st["start"][1] + BAR_H),
                              (st["cur"][0], st["cur"][1] + BAR_H), (0, 255, 255), 1)
            if st["err"]:
                view = put_cn(view, "出错啦：" + st["err"], (10, BAR_H + 10), (0, 0, 255))
            cv2.imshow(win, view)
        except Exception:
            print("画面出错：", traceback.format_exc())
            break
        # 鼠标点窗口右上角的 ✕ 也能退出 —— 不然窗口被点掉以后，下一圈 imshow 又把它拉回来，
        # 看着就是「关不掉、只能去任务管理器」。
        try:
            if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:
                break
        except cv2.error:
            break
        raw = cv2.waitKey(20)
        k = raw & 0xFF
        if 65 <= k <= 90:                   # 大写字母当小写用（CapsLock 开着也能按）
            k += 32
        if raw in (2424832, 0xFF51):        # ← 上一张（两种键盘码都收）
            reload(st["idx"] - 1)
        elif raw in (2555904, 0xFF53):      # → 下一张
            reload(st["idx"] + 1)
        elif k in (ord("q"), 27):
            break
        elif k in (ord("1"), ord("2"), ord("3"), ord("4")):   # 数字键切类别，纯 Python 变量，不可能崩
            st["cls"] = k - ord("1")
            st["hint"] = ""
        elif k in (ord("d"), ord("n")):
            reload(st["idx"] + 1)
        elif k in (ord("a"), ord("p")):
            reload(st["idx"] - 1)
        elif k == ord("u") and st["boxes"]:
            st["boxes"].pop()
            h, w = img.shape[:2]
            save_labels(files[st["idx"]], st["boxes"], w, h)
            st["hint"] = "  撤销了一个框"
        elif k == ord("c"):
            st["boxes"] = []
            h, w = img.shape[:2]
            save_labels(files[st["idx"]], [], w, h)
            st["hint"] = "  本张清空了"
    cv2.destroyAllWindows()
    print("标注结束。结果在：", LBL_DIR)


if __name__ == "__main__":
    main()
