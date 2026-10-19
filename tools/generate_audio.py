# 程序化生成基础音效（纯标准库，无外部依赖）
from pathlib import Path
import wave
import struct
import math
import random

# 直接输出到 Godot 客户端目录
OUT_DIR = Path("client/audio")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_RATE = 44100

def save_wav(name: str, samples: list[float]):
    path = OUT_DIR / name
    with wave.open(str(path), 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        # 转成 16-bit 整数
        data = b''.join(struct.pack('<h', int(max(-1.0, min(1.0, s)) * 32767)) for s in samples)
        w.writeframes(data)
    print(f"Generated {path}")

def apply_envelope(samples: list[float], attack=0.02, decay=0.1) -> list[float]:
    """简单 AD 包络，防止前后爆音"""
    n = len(samples)
    a_len = int(SAMPLE_RATE * attack)
    d_len = int(SAMPLE_RATE * decay)
    out = []
    for i in range(n):
        if i < a_len:
            vol = i / max(1, a_len)
        elif i < a_len + d_len:
            vol = 1.0 - ((i - a_len) / max(1, d_len))
        else:
            vol = 0.0
        out.append(samples[i] * vol)
    return out

# ==========================================
# 音效生成器
# ==========================================

def gen_click():
    """UI 点击：极短、高频衰减"""
    dur = 0.05
    n = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        # 混合 1200Hz 和 2400Hz，快速指数衰减
        val = (math.sin(2 * math.pi * 1200 * t) * 0.5 +
               math.sin(2 * math.pi * 2400 * t) * 0.5) * math.exp(-t * 100)
        samples.append(val)
    return apply_envelope(samples, attack=0.001, decay=0.04)

def gen_success():
    """成功/获得物品：清脆的双音阶上升"""
    dur = 0.4
    n = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        # 前半段 800Hz，后半段 1200Hz
        freq = 800 if t < 0.15 else 1200
        val = math.sin(2 * math.pi * freq * t) * math.exp(-t * 8)
        samples.append(val)
    return apply_envelope(samples, attack=0.01, decay=0.3)

def gen_error():
    """错误/失败：低沉、下坠"""
    dur = 0.3
    n = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        # 频率随时间下降
        freq = 300 - (t * 500)
        val = math.sin(2 * math.pi * max(50, freq) * t) * math.exp(-t * 10)
        samples.append(val)
    return apply_envelope(samples, attack=0.01, decay=0.2)

def gen_hit():
    """战斗命中：低频冲击 + 噪声"""
    dur = 0.15
    n = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        # 低频主体 + 短促噪声
        body = math.sin(2 * math.pi * 150 * t) * math.exp(-t * 20)
        noise = random.uniform(-1, 1) * math.exp(-t * 40) * 0.5
        samples.append(body * 0.7 + noise * 0.3)
    return apply_envelope(samples, attack=0.005, decay=0.1)

def gen_coin():
    """金币：高频金属撞击"""
    dur = 0.3
    n = int(SAMPLE_RATE * dur)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        # 3000Hz + 4000Hz，金属感
        val = (math.sin(2 * math.pi * 3000 * t) * 0.4 +
               math.sin(2 * math.pi * 4000 * t) * 0.3) * math.exp(-t * 15)
        samples.append(val)
    return apply_envelope(samples, attack=0.001, decay=0.2)

def gen_rain():
    """环境音：循环的雨声（白噪声低通）"""
    dur = 2.0  # 2秒循环
    n = int(SAMPLE_RATE * dur)
    samples = []
    last = 0.0
    for i in range(n):
        noise = random.uniform(-1, 1)
        # 简单的低通滤波器
        val = last * 0.95 + noise * 0.05
        last = val
        samples.append(val * 1.5)
    
    # 雨声为了循环平滑，首尾各做 0.1 秒的交叉淡化
    fade = int(SAMPLE_RATE * 0.1)
    for i in range(fade):
        vol = i / fade
        samples[i] *= vol
        samples[-i-1] *= vol
        
    return samples

if __name__ == "__main__":
    print("开始生成音效...")
    save_wav("click.wav", gen_click())
    save_wav("success.wav", gen_success())
    save_wav("error.wav", gen_error())
    save_wav("hit.wav", gen_hit())
    save_wav("coin.wav", gen_coin())
    save_wav("rain.wav", gen_rain())
    print("全部完成！请回到 Godot，它会自动导入这些 .wav 文件。")