import os
import io
import ast
import base64
import zlib
import hashlib
import random
import string
import traceback
import binascii

from flask import Flask, render_template, request, jsonify, send_file

# ---------------- CRYPTOGRAPHY IMPORT (Safe for Android) ----------------
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    CRYPTO_OK = True
except ImportError:
    CRYPTO_OK = False

# ---------------- AURA CONFIG ----------------
AURA_MARKER = "# === END AURA METADATA (DO NOT REMOVE) ===\n"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEYS_DIR = os.path.join(BASE_DIR, "keys")
os.makedirs(KEYS_DIR, exist_ok=True)
PRIV_PATH = os.path.join(KEYS_DIR, "aura_private.pem")
PUB_PATH = os.path.join(KEYS_DIR, "aura_public.pem")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


# ---------------- KEY MANAGEMENT ----------------
def ensure_keys():
    if not CRYPTO_OK:
        return None, None
    if not (os.path.exists(PRIV_PATH) and os.path.exists(PUB_PATH)):
        priv = Ed25519PrivateKey.generate()
        with open(PRIV_PATH, "wb") as f:
            f.write(priv.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ))
        with open(PUB_PATH, "wb") as f:
            f.write(priv.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ))
    with open(PRIV_PATH, "rb") as f:
        priv = serialization.load_pem_private_key(f.read(), password=None)
    with open(PUB_PATH, "rb") as f:
        pub = serialization.load_pem_public_key(f.read())
    return priv, pub


if CRYPTO_OK:
    PRIV, PUB = ensure_keys()
else:
    PRIV, PUB = None, None


# ---------------- MODE 01 — SIGNATURE PROTECTOR ----------------
def protect_mode01(code: str) -> str:
    if not CRYPTO_OK:
        raise ValueError("Mode 01 requires the 'cryptography' library. (Currently unavailable on this device).")
    
    code_bytes = code.encode("utf-8")
    digest = hashlib.sha256(code_bytes).hexdigest()
    sig = PRIV.sign(code_bytes)
    sig_b64 = base64.b64encode(sig).decode("ascii")
    pub_b64 = base64.b64encode(PUB.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )).decode("ascii")

    header = (
        "# ============================================\n"
        "# AURA — MAVIXOR SIGNATURE PROTECTOR\n"
        "# Developer: MAVIXOR\n"
        f"# SHA256: {digest}\n"
        f"# ED25519-SIGNATURE: {sig_b64}\n"
        f"# ED25519-PUBKEY: {pub_b64}\n"
        "# ============================================\n"
        f"{AURA_MARKER}"
    )
    return header + code


# ---------------- MODE 02 — ULTRA HARD ----------------
_AURA_RESERVED = {
    'IlIlIIlIIlIllIlI', 'IIIllllllIIIlIIIll',
    'IlIIlIIlIIIlIl', 'IlIIIIllIll',
    'IlIllIlIIlIllIl', 'llIlIllIllIIllIIlI',
    'IllllIlIlllIllIII', 'lllIIIIIIIIllI',
    'IlIlIlllIllI', 'IlIlIlllIlI', 'IlIlIlllIIl',
    'IlllIlIlI', 'IllIlIlIlII', 'IlIlIlIlIll',
    'IlIlllI', 'IllIIIl',
    'IlIIIlIIllIIIl', 'IlIIlllIlIIll', 'IllIllIlIIIIl',
}

