#!/usr/bin/env python3
"""
エンコーディングチェックスクリプト

指定ディレクトリ配下の *.c ファイルをUTF-8で読み込めるかチェックする。
生成処理開始前の事前チェック用。

使用方法:
    python check_encoding.py dir_path
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple


def check_file_encoding(file_path: Path) -> Tuple[bool, str]:
    """
    ファイルをUTF-8で読み込めるかチェックする。

    Args:
        file_path: チェック対象のファイルパス

    Returns:
        (成功フラグ, エラーメッセージ)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            # ファイル全体を読み込んでエンコーディングをチェック
            f.read()
        return True, ""
    except UnicodeDecodeError as e:
        return False, f"UnicodeDecodeError: {e}"
    except Exception as e:
        return False, f"読み込みエラー: {e}"


def fix_file_encoding(file_path: Path) -> Tuple[bool, str]:
    """
    ファイルのエンコーディングエラーを修正する。
    問題のある文字を削除してUTF-8で保存し直す。

    Args:
        file_path: 修正対象のファイルパス

    Returns:
        (成功フラグ, 結果メッセージ)
    """
    try:
        # 元ファイルをバイナリモードで読み込み
        with open(file_path, "rb") as f:
            raw_content = f.read()

        # UTF-8でデコード（エラー文字は無視）
        clean_content = raw_content.decode("utf-8", errors="ignore")

        # 元のバイト数と修正後のバイト数を比較
        original_size = len(raw_content)
        clean_size = len(clean_content.encode("utf-8"))
        removed_bytes = original_size - clean_size

        if removed_bytes > 0:
            # クリーンな内容で上書き保存
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(clean_content)
            
            # 修正後の検証
            with open(file_path, "r", encoding="utf-8") as f:
                f.read()
            
            return True, f"修正完了: {removed_bytes}バイト削除"
        else:
            return True, "修正不要: エンコーディングエラーなし"

    except Exception as e:
        return False, f"修正エラー: {e}"


def find_c_files(directory: Path) -> List[Path]:
    """
    指定ディレクトリ配下の *.c ファイルを再帰的に検索する。

    Args:
        directory: 検索対象のディレクトリ

    Returns:
        見つかった *.c ファイルのリスト
    """
    return list(directory.glob("**/*.c"))


def main():
    """
    メイン処理
    """
    parser = argparse.ArgumentParser(
        description="指定ディレクトリ配下の *.c ファイルのUTF-8エンコーディングをチェックし、エラーがあれば修正します"
    )
    parser.add_argument("dir_path", type=str, help="チェック対象のディレクトリパス")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="エンコーディングエラーを自動修正する（デフォルト: True）",
        default=True,  # デフォルトで修正を有効化
    )
    parser.add_argument(
        "--no-fix",
        dest="fix",
        action="store_false",
        help="エンコーディングエラーの修正を無効化（チェックのみ）",
    )

    args = parser.parse_args()

    # ディレクトリパスの確認
    target_dir = Path(args.dir_path)
    if not target_dir.exists():
        print(f"エラー: ディレクトリが存在しません: {target_dir}")
        sys.exit(1)

    if not target_dir.is_dir():
        print(f"エラー: 指定されたパスはディレクトリではありません: {target_dir}")
        sys.exit(1)

    print(f"エンコーディングチェック開始: {target_dir}")

    # *.c ファイルを検索
    print("*.c ファイルを検索中...")
    c_files = find_c_files(target_dir)

    if not c_files:
        print("*.c ファイルが見つかりませんでした")
        return

    print(f"見つかったファイル数: {len(c_files)} 個")

    # エンコーディングチェック実行
    print("エンコーディングチェック中...")
    if args.fix:
        print("修正モード: 有効（エラーが見つかった場合は自動修正します）")
    else:
        print("修正モード: 無効（チェックのみ）")

    success_count = 0
    error_files = []
    fixed_files = []
    failed_fixes = []

    # 進捗表示用
    total_files = len(c_files)
    processed_files = 0

    for file_path in c_files:
        processed_files += 1

        # 進捗表示（100ファイル毎または最後のファイル）
        if processed_files % 100 == 0 or processed_files == total_files:
            print(f"進捗: {processed_files}/{total_files} ファイル処理済み")

        is_success, error_msg = check_file_encoding(file_path)

        if is_success:
            success_count += 1
        else:
            if args.fix:
                # 修正を試みる
                fix_success, fix_msg = fix_file_encoding(file_path)
                if fix_success:
                    fixed_files.append((file_path, fix_msg))
                    success_count += 1  # 修正成功したら成功にカウント
                else:
                    failed_fixes.append((file_path, fix_msg))
                    error_files.append((file_path, error_msg))
            else:
                error_files.append((file_path, error_msg))

    # 結果出力
    print("\n" + "=" * 50)
    print("エンコーディングチェック結果")
    print("=" * 50)
    print(f"処理したファイル総数: {total_files}")
    print(f"正常に読み込めたファイル数: {success_count}")

    if args.fix and fixed_files:
        print(f"修正したファイル数: {len(fixed_files)}")

    if error_files:
        print(f"エラーが発生したファイル数: {len(error_files)}")

    # 修正されたファイルの詳細を表示
    if fixed_files:
        print("\n修正されたファイル:")
        print("-" * 50)
        for file_path, fix_msg in fixed_files:
            try:
                relative_path = file_path.relative_to(target_dir)
                print(f"✅ {relative_path}: {fix_msg}")
            except ValueError:
                print(f"✅ {file_path}: {fix_msg}")

    # エラーファイルの詳細を表示
    if error_files:
        print("\nエラーファイル一覧:")
        print("-" * 50)
        for file_path, error_msg in error_files:
            try:
                relative_path = file_path.relative_to(target_dir)
                print(f"❌ {relative_path}")
            except ValueError:
                print(f"❌ {file_path}")
            print(f"   エラー: {error_msg}")

    # 修正失敗ファイルの詳細を表示
    if failed_fixes:
        print("\n修正に失敗したファイル:")
        print("-" * 50)
        for file_path, fix_msg in failed_fixes:
            try:
                relative_path = file_path.relative_to(target_dir)
                print(f"⚠️ {relative_path}: {fix_msg}")
            except ValueError:
                print(f"⚠️ {file_path}: {fix_msg}")

    # 最終判定
    if error_files:
        print(
            f"\n❌ チェック失敗: {len(error_files)} 個のファイルでエラーが残っています"
        )
        sys.exit(1)
    elif fixed_files:
        print(f"\n✅ チェック完了: {len(fixed_files)} 個のファイルを修正しました")
    else:
        print("\n✅ チェック成功: すべてのファイルがUTF-8で正常に読み込めます")


if __name__ == "__main__":
    main()
