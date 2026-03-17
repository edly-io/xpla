"""Entry point: python -m xpla.lti"""

import argparse
import uvicorn

parser = argparse.ArgumentParser()
parser.add_argument("--host", "-H", default="127.0.0.1")
parser.add_argument("--port", "-p", type=int, default=9754)
args = parser.parse_args()

uvicorn.run("xpla.lti.app:app", host=args.host, port=args.port, reload=True)
