import argparse, ipaddress, json, os
from shodan import Shodan, APIError
def main():
    parser = argparse.ArgumentParser(description='Query existing Shodan data; no scan submission or account changes.')
    parser.add_argument('kind', choices=['host', 'count', 'search'])
    parser.add_argument('target')
    parser.add_argument('--limit', type=int, default=10)
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        parser.error('--limit must be between 1 and 100')
    if args.kind == 'host':
        try: ipaddress.ip_address(args.target)
        except ValueError: parser.error('host expects an IP address')
    key = os.environ.get('SHODAN_API_KEY')
    if not key:
        print(json.dumps({'error':'Set SHODAN_API_KEY in this process before live queries.', 'state':'credential-required'}))
        return 2
    api = Shodan(key)
    try:
        if args.kind == 'host':
            result = api.host(args.target)
        elif args.kind == 'count':
            result = api.count(args.target)
        else:
            result = api.search(args.target, page=1)
            result['matches'] = result.get('matches', [])[:args.limit]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except APIError as exc:
        print(json.dumps({'error':str(exc), 'state':'provider-error'}))
        return 1
if __name__ == '__main__':
    raise SystemExit(main())
