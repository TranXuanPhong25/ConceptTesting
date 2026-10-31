"""Usage: python -m python_bug_concepts.retrieval_v15 source.py --entry f"""
import argparse
import json
from pathlib import Path
from .retriever import search,ARMS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--entry')
    parser.add_argument('--arm',choices=ARMS,default='relations')
    args=parser.parse_args()
    print(json.dumps(search(args.source.read_text(),args.entry,args.arm),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
