# -*- coding: utf-8 -*-
"""把 G:\\fospeed\\code\\vision 里今天动过的东西同步进仓库，再提交、推送到 GitHub。

双击同目录的「更新到GitHub.cmd」就是跑它。它只做四件事：
    ① 拷脚本和数据集（只拷用得上的，归档、缓存、输出图一律不拷）
    ② 去掉脚本里写死的本机 Python 路径（公开仓库不带自己电脑的家底）
    ③ git add + commit（提交信息自动带今天的日期）
    ④ git push，并把 GitHub 的回话原样打出来

没有任何新变化时它会说「今天没有新东西」，不会造一个空提交。
"""

import os
import re
import subprocess
import sys
import datetime
import shutil
import glob

SRC = r"G:\fospeed\code\vision"
REPO = r"G:\fospeed\smartcar-vision-log"
DST = os.path.join(REPO, "vision")

# 拷哪些东西：(源目录, 源通配, 目标子目录)
计划 = [
    (SRC, "*.py", ""),
    (os.path.join(SRC, "dataset", "images"), "*.jpg", os.path.join("dataset", "images")),
    (os.path.join(SRC, "dataset", "images"), "*.png", os.path.join("dataset", "images")),
    (os.path.join(SRC, "dataset", "labels"), "*.txt", os.path.join("dataset", "labels")),
    (os.path.join(SRC, "训练实验"), "*.py", "训练实验"),
    (os.path.join(SRC, "训练实验"), "训练日志.txt", "训练实验"),
    (os.path.join(SRC, "盲调练习"), "*.py", "盲调练习"),
    (os.path.join(SRC, "盲调练习"), "练习记录.txt", "盲调练习"),
]

# 本机绝对路径 → 通用写法（公开仓库里不能带 C:\Users\Administrator... 这种家底）
脱敏规则 = [
    (re.compile(r'"[A-Za-z]:\\\\?Users\\\\?[^"]*?python\.exe"', re.I), '"python"'),
    (re.compile(r'[A-Za-z]:[\\/]+Users[\\/]+[^\s"\']{3,60}?python\.exe', re.I), 'python'),
    (re.compile(r'C:[\\/]+Users[\\/]+Administrator[^"\s\']*', re.I), '<本机路径>'),
]


def 跑(命令, cwd=REPO):
    """跑一条命令，返回 (返回码, 合并输出)"""
    结果 = subprocess.run(命令, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", shell=False)
    return 结果.returncode, (结果.stdout or "") + (结果.stderr or "")


def 拷文件():
    新拷 = 0
    for 源目录, 通配, 子目录 in 计划:
        if not os.path.isdir(源目录):
            continue
        目标目录 = os.path.join(DST, 子目录) if 子目录 else DST
        os.makedirs(目标目录, exist_ok=True)
        for 源 in glob.glob(os.path.join(源目录, 通配)):
            if os.path.isdir(源):
                continue
            名 = os.path.basename(源)
            目标 = os.path.join(目标目录, 名)
            需要拷 = (not os.path.exists(目标)) or \
                     os.path.getmtime(源) > os.path.getmtime(目标) + 1 or \
                     os.path.getsize(源) != os.path.getsize(目标)
            if not 需要拷:
                continue
            if 名.lower().endswith((".py", ".txt", ".cmd")):
                try:
                    with open(源, encoding="utf-8", errors="replace") as f:
                        文本 = f.read()
                    for 正则, 换 in 脱敏规则:
                        文本 = 正则.sub(换, 文本)
                    with open(目标, "w", encoding="utf-8", newline="\n") as f:
                        f.write(文本)
                except Exception as 错:
                    print("    跳过 %s（%s）" % (名, 错))
                    continue
            else:
                shutil.copy2(源, 目标)
            新拷 += 1
            print("    + " + os.path.join(子目录, 名) if 子目录 else "    + " + 名)
    return 新拷


def main():
    print("")
    print("========== 更新到 GitHub ==========")
    今天 = datetime.date.today().strftime("%Y-%m-%d")

    if not os.path.isdir(REPO):
        print("找不到仓库文件夹：" + REPO)
        return 1

    print("① 同步文件到仓库（只拷用得上的）")
    新拷 = 拷文件()
    print("    本次拷入 %d 个文件" % 新拷)

    print("② 看看仓库里有什么变化")
    码, 输出 = 跑(["git", "status", "--porcelain"])
    if 码 != 0:
        print("    git 出错了：" + 输出.strip())
        return 1
    变化 = [行 for 行 in 输出.splitlines() if 行.strip()]
    if not 变化:
        print("    今天没有新东西 —— 不提交，也不推送。")
        return 0
    for 行 in 变化[:20]:
        print("    " + 行)
    if len(变化) > 20:
        print("    …… 还有 %d 处" % (len(变化) - 20))

    print("③ 提交")
    码, 输出 = 跑(["git", "add", "-A"])
    if 码 != 0:
        print("    git add 失败：" + 输出.strip())
        return 1
    信息 = "学习记录 " + 今天
    码, 输出 = 跑(["git", "commit", "-m", 信息])
    if 码 != 0:
        print("    提交失败：" + 输出.strip()[:400])
        return 1
    print("    " + 信息)

    print("④ 推送到 GitHub")
    码, 输出 = 跑(["git", "push", "origin", "HEAD"])
    print("    " + 输出.strip().replace("\n", "\n    ")[:800])
    if 码 != 0:
        print("")
        print("推送没成功。照这个顺序查：")
        print("    1) 能不能打开 github.com？打不开 = 网的问题（Steam++ 写的 hosts 会挡住它）")
        print("    2) 它说要密码/登录 = GitHub 那边掉登录了，需要重新登录一次")
        return 1

    print("")
    print("推送成功。仓库地址：https://github.com/wudixiaowang/smartcar-vision-log")
    return 0


if __name__ == "__main__":
    sys.exit(main())
