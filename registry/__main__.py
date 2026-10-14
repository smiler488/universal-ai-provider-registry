import argparse
from pathlib import Path
from .core import build, validate

parser=argparse.ArgumentParser(description='Build and validate evidence-preserving public model metadata')
parser.add_argument('command',choices=['sync','build','validate'])
parser.add_argument('--output',type=Path,default=Path('public/v1'))
parser.add_argument('--cache',type=Path,default=Path('.cache'))
args=parser.parse_args()
if args.command=='validate':
    validate(args.output)
else:
    build(args.command=='sync',args.output,args.cache)
