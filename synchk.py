import ast
import sys

bad = 0
for path in sys.argv[1:]:
    try:
        src = open(path, encoding="utf-8").read()
        ast.parse(src)
        print("OK   " + path)
    except Exception as exc:
        bad += 1
        print("FAIL " + path + " " + type(exc).__name__ + " " + str(exc))
sys.exit(1 if bad else 0)
