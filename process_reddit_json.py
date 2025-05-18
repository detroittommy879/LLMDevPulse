import os
import sys
import json
from datetime import datetime

BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def base58_encode(s):
    # Convert string to bytes, then to int
    n = int.from_bytes(s.encode('utf-8'), 'big')
    res = ''
    while n > 0:
        n, r = divmod(n, 58)
        res = BASE58_ALPHABET[r] + res
    # Handle leading zeros
    pad = 0
    for c in s.encode('utf-8'):
        if c == 0:
            pad += 1
        else:
            break
    return BASE58_ALPHABET[0] * pad + res if res else BASE58_ALPHABET[0]

def extract_date(date_str):
    # Expects 'YYYY-MM-DD HH:MM:SS'
    return date_str.split(' ')[0]

def process_file(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    entries = []

    # Process post
    author = data.get('author', '')
    date = extract_date(data.get('created_date', ''))
    body = data.get('selftext', '').strip()
    if author and date and body:
        entries.append(f"{base58_encode(author)} {date} {body}")

    # Process comments
    for comment in data.get('comments', []):
        cauthor = comment.get('author', '')
        cdate = extract_date(comment.get('created_date', ''))
        cbody = comment.get('body', '').strip()
        if cauthor and cdate and cbody and cbody != '[removed]':
            entries.append(f"{base58_encode(cauthor)} {cdate} {cbody}")

    return entries

def main():
    if len(sys.argv) != 2:
        print("Usage: python process_reddit_json.py <folder>")
        sys.exit(1)
    folder = sys.argv[1]
    txt_folder = os.path.join(folder, 'txt')
    os.makedirs(txt_folder, exist_ok=True)

    all_entries = []
    for fname in os.listdir(folder):
        if fname.endswith('.json'):
            fpath = os.path.join(folder, fname)
            print(f"Processing {fname}...")
            entries = process_file(fpath)
            print(f"  Found {len(entries)} entries.")
            if entries:
                # Write individual txt file
                txt_path = os.path.join(txt_folder, fname.replace('.json', '.txt'))
                with open(txt_path, 'w', encoding='utf-8') as tf:
                    tf.write('\n\n'.join(entries) + '\n')
                print(f"  Wrote {txt_path}")
                all_entries.extend(entries)

    # Write giant txt file
    if all_entries:
        big_txt_path = os.path.join(folder, 'all_data.txt')
        with open(big_txt_path, 'w', encoding='utf-8') as bf:
            bf.write('\n\n'.join(all_entries) + '\n')
        print(f"Wrote {big_txt_path} with {len(all_entries)} total entries.")
    else:
        print("No entries found in any JSON files.")

if __name__ == '__main__':
    main()
