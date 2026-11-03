import os
import io
import ast
import base64
import zlib
import hashlib
import random
import string

from flask import Flask, render_template, request, jsonify, send_file
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

# ---------------- AURA CONFIG ----------------
AURA_MARKER = "# === END AURA METADATA (DO NOT REMOVE) ===\n"
XOR_KEY = 167

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEYS_DIR = os.path.join(BASE_DIR, "keys")
os.makedirs(KEYS_DIR, exist_ok=True)
PRIV_PATH = os.path.join(KEYS_DIR, "aura_private.pem")
PUB_PATH = os.path.join(KEYS_DIR, "aura_public.pem")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


# ---------------- KEY MANAGEMENT ----------------
def ensure_keys():
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


PRIV, PUB = ensure_keys()


# ---------------- MODE 01 — SIGNATURE PROTECTOR ----------------
def protect_mode01(code: str) -> str:
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


# ---------------- MODE 02 — ADVANCED OBFUSCATOR (BD-Style) ----------------
_AURA_RESERVED = {
    'IlIlIIlIIlIllIlI', 'IIIllllllIIIlIIIll',
    'IlIIlIIlIIIlIl', 'IlIIIIllIll',
    'IlIllIlIIlIllIl', 'llIlIllIllIIllIIlI',
    'IllllIlIlllIllIII', 'lllIIIIIIIIllI',
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
}

_AURA_MODE02_PREAMBLE = (
    "globals()['IlIlIIlIIlIllIlI'] = lambda *a: ''.join(map(chr, [x ^ 167 for x in a]))\n"
    "globals()['IIIllllllIIIlIIIll'] = getattr(__builtins__, IlIlIIlIIlIllIlI(248, 248, 195, 206, 196, 211, 248, 248), __builtins__)\n"
    "IlIIlIIlIIIlIl = IIIllllllIIIlIIIll[IlIlIIlIIlIllIlI(202, 198, 215)]\n"
    "IlIIIIllIll = IIIllllllIIIlIIIll[IlIlIIlIIlIllIlI(196, 207, 213)]\n"
    "globals()['IlIlIIlIIlIllIlI'] = lambda *a: ''.join(IlIIlIIlIIIlIl(IlIIIIllIll, [x ^ 167 for x in a]))\n"
    "globals()['IlIllIlIIlIllIl'] = lambda b, k: IIIllllllIIIlIIIll[IlIlIIlIIlIllIlI(197, 222, 211, 194, 212)]((x ^ k[i % IIIllllllIIIlIIIll[IlIlIIlIIlIllIlI(203, 194, 201)](k)] for i, x in IIIllllllIIIlIIIll[IlIlIIlIIlIllIlI(194, 201, 218, 202, 194, 213, 198, 211, 194)](b)))\n"
    "globals()['llIlIllIllIIllIIlI'] = IlIllIlIIlIllIl\n"
    "globals()['IllllIlIlllIllIII'] = IlIllIlIIlIllIl\n"
    "globals()['lllIIIIIIIIllI'] = IlIllIlIIlIllIl\n"
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
            if isinstance(t, ast.Name):
                self.defined.add(t.id)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name):
            self.defined.add(node.target.id)
        self.generic_visit(node)

    def visit_arg(self, node):
        self.defined.add(node.arg)
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

    def visit_Attribute(self, node):
        self.visit(node.value)
        return node


class AuraBuiltinRewriter(ast.NodeTransformer):
    def __init__(self, shadowed):
        self.shadowed = shadowed

    def visit_Name(self, node):
        if (
            isinstance(node.ctx, ast.Load)
            and node.id in _AURA_BUILTINS
            and node.id not in self.shadowed
        ):
            elts = [ast.Constant(value=ord(c) ^ XOR_KEY) for c in node.id]
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


class AuraStringEncoder(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str):
            if not node.value:
                return ast.copy_location(
                    ast.Call(
                        func=ast.Name(id='IlIlIIlIIlIllIlI', ctx=ast.Load()),
                        args=[], keywords=[],
                    ),
                    node,
                )
            elts = [ast.Constant(value=ord(c) ^ XOR_KEY) for c in node.value]
            return ast.copy_location(
                ast.Call(
                    func=ast.Name(id='IlIlIIlIIlIllIlI', ctx=ast.Load()),
                    args=elts, keywords=[],
                ),
                node,
            )
        if isinstance(node.value, bytes):
            key = b'\xde\x2c\xeb\x3b'
            encoded = bytes(x ^ key[i % len(key)] for i, x in enumerate(node.value))
            return ast.copy_location(
                ast.Call(
                    func=ast.Name(id='llIlIllIllIIllIIlI', ctx=ast.Load()),
                    args=[
                        ast.Constant(value=encoded),
                        ast.Constant(value=key),
                    ],
                    keywords=[],
                ),
                node,
            )
        return node


def obfuscate_mode02(code: str) -> str:
    try:
        ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Syntax error in source: {e}")

    body = code

    try:
        tree = ast.parse(code)
        collector = NameCollector()
        collector.visit(tree)
        user_defined = collector.defined - collector.imported
        shadowed = user_defined & _AURA_BUILTINS
        targets = (user_defined - _AURA_BUILTINS) | shadowed
        targets = targets - _AURA_RESERVED

        renamer = Renamer(targets)
        tree = renamer.visit(tree)
        ast.fix_missing_locations(tree)

        builtin_rw = AuraBuiltinRewriter(shadowed)
        tree = builtin_rw.visit(tree)
        ast.fix_missing_locations(tree)

        encoder = AuraStringEncoder()
        tree = encoder.visit(tree)
        ast.fix_missing_locations(tree)

        candidate = ast.unparse(tree)
        ast.parse(_AURA_MODE02_PREAMBLE + candidate + "\n")
        body = candidate
    except Exception:
        body = code

    header = (
        "# ============================================\n"
        "# AURA — MAVIXOR ADVANCED OBFUSCATOR\n"
        "# Developer: MAVIXOR\n"
        "# Mode: 02 (BD-Style XOR + Builtins Indirection)\n"
        "# ============================================\n"
    )

    result = header + _AURA_MODE02_PREAMBLE + body + "\n"

    try:
        ast.parse(result)
    except SyntaxError:
        return header + body

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
        if mode not in ("mode01", "mode02"):
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
        else:
            result = obfuscate_mode02(code)
            suffix = "obf"

        try:
            ast.parse(result)
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