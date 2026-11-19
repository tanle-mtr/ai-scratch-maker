#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""共创世界 (CCW / cocrea.world) sb3 解密模块。

逆向自开源仓库 https://github.com/OpenCCW/sb3-crypto （Unlicense）。
CCW 的 sb3 有两层保护：

  1) 整文件加密（少见）：下载到的文件整体是 base64(AES-CBC(逗号分隔字节))。
     密钥 = b64decode("KzdnFCBRvq3" + 文件名前 32 字符) 的前 32 字节，
     IV   = 密钥的前 16 字节。AES-CBC 解密后得到的明文是「逗号分隔的十进制字节」，
     按逗号 split 即为真正的 zip 字节。

  2) 仅 project.json 混淆（常见）：zip 头是正常 PK，但 project.json 的内容被混淆
     成一段 base64 文本，还原方式：
        s  = btoa(encodeURIComponent(原始JSON))
        n  = len(s) % 10
        stored = s[:n] + 'bxeygiuc12'[n] + s[n+1:] + s[n]   # 把第 n 个字符挪到末尾，原位置塞一个哨兵字符
     解密时反过来把末尾字符拿回第 n 位，再 atob + decodeURIComponent。

本模块两个方向都实现，并带 --selftest 自检（加密->解密 往返一致）。
"""
import sys, os, base64, urllib.parse

try:
    from Crypto.Cipher import AES
    _HAVE_CRYPTO = True
except Exception:
    _HAVE_CRYPTO = False

CANARY = "bxeygiuc12"  # 长度 10，按 n 取哨兵字符


def _b64decode(text: str) -> bytes:
    """容错 base64 解码（补齐 padding）。"""
    t = text.encode("ascii") if isinstance(text, str) else text
    # 去掉空白
    t = t.strip()
    pad = (-len(t)) % 4
    if pad:
        t = t + b"=" * pad
    return base64.b64decode(t, validate=False)


def scramble_json(project_json: str) -> str:
    """加密侧：把 project.json 文本混淆成 stored 字符串（对应 encrypt.ts）。"""
    s = base64.b64encode(urllib.parse.quote(project_json).encode("utf-8")).decode("ascii")
    n = len(s) % 10
    return s[:n] + CANARY[n] + s[n + 1:] + s[n]


def unscramble_json(stored: str) -> str:
    """解密侧：还原 project.json 文本（对应 decrypt.ts 的 project.json 分支）。"""
    t = len(stored) - 1
    n = t % 10
    recon = stored[:n] + stored[t] + stored[n + 1:t]
    raw = _b64decode(recon)
    return urllib.parse.unquote(raw.decode("ascii"))


# --------------------------- 整文件 AES-CBC 路径 ---------------------------
def _derive_key(filename: str) -> bytes:
    """从文件名推导 32 字节 AES 密钥（对应 crypto-transform.ts）。"""
    if filename.endswith(".sb3"):
        filename = filename[:-4]
    i = max(filename.rfind("/"), filename.rfind("\\"))
    if i != -1:
        filename = filename[i + 1:]
    if len(filename) > 32:
        filename = filename[:32]
    return base64.b64decode(("KzdnFCBRvq3" + filename))[:32]


def _csb_split(data: bytes) -> bytes:
    """逗号分隔十进制字节 -> 字节串（对应 comma-separated-bytes.ts 的 csbSplit）。"""
    return bytes(int(x) for x in data.decode("ascii").split(",") if x != "")


def _csb_join(data: bytes) -> str:
    """字节串 -> 逗号分隔十进制（对应 csbJoin），用于自检加密。"""
    return ",".join(str(b) for b in data)


def decrypt_sb3(data: bytes, filename: str) -> bytes:
    """输入：下载到的 CCW sb3 字节；输出：标准 sb3（zip）字节。

    处理三种情况：
      - 以 PK\\x03\\x04 开头：未加密，仅还原 project.json（情况 2）。
      - 以 7z 头开头：zip 头被伪装成 7z，改回 PK 后按情况 2 处理。
      - 其它：整文件 base64 -> AES-CBC 解密 -> csbSplit -> zip 字节（情况 1）。
    """
    # 1) 整文件加密？
    if not (data[:3] == b"PK\x03" or data[:3] == b"7z\xaf" or data[:7] == b"7z\xbc\xaf\x27\x08\x09\x05\x02\x07"):
        if not _HAVE_CRYPTO:
            raise RuntimeError("整文件加密的 CCW sb3 需要 pycryptodome：pip install pycryptodome")
        key = _derive_key(filename)
        iv = key[:16]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(_b64decode(data.decode("ascii")))
        data = _csb_split(decrypted)
    # 2) 7z 头伪装 -> 还原 PK 头（前 8 字节固定为 PK\x03\x04\n\x00\x00\x00）
    if data[:6] == b"7z\xbc\xaf\x27\x08":
        data = bytearray(data)
        for i, b in enumerate([80, 75, 3, 4, 10, 0, 0, 0]):
            data[i] = b
        data = bytes(data)
    # 3) zip 内 project.json 混淆还原
    import zipfile, io
    zin = zipfile.ZipFile(io.BytesIO(data))
    # 判断 project.json 是否被混淆（不以 { 开头）
    pj = zin.read("project.json").decode("utf-8", "replace")
    if not pj.lstrip().startswith("{"):
        pj = unscramble_json(pj)
    # 写出新 zip
    out = io.BytesIO()
    zout = zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED)
    for item in zin.infolist():
        content = zin.read(item.filename)
        if item.filename == "project.json":
            content = pj.encode("utf-8")
        zout.writestr(item, content)
    zout.close()
    return out.getvalue()


def encrypt_sb3(project_json: str, filename: str) -> bytes:
    """自检用：把 project.json 加密回整文件加密的 CCW sb3（对应 encrypt.ts 全路径）。"""
    if not _HAVE_CRYPTO:
        raise RuntimeError("需要 pycryptodome")
    import zipfile, io
    scrambled = scramble_json(project_json).encode("utf-8")
    buf = io.BytesIO()
    z = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)
    z.writestr("project.json", scrambled)
    z.close()
    csb = _csb_join(buf.getvalue()).encode("ascii")
    key = _derive_key(filename)
    iv = key[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    # 补齐到 16 倍数
    if len(csb) % 16:
        csb = csb + b"\x00" * (16 - len(csb) % 16)
    enc = cipher.encrypt(csb)
    return base64.b64encode(enc)


def self_test() -> bool:
    print("CCW crypto self-test ...")
    # 1) project.json 混淆往返
    sample = '{"targets":[{"name":"Stage","blocks":{},"variables":{}}],"meta":{"some":"中文测试"}}'
    sc = scramble_json(sample)
    ok1 = unscramble_json(sc) == sample
    print("  [1] project.json scramble roundtrip:", "OK" if ok1 else "FAIL")
    # 2) 整文件 AES 往返（需要 pycryptodome；缺省则跳过）
    ok2 = ok3 = True
    if _HAVE_CRYPTO:
        fn = "abc123def456ghi789jkl012mno345".rjust(32, "0")[:32] + ".sb3"
        enc = encrypt_sb3(sample, fn)
        dec = decrypt_sb3(enc, fn)
        ok2 = dec.startswith(b"PK\x03\x04")
        import zipfile, io
        z = zipfile.ZipFile(io.BytesIO(dec))
        pj = z.read("project.json").decode("utf-8")
        ok3 = ("{" in pj) and ("中文测试" in pj)
        print("  [2] whole-file AES decrypt -> zip:", "OK" if ok2 else "FAIL")
        print("  [3] decrypted project.json readable:", "OK" if ok3 else "FAIL")
    else:
        print("  [2] whole-file AES path: SKIP (缺 pycryptodome，pip install pycryptodome)")
        print("  [3] whole-file AES path: SKIP")
    return ok1 and ok2 and ok3


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if self_test() else 1)
    print("usage: python ccw_crypto.py --selftest")
