import sys

def extract_skill_lines(input_path: str, output_path: str):
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    result = []
    for line in lines:
        parts = line.split(" ")
        if len(parts) >= 3 and parts[2].startswith("skill"):
            result.append(line)

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(result)

    print(f"{len(result)} 行抽出 → {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("使い方: python script.py <入力ファイル> <出力ファイル>")
        sys.exit(1)

    extract_skill_lines(sys.argv[1], sys.argv[2])
```

**使い方：**
```
python script.py input.txt output.txt
