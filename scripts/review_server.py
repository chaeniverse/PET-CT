#!/usr/bin/env python3
"""맥 판독용 로컬 서버: 후보 확인 페이지를 열고, 페이지의 버튼으로 3D Slicer 를 띄운다.

make_review_html.py 가 review 폴더에 이 파일을 복사해 두므로 rsync 로 맥 판독 폴더에 같이 온다(맥에 저장소가 없어도 된다).
  - 이 파일이 있는 폴더의 파일을 http://127.0.0.1:8765/ 로 준다(python3 -m http.server 와 같다). 다른 컴퓨터에서는 접속되지 않는다
  - POST /slicer/<case>         <case>_viewer/open_in_slicer.py 로 Slicer 를 연다(이미 열려 있으면 다시 열지 않는다)
  - POST /goto/<case>?x=&y=&z=  열린 Slicer 가 그 RAS 위치(mm)로 가도록 <case>_viewer/goto.json 을 쓴다
Slicer 에서 찍은 점은 Slicer 가 <case>_viewer/slicer_points.csv 에 쓰고, 페이지가 그 파일을 읽어 누락 병변 목록에 합친다.
케이스는 가명(P01, C001)만 받는다. 식별정보는 다루지 않는다.

사용(맥 터미널): python3 "<판독 폴더>/review_server.py"  ->  브라우저 http://127.0.0.1:8765/P01_후보확인.html
"""
import json
import os
import re
import subprocess
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get("REVIEW_PORT", "8765"))
SLICER = os.environ.get("SLICER", "/Applications/Slicer.app/Contents/MacOS/Slicer")
ORIGINS = {f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"}
CASE = re.compile(r"^(P\d{2}|C\d{3})$")
running = {}   # 케이스 -> 띄운 Slicer


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.headers.get("Origin") not in ORIGINS:     # 다른 웹사이트가 이 주소로 요청하지 못하게
            return self.reply(403, "판독 페이지에서만 부를 수 있다")
        url = urlparse(self.path)
        parts = url.path.strip("/").split("/")
        if len(parts) != 2 or parts[0] not in ("slicer", "goto") or not CASE.match(parts[1]):
            return self.reply(404, "알 수 없는 요청")
        cmd, case = parts
        vdir = ROOT / f"{case}_viewer"
        if not (vdir / "open_in_slicer.py").exists():
            return self.reply(404, f"{case}_viewer/open_in_slicer.py 가 없다. 페이지를 --no-viewer 없이 다시 만든다")
        if cmd == "slicer":
            p = running.get(case)
            if p is not None and p.poll() is None:
                return self.reply(200, f"{case} Slicer 가 이미 열려 있다")
            try:
                running[case] = subprocess.Popen([SLICER, "--python-script", "open_in_slicer.py"], cwd=vdir)
            except OSError as e:
                return self.reply(500, f"Slicer 를 열지 못했다({SLICER}): {e}")
            return self.reply(200, f"{case} Slicer 를 연다(처음에는 1분쯤 걸린다)")
        q = parse_qs(url.query)
        try:
            ras = [float(q[k][0]) for k in ("x", "y", "z")]
        except (KeyError, ValueError):
            return self.reply(400, "x·y·z(mm) 가 필요하다")
        (vdir / "goto.json").write_text(json.dumps({"ras": ras, "t": time.time()}), encoding="utf-8")
        return self.reply(200, f"Slicer 를 ({ras[0]:.1f}, {ras[1]:.1f}, {ras[2]:.1f}) mm 로 옮긴다")

    def reply(self, code, text):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")   # 찍은 점 파일을 늘 새로 읽게
        super().end_headers()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), partial(Handler, directory=str(ROOT)))
    print(f"판독 폴더를 http://127.0.0.1:{PORT}/ 로 연다. 끌 때는 Ctrl+C")
    server.serve_forever()
