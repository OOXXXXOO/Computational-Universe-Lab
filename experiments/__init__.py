"""独立实验脚本命名空间。

历史脚本仍支持从 experiments/ 目录直接运行；此包入口供 rulespace_gpu 中少量跨层复用使用。
少数冻结脚本仍使用平铺绝对 import，因此为 R10 注册兼容别名，不改写证书脚本本身。
"""
import importlib
import sys

_r10 = importlib.import_module(".r10_current_generator", __name__)
sys.modules.setdefault("r10_current_generator", _r10)