_AURA_BUILTINS = {
    'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
    'callable', 'chr', 'classmethod', 'compile', 'complex', 'delattr',
    'dict', 'dir', 'divmod', 'enumerate', 'eval', 'exec', 'filter',
    'float', 'format', 'frozenset', 'getattr', 'hasattr', 'hash', 'help',
    'hex', 'id', 'input', 'int', 'isinstance', 'issubclass', 'iter',
    'len', 'list', 'locals', 'map', 'max', 'memoryview', 'min', 'next',
    'object', 'oct', 'open', 'ord', 'pow', 'print', 'property', 'range',
    'repr', 'reversed', 'round', 'set', 'setattr', 'slice', 'sorted',
    'staticmethod', 'str', 'sum', 'super', 'tuple', 'type', 'vars', 'zip',
    '__import__', '__build_class__',
    'Exception', 'ValueError', 'TypeError', 'KeyError', 'IndexError',
    'AttributeError', 'RuntimeError', 'StopIteration', 'ZeroDivisionError',
    'OverflowError', 'ImportError', 'NameError', 'UnicodeDecodeError',
    'UnicodeEncodeError', 'FileNotFoundError', 'OSError', 'IOError',
    'PermissionError', 'ConnectionError', 'TimeoutError',
    'NotImplementedError', 'AssertionError', 'BaseException',
    'KeyboardInterrupt', 'SystemExit', 'GeneratorExit',
    'StopAsyncIteration', 'RuntimeWarning', 'SyntaxError',
}


def _enc_char(c, K, M):
    return (ord(c) ^ K) + M


def _build_preamble(K, M, KB):
    decoy1 = ", ".join(str(_enc_char(c, K, M)) for c in "AURA")
    decoy2 = ", ".join(str(_enc_char(c, K, M)) for c in "MAVIXOR")

    return (
        "def IlIIIlIIllIIIl():\n"
        f"    IlllIlIlI = {K}\n"
        f"    IllIlIlIlII = {M}\n"
        f"    IlIlIlIlIll = {KB}\n"
        "    def IlIlllI(*IlIlllll):\n"
        "        IlIlIlIl = []\n"
        "        for IlIlIIlII in IlIlllll:\n"
        "            IlIlIlIl.append(chr(((IlIlIIlII - IllIlIlIlII) ^ IlllIlIlI) & 0xFFFF))\n"
        "        return ''.join(IlIlIlIl)\n"
        "    def IlIIlllIlIIll(IlIllllll, IlIlllllll=None):\n"
        "        if IlIlllllll is None:\n"
        "            IlIlllllll = bytes([IlIlIlIlIll])\n"
        "        IlIlll = []\n"
        "        for IlIIIIIlI, IlIlIlllII in enumerate(IlIllllll):\n"
        "            IlIlll.append(IlIlIlllII ^ IlIlllllll[IlIIIIIlI % len(IlIlllllll)])\n"
        "        return bytes(IlIlll)\n"
        "    return IlIlllI, IlIIlllIlIIll\n"
        "IlIlIlllIlI, IlIlIlllIIl = IlIIIlIIllIIIl()\n"
        "globals()['IlIlIIlIIlIllIlI'] = IlIlIlllIlI\n"
        "globals()['llIlIllIllIIllIIlI'] = IlIlIlllIIl\n"
        "globals()['IllllIlIlllIllIII'] = IlIlIlllIIl\n"
        "globals()['lllIIIIIIIIllI'] = IlIlIlllIIl\n"
        "globals()['IlIllIlIIlIllIl'] = IlIlIlllIIl\n"
        "globals()['IIIllllllIIIlIIIll'] = getattr(__builtins__, '__dict__', __builtins__)\n"
        "del IlIIIlIIllIIIl, IlIlIlllIlI, IlIlIlllIIl\n"
        f"_IlIlllllllI = IlIlIIlIIlIllIlI({decoy1}) + IlIlIIlIIlIllIlI({decoy2})\n"
    )


def _gen_name(lo=9, hi=15):
    while True:
        n = random.randint(lo, hi)
        name = "".join(random.choice("Il") for _ in range(n))
        if name not in _AURA_RESERVED:
            return name


