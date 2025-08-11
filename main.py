
from crawler.navigator import run_crawler

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python main.py <URL>")
    else:
        run_crawler(sys.argv[1])
