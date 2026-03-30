import re
import sys
from collections import defaultdict
import statistics

def parse_log(filepath):
    pattern = re.compile(
        r'\[\d{2}:\d{2}\]\s+(\S+)\s+\|\s+context:\s+(\d+)/128000\s+\|\s+total:\s+\d+'
    )
    
    stats = defaultdict(list)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            m = pattern.search(line)
            if m:
                skill_name = m.group(1)
                context_a = int(m.group(2))
                stats[skill_name].append(context_a)
    
    print(f"{'Skill':<20} {'Count':>6} {'Total':>12} {'Average':>12} {'StdDev':>12} {'Min':>10} {'Max':>10}")
    print("-" * 86)
    
    for skill, values in sorted(stats.items()):
        count = len(values)
        total = sum(values)
        avg = total / count
        stddev = statistics.stdev(values) if count > 1 else 0.0
        mn = min(values)
        mx = max(values)
        print(f"{skill:<20} {count:>6} {total:>12,} {avg:>12.1f} {stddev:>12.1f} {mn:>10,} {mx:>10,}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <logfile.txt>")
        sys.exit(1)
    
    parse_log(sys.argv[1])