class NameCollector(ast.NodeVisitor):
    def __init__(self):
        self.defined = set()
        self.imported = set()

    def visit_FunctionDef(self, node):
        self.defined.add(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.defined.add(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.defined.add(node.name)
        self.generic_visit(node)

    def visit_Assign(self, node):
        for t in node.targets:
            for n in ast.walk(t):
                if isinstance(n, ast.Name):
                    self.defined.add(n.id)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name):
            self.defined.add(node.target.id)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        if isinstance(node.target, ast.Name):
            self.defined.add(node.target.id)
        self.generic_visit(node)

    def visit_arg(self, node):
        self.defined.add(node.arg)
        self.generic_visit(node)

    def visit_For(self, node):
        for n in ast.walk(node.target):
            if isinstance(n, ast.Name):
                self.defined.add(n.id)
        self.generic_visit(node)

    def visit_comprehension(self, node):
        for n in ast.walk(node.target):
            if isinstance(n, ast.Name):
                self.defined.add(n.id)
        self.generic_visit(node)

    def visit_With(self, node):
        for item in node.items:
            if item.optional_vars is not None:
                for n in ast.walk(item.optional_vars):
                    if isinstance(n, ast.Name):
                        self.defined.add(n.id)
        self.generic_visit(node)

    def visit_AsyncWith(self, node):
        self.visit_With(node)

    def visit_ExceptHandler(self, node):
        if node.name:
            self.defined.add(node.name)
        self.generic_visit(node)

    def visit_Import(self, node):
        for n in node.names:
            self.imported.add(n.asname or n.name.split(".")[0])

    def visit_ImportFrom(self, node):
        for n in node.names:
            if n.name == "*":
                continue
            self.imported.add(n.asname or n.name)


class Renamer(ast.NodeTransformer):
    def __init__(self, names_to_rename):
        self.map = {}
        self.names = names_to_rename

    def _new(self, old):
        if old in self.map:
            return self.map[old]
        if old.startswith("__") and old.endswith("__"):
            return old
        if old in _AURA_BUILTINS:
            return old
        if old not in self.names:
            return old
        new = _gen_name()
        while new in self.map.values():
            new = _gen_name()
        self.map[old] = new
        return new

    def visit_Name(self, node):
        node.id = self._new(node.id)
        return node

    def visit_arg(self, node):
        node.arg = self._new(node.arg)
        return node

    def visit_FunctionDef(self, node):
        node.name = self._new(node.name)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        node.name = self._new(node.name)
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        node.name = self._new(node.name)
        self.generic_visit(node)
        return node

    def visit_ExceptHandler(self, node):
        if node.name:
            node.name = self._new(node.name)
        self.generic_visit(node)
        return node

    def visit_Attribute(self, node):
        self.visit(node.value)
        return node


class AuraBuiltinRewriter(ast.NodeTransformer):
    def __init__(self, shadowed, K, M):
        self.shadowed = shadowed
        self.K = K
        self.M = M

    def visit_Name(self, node):
        if (
            isinstance(node.ctx, ast.Load)
            and node.id in _AURA_BUILTINS
            and node.id not in self.shadowed
        ):
            elts = [
                ast.Constant(value=_enc_char(c, self.K, self.M))
                for c in node.id
            ]
            decoder_call = ast.Call(
                func=ast.Name(id='IlIlIIlIIlIllIlI', ctx=ast.Load()),
                args=elts, keywords=[],
            )
            sub = ast.Subscript(
                value=ast.Name(id='IIIllllllIIIlIIIll', ctx=ast.Load()),
                slice=decoder_call,
                ctx=ast.Load(),
            )
            return ast.copy_location(sub, node)
        return node


class MBAFold(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, int) and not isinstance(node.value, bool):
            if abs(node.value) < 10_000_000:
                r = random.randint(1, 9999)
                return ast.copy_location(
                    ast.BinOp(
                        left=ast.BinOp(
                            left=ast.Constant(value=node.value),
                            op=ast.Add(),
                            right=ast.Constant(value=r),
                        ),
                        op=ast.Sub(),
                        right=ast.Constant(value=r),
                    ),
                    node,
                )
        return node


class OpaquePredicate(ast.NodeTransformer):
    def visit_If(self, node):
        self.generic_visit(node)
        n = random.randint(1000, 99999)
        inner = ast.Compare(
            left=ast.BinOp(
                left=ast.BinOp(
                    left=ast.Constant(value=n * 2),
                    op=ast.Add(),
                    right=ast.Constant(value=1),
                ),
                op=ast.Mod(),
                right=ast.Constant(value=2),
            ),
            ops=[ast.Eq()],
            comparators=[ast.Constant(value=1)],
        )
        node.test = ast.BoolOp(op=ast.And(), values=[inner, node.test])
        return node


class ChunkedStringEncoder(ast.NodeTransformer):
    def __init__(self, K, M, KB):
        self.K = K
        self.M = M
        self.KB = KB

    def _chunk(self, data, min_len, max_len):
        if len(data) <= max_len:
            return [data]
        chunks = []
        i = 0
        while i < len(data):
            n = random.randint(min_len, max_len)
            chunks.append(data[i:i+n])
            i += n
        return chunks

    def _make_str_call(self, chunk):
        elts = [ast.Constant(value=_enc_char(c, self.K, self.M)) for c in chunk]
        return ast.Call(
            func=ast.Name(id='IlIlIIlIIlIllIlI', ctx=ast.Load()),
            args=elts, keywords=[],
        )

    def _make_bytes_call(self, chunk_bytes):
        key = bytes([self.KB])
        encoded = bytes(x ^ key[0] for x in chunk_bytes)
        return ast.Call(
            func=ast.Name(id='llIlIllIllIIllIIlI', ctx=ast.Load()),
            args=[
                ast.Constant(value=encoded),
                ast.Constant(value=key),
            ],
            keywords=[],
        )

    def _join(self, calls):
        if not calls:
            return None
        expr = calls[0]
        for c in calls[1:]:
            expr = ast.BinOp(left=expr, op=ast.Add(), right=c)
        return expr

    def _encode_str(self, s):
        if not s:
            return ast.Call(
                func=ast.Name(id='IlIlIIlIIlIllIlI', ctx=ast.Load()),
                args=[], keywords=[],
            )
        chunks = self._chunk(s, 1, 5)
        calls = [self._make_str_call(c) for c in chunks]
        return self._join(calls)

    def _encode_bytes(self, b):
        if not b:
            return self._make_bytes_call(b'')
        if len(b) > 200:
            chunks = self._chunk(b, 32, 64)
        elif len(b) > 50:
            chunks = self._chunk(b, 8, 16)
        else:
            chunks = self._chunk(b, 4, 10)
        calls = [self._make_bytes_call(c) for c in chunks]
        return self._join(calls)

    def visit_JoinedStr(self, node):
        for v in node.values:
            if isinstance(v, ast.FormattedValue):
                v.value = self.visit(v.value)
                if v.format_spec is not None:
                    v.format_spec = self.visit(v.format_spec)
        return node

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            return ast.copy_location(self._encode_str(node.value), node)
        if isinstance(node.value, bytes):
            return ast.copy_location(self._encode_bytes(node.value), node)
        return node


class CFF(ast.NodeTransformer):
    def __init__(self):
        self.counter = 0

    def _next(self):
        self.counter += 1
        return self.counter

    def _has_hard_control(self, stmts):
        for s in stmts:
            for node in ast.walk(s):
                if isinstance(node, (ast.Try, ast.While, ast.For,
                                     ast.AsyncFor, ast.With, ast.AsyncWith,
                                     ast.Return, ast.Raise, ast.Break,
                                     ast.Continue, ast.Yield, ast.YieldFrom,
                                     ast.Await, ast.AsyncFunctionDef,
                                     ast.Lambda)):
                    return True
        return False

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if not node.body or self._has_hard_control(node.body) or len(node.body) < 3:
            return node
        has_only_safe = all(
            isinstance(s, (ast.Expr, ast.Assign, ast.AugAssign, ast.If,
                           ast.Pass, ast.AnnAssign, ast.Assert))
            for s in node.body
        )
        if not has_only_safe:
            return node
        for s in node.body:
            for n in ast.walk(s):
                if isinstance(n, (ast.Try, ast.While, ast.For, ast.Return,
                                  ast.Raise, ast.Break, ast.Continue)):
                    return node

        state_var = _gen_name(10, 14)
        exit_state = 0
        blocks = [(self._next(), stmt) for stmt in node.body]

        chain = None
        cur = None
        for i, (num, stmt) in enumerate(blocks):
            r = random.randint(100, 999)
            test = ast.Compare(
                left=ast.BinOp(
                    left=ast.BinOp(
                        left=ast.Name(id=state_var, ctx=ast.Load()),
                        op=ast.Add(),
                        right=ast.Constant(value=r),
                    ),
                    op=ast.Sub(),
                    right=ast.Constant(value=r),
                ),
                ops=[ast.Eq()],
                comparators=[ast.Constant(value=num)],
            )
            body = [stmt]
            next_state = blocks[i + 1][0] if i + 1 < len(blocks) else exit_state
            body.append(ast.Assign(
                targets=[ast.Name(id=state_var, ctx=ast.Store())],
                value=ast.Constant(value=next_state),
            ))
            body.append(ast.Continue())
            if_node = ast.If(test=test, body=body, orelse=[])
            if chain is None:
                chain = if_node
                cur = if_node
            else:
                cur.orelse = [if_node]
                cur = if_node

        r = random.randint(100, 999)
        exit_test = ast.Compare(
            left=ast.BinOp(
                left=ast.BinOp(
                    left=ast.Name(id=state_var, ctx=ast.Load()),
                    op=ast.Add(),
                    right=ast.Constant(value=r),
                ),
                op=ast.Sub(),
                right=ast.Constant(value=r),
            ),
            ops=[ast.Eq()],
            comparators=[ast.Constant(value=exit_state)],
        )
        exit_node = ast.If(test=exit_test, body=[ast.Break()], orelse=[])
        if cur is not None:
            cur.orelse = [exit_node]
        else:
            chain = exit_node

        new_loop = ast.While(test=ast.Constant(value=True), body=[chain], orelse=[])
        node.body = [
            ast.Assign(
                targets=[ast.Name(id=state_var, ctx=ast.Store())],
                value=ast.Constant(value=blocks[0][0] if blocks else exit_state),
            ),
            new_loop,
        ]
        ast.fix_missing_locations(node)
        return node


def obfuscate_mode02(code: str) -> str:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Syntax error in source: {e}")

    K = random.randint(60, 200)
    M = random.randint(20, 100)
    KB = random.randint(60, 200)

    docstring_ast = None
    if tree.body and isinstance(tree.body[0], ast.Expr):
        v = tree.body[0].value
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            docstring_ast = tree.body[0]
            tree.body = tree.body[1:]

    future_asts = []
    while (tree.body and isinstance(tree.body[0], ast.ImportFrom)
           and tree.body[0].module == "__future__"):
        future_asts.append(tree.body[0])
        tree.body = tree.body[1:]

    try:
        collector = NameCollector()
        collector.visit(tree)
        user_defined = collector.defined - collector.imported
        shadowed = user_defined & _AURA_BUILTINS
        targets = (user_defined - _AURA_BUILTINS) | shadowed
        targets = targets - _AURA_RESERVED
        tree = Renamer(targets).visit(tree)
        ast.fix_missing_locations(tree)

        tree = AuraBuiltinRewriter(shadowed, K, M).visit(tree)
        ast.fix_missing_locations(tree)

        tree = CFF().visit(tree)
        ast.fix_missing_locations(tree)

        tree = OpaquePredicate().visit(tree)
        ast.fix_missing_locations(tree)

        tree = ChunkedStringEncoder(K, M, KB).visit(tree)
        ast.fix_missing_locations(tree)

        tree = MBAFold().visit(tree)
        ast.fix_missing_locations(tree)
    except Exception:
        traceback.print_exc()
        return _aura_mode02_fallback(code)

    header = (
        "# ============================================\n"
        "# AURA — MAVIXOR ADVANCED OBFUSCATOR\n"
        "# Developer: MAVIXOR\n"
        "# Mode: 02 (Ultra Hard: CFF + MBA + Opaque + Chunking)\n"
        "# ============================================\n"
    )
    preamble = _build_preamble(K, M, KB)

    pieces = [header]
    if docstring_ast is not None:
        try:
            pieces.append(ast.unparse(docstring_ast))
        except Exception:
            pass
    for f in future_asts:
        try:
            pieces.append(ast.unparse(f))
        except Exception:
            pass
    pieces.append(preamble)
    try:
        pieces.append(ast.unparse(tree))
    except Exception:
        traceback.print_exc()
        return _aura_mode02_fallback(code)

    result = "\n".join(pieces) + "\n"

    try:
        compile(result, "<aura>", "exec")
    except SyntaxError:
        traceback.print_exc()
        return _aura_mode02_fallback(code)

    return result


def _aura_mode02_fallback(code: str) -> str:
    K = random.randint(60, 200)
    M = random.randint(20, 100)
    KB = random.randint(60, 200)
    header = (
        "# ============================================\n"
        "# AURA — MAVIXOR ADVANCED OBFUSCATOR (fallback)\n"
        "# ============================================\n"
    )
    return header + _build_preamble(K, M, KB) + "\n" + code


# ---------------- MODE 03 — KRAMER-STYLE ----------------
_KRAMER_ALPHA = "abcdefghijklmnopqrstuvwxyz0123456789"

def _kyrie_ekyrie(text: str) -> str:
    r = ""
    for a in text:
        if a in _KRAMER_ALPHA:
            a = _KRAMER_ALPHA[_KRAMER_ALPHA.index(a) - 1]
        r += a
    return r

def _kyrie_encrypt(text: str, key: int) -> str:
    return "".join(
        chr(ord(t) + key) if t != "\n" else "\u03b6"
        for t in text
    )

def _kramer_core(content: str, key: int) -> str:
    e1 = _kyrie_ekyrie(content)
    e = _kyrie_encrypt(e1, key)
    lines_sep = '/'
    hex_lines = lines_sep.join(
        binascii.hexlify(x.encode()).decode() for x in e
    )

    fixed = {"n_1": "_eval", "n_4": "_exec", "n_7": "_byte"}
    free_pool = [
        "_bytes", "_bit", "_bits", "_system",
        "_encode", "_decode", "_delete", "_exit",
        "_rasputin", "_kramer",
    ]
    random.shuffle(free_pool)
    n_map = dict(fixed)
    for i in (2, 3, 5, 6, 8, 9, 10, 11, 12):
        n_map[f"n_{i}"] = free_pool.pop()

    types_pool = ("str", "float", "bool", "int")

    _1_ = (
        "_n5_",
        'lambda _n9_:"".join(__import__(_n7_[1]+_n7_[8]+_n7_[13]+_n7_[0]+_n7_[18]+_n7_[2]+_n7_[8]+_n7_[8]).unhexlify(str(_n10_)).decode()for _n10_ in str(_n9_).split(\'/\'))',
    )
    _2_ = (
        "_n6_",
        'lambda _n1_:str(_n4_[_n2_](f"{_n7_[4]+_n7_[-13]+_n7_[4]+_n7_[2]}(\'\'.join(%s),{_n7_[6]+_n7_[11]+_n7_[14]+_n7_[1]+_n7_[0]+_n7_[11]+_n7_[18]}())"%list(_n1_))).encode(_n7_[20]+_n7_[19]+_n7_[5]+_n7_[34])if _n4_[_n2_]==eval else exit()',
    )
    _3_ = ("_n4_[_n2_]", "eval")
    _4_ = (
        "_n1_",
        'lambda _n1_:exit()if _n7_[15]+_n7_[17]+_n7_[8]+_n7_[13]+_n7_[19] in open(__file__, errors=_n7_[8]+_n7_[6]+_n7_[13]+_n7_[14]+_n7_[17]+_n7_[4]).read() or _n7_[8]+_n7_[13]+_n7_[15]+_n7_[20]+_n7_[19] in open(__file__, errors=_n7_[8]+_n7_[6]+_n7_[13]+_n7_[14]+_n7_[17]+_n7_[4]).read()else"".join(_n1_ if _n1_ not in _n7_ else _n7_[_n7_.index(_n1_)+1 if _n7_.index(_n1_)+1<len(_n7_)else 0]for _n1_ in "".join(chr(ord(t)-%d)if t!="\u03b6"else"\\n"for t in _n5_(_n1_)))' % key,
    )
    _5_ = (
        "_n7_",
        "exit()if _n1_ else'abcdefghijklmnopqrstuvwxyz0123456789'",
    )
    _6_ = ("_n8_", "lambda _n12_:_n6_(_n1_(_n12_))")

    all_ = [_1_, _2_, _3_, _4_, _5_, _6_]
    random.shuffle(all_)

    vars_content = ",".join(s[0] for s in all_)
    valors_content = ",".join(s[1] for s in all_)
    vars_line = vars_content + "=" + valors_content

    t1 = random.choice(types_pool)
    t2 = random.choice(types_pool)
    t3 = random.choice(types_pool)
    t4 = random.choice(types_pool)

    content_repr = repr(hex_lines)

    final_template = (
        "class Kramer():\n"
        " def __decode__(self:object,_execute:str)->exec:return(None,_n8_(_execute))[0]\n"
        " def __init__(self:object,_n1_:T1=False,_n2_:T2=0,*_n3_:T3,**_n4_:T4)->exec:\n"
        "  VARS\n"
        "  return self.__decode__(_n4_[(_n7_[-1]+'_')[-1]+_n7_[18]+_n7_[15]+_n7_[0]+_n7_[17]+_n7_[10]+_n7_[11]+_n7_[4]])\n"
        "Kramer(_n1_=False,_n2_=False,_sparkle=CONTENT)"
    )

    out = final_template.replace("T1", t1).replace("T2", t2)\
                        .replace("T3", t3).replace("T4", t4)\
                        .replace("VARS", vars_line)\
                        .replace("CONTENT", content_repr)

    for placeholder in sorted(
        [f"_n{i}_" for i in range(1, 13)] + ["_n5_", "_n6_", "_n7_", "_n8_", "_n9_", "_n10_", "_n12_"],
        key=len, reverse=True,
    ):
        if placeholder in out:
            idx = placeholder[2:-1]
            key_ = idx.replace("_", "")
            if key_ in n_map:
                out = out.replace(placeholder, n_map[key_].removeprefix("self."))

    return out.strip()


def obfuscate_mode03(code: str) -> str:
    try:
        ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Syntax error in source: {e}")

    key = random.randint(3, 1000000)
    body = _kramer_core(code, key)

    header = (
        "# ============================================\n"
        "# AURA — MAVIXOR KRAMER-STYLE OBFUSCATOR\n"
        "# Developer: MAVIXOR\n"
        f"# Mode: 03 (Kyrie cipher + hex + shuffled vars)  key={key}\n"
        "# ============================================\n"
    )
    result = header + body + "\n"

    try:
        compile(result, "<aura-m3>", "exec")
    except SyntaxError:
        traceback.print_exc()
        raise ValueError("Kramer-style output failed syntax check")

    return result


# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/protect", methods=["POST"])
def protect():
    try:
        data = request.get_json(silent=True) or {}
        code = data.get("code", "")
        mode = data.get("mode", "")

        if not code.strip():
            return jsonify({"ok": False, "error": "No code provided."}), 400
        if mode not in ("mode01", "mode02", "mode03"):
            return jsonify({"ok": False, "error": "Invalid mode."}), 400

        try:
            ast.parse(code)
        except SyntaxError as e:
            return jsonify({
                "ok": False,
                "error": f"Python syntax error: {e.msg} (line {e.lineno})",
            }), 400

        if mode == "mode01":
            result = protect_mode01(code)
            suffix = "signed"
        elif mode == "mode02":
            result = obfuscate_mode02(code)
            suffix = "obf"
        else:
            result = obfuscate_mode03(code)
            suffix = "kramer"

        try:
            compile(result, "<aura-out>", "exec")
        except SyntaxError as e:
            return jsonify({
                "ok": False,
                "error": f"Generated file failed syntax check: {e.msg}",
            }), 500

        return jsonify({
            "ok": True,
            "output": result,
            "filename": f"aura_{suffix}_protected.py",
        })
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"Internal error: {e}"}), 500

@app.route("/download", methods=["POST"])
def download():
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")
    filename = data.get("filename", "aura_protected.py")
    if not code:
        return jsonify({"ok": False, "error": "Nothing to download."}), 400
    buf = io.BytesIO(code.encode("utf-8"))
    buf.seek(0)
    return send_file(
        buf,
        mimetype="text/x-python",
        as_attachment=True,
        download_name=filename,
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)