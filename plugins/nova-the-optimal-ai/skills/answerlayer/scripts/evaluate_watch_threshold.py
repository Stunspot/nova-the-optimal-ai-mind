from __future__ import annotations
import argparse
OPS={"gte":lambda a,b:a>=b,"gt":lambda a,b:a>b,"lte":lambda a,b:a<=b,"lt":lambda a,b:a<b,"eq":lambda a,b:a==b}
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("observed",type=float);p.add_argument("operator",choices=OPS);p.add_argument("threshold",type=float);a=p.parse_args();hit=OPS[a.operator](a.observed,a.threshold);print("TRIGGERED" if hit else "NOT_TRIGGERED");return 0
if __name__=="__main__":raise SystemExit(main())
