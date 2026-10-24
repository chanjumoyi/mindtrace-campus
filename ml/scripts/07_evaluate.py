"""待实现：evaluate。运行时明确退出，避免生成虚假实验结果。"""
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    parser.exit(2, "该步骤尚未实现；请参阅 ml/README.md。\n")


if __name__ == "__main__":
    main()
